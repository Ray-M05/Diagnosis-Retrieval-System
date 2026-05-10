"""GroqAdapter — calls Groq Cloud API via its OpenAI-compatible HTTP endpoint.

Uses httpx (already in base deps) — no additional SDK required.
Endpoint: POST https://api.groq.com/openai/v1/chat/completions

Free tier (as of 2026): llama-3.1-8b-instant — 30 RPM / 1M tokens/day.
Set GROQ_API_KEY environment variable.
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

_GROQ_BASE = "https://api.groq.com/openai/v1"


@dataclass
class GroqAdapterConfig:
    model: str = "llama-3.1-8b-instant"
    api_key: str = ""
    default_max_tokens: int = 1500
    default_temperature: float = 0.2
    timeout_s: float = 60.0


class GroqAdapter(LLMPort):
    """LLMPort implementation backed by Groq Cloud (OpenAI-compatible API)."""

    def __init__(self, config: GroqAdapterConfig | None = None) -> None:
        self.cfg = config or GroqAdapterConfig()

        if not self.cfg.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com"
            )

        self._headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        self._chat_url = f"{_GROQ_BASE}/chat/completions"

        if not self.health_check():
            raise RuntimeError(
                f"Groq API not reachable or API key invalid. Model: {self.cfg.model}"
            )

    # ------------------------------------------------------------------
    # LLMPort interface
    # ------------------------------------------------------------------

    def generate(self, req: GenerationRequest) -> GenerationResult:
        payload = self._build_payload(req, stream=False)
        t0 = time.monotonic()

        try:
            with httpx.Client(timeout=self.cfg.timeout_s) as client:
                resp = client.post(self._chat_url, headers=self._headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Groq request failed: {exc}") from exc

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return GenerationResult(
            text=text,
            model=data.get("model", self.cfg.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            eval_duration_ms=elapsed_ms,
            stop_reason=data["choices"][0].get("finish_reason"),
        )

    def stream(self, req: GenerationRequest) -> Iterator[str]:
        payload = self._build_payload(req, stream=True)

        try:
            with httpx.Client(timeout=self.cfg.timeout_s) as client:
                with client.stream("POST", self._chat_url, headers=self._headers, json=payload) as resp:
                    resp.raise_for_status()
                    for raw_line in resp.iter_lines():
                        if not raw_line or raw_line == "data: [DONE]":
                            continue
                        if raw_line.startswith("data: "):
                            raw_line = raw_line[6:]
                        try:
                            chunk = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Groq streaming failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{_GROQ_BASE}/models",
                    headers=self._headers,
                )
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
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
