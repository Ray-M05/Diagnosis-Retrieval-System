"""OllamaAdapter — calls a local Ollama instance via its HTTP API.

Uses httpx (already in base deps) — no additional SDK required.
Endpoint: POST /api/chat  (Ollama ≥ 0.1.14)

Streaming: POST /api/chat with stream=true returns NDJSON; each line is a JSON
object with {"message": {"content": "<delta>"}, "done": false|true}.
The final line has "done": true and carries token usage stats.

Health check: GET /api/tags — lists available models. Raises RuntimeError on
startup if Ollama is unreachable (other endpoints stay available).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Iterator

import httpx

from sri_dx.core.ports.generation.llm_port import (
    GenerationRequest,
    GenerationResult,
    LLMPort,
)

logger = logging.getLogger(__name__)


@dataclass
class OllamaAdapterConfig:
    model: str = "llama3.1:8b-instruct"
    host: str = "http://localhost:11434"
    default_max_tokens: int = 1500
    default_temperature: float = 0.2
    timeout_s: float = 120.0
    num_ctx: int = 8192          # context window for the model


class OllamaAdapter(LLMPort):
    """LLMPort implementation backed by a local Ollama server."""

    def __init__(self, config: OllamaAdapterConfig | None = None) -> None:
        self.cfg = config or OllamaAdapterConfig()
        self._chat_url = f"{self.cfg.host.rstrip('/')}/api/chat"
        self._tags_url = f"{self.cfg.host.rstrip('/')}/api/tags"

        if not self.health_check():
            raise RuntimeError(
                f"Ollama not reachable at {self.cfg.host}. "
                f"Verify it is running. Model expected: {self.cfg.model}"
            )

    # ------------------------------------------------------------------
    # LLMPort interface
    # ------------------------------------------------------------------

    def generate(self, req: GenerationRequest) -> GenerationResult:
        """Blocking call — collects the full response before returning."""
        payload = self._build_payload(req, stream=False)
        t0 = time.monotonic()

        try:
            with httpx.Client(timeout=self.cfg.timeout_s) as client:
                resp = client.post(self._chat_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        text = data.get("message", {}).get("content", "")
        return GenerationResult(
            text=text,
            model=data.get("model", self.cfg.model),
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            eval_duration_ms=elapsed_ms,
            stop_reason=data.get("done_reason"),
        )

    def stream(self, req: GenerationRequest) -> Iterator[str]:
        """Streaming call — yields text deltas as they arrive from Ollama."""
        payload = self._build_payload(req, stream=True)

        try:
            with httpx.Client(timeout=self.cfg.timeout_s) as client:
                with client.stream("POST", self._chat_url, json=payload) as resp:
                    resp.raise_for_status()
                    for raw_line in resp.iter_lines():
                        if not raw_line:
                            continue
                        try:
                            chunk = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue

                        delta = chunk.get("message", {}).get("content", "")
                        if delta:
                            yield delta

                        if chunk.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama streaming failed: {exc}") from exc

    def health_check(self) -> bool:
        """Return True if Ollama is reachable (model availability not checked)."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(self._tags_url)
                return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_payload(self, req: GenerationRequest, *, stream: bool) -> dict:
        messages = [{"role": "system", "content": req.system}]
        for msg in req.messages:
            messages.append({"role": msg.role, "content": msg.content})

        return {
            "model": self.cfg.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": self.cfg.num_ctx,
                "temperature": req.temperature,
                "num_predict": req.max_tokens,
            },
        }
