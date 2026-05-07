"""GeminiAdapter — calls Google Gemini API via the google-genai SDK.

Requires: google-genai>=1.0
API key:  set GEMINI_API_KEY environment variable.
Free tier: gemini-1.5-flash supports ~15 RPM / 1M tokens/day at no cost.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterator

from google import genai
from google.genai import types

from sri_dx.core.ports.generation.llm_port import (
    GenerationRequest,
    GenerationResult,
    LLMPort,
)

logger = logging.getLogger(__name__)


@dataclass
class GeminiAdapterConfig:
    model: str = "gemini-2.0-flash-lite"
    api_key: str = ""
    default_max_tokens: int = 1500
    default_temperature: float = 0.2


class GeminiAdapter(LLMPort):
    """LLMPort implementation backed by Google Gemini API (google-genai SDK)."""

    def __init__(self, config: GeminiAdapterConfig | None = None) -> None:
        self.cfg = config or GeminiAdapterConfig()

        if not self.cfg.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/app/apikey"
            )

        self._client = genai.Client(api_key=self.cfg.api_key)

        if not self.health_check():
            raise RuntimeError(
                f"Gemini API not reachable or API key invalid. Model: {self.cfg.model}"
            )

    # ------------------------------------------------------------------
    # LLMPort interface
    # ------------------------------------------------------------------

    def generate(self, req: GenerationRequest) -> GenerationResult:
        """Blocking call — returns the full generated text."""
        t0 = time.monotonic()

        try:
            response = self._client.models.generate_content(
                model=self.cfg.model,
                contents=self._build_contents(req),
                config=self._build_config(req),
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        text = response.text or ""
        usage = response.usage_metadata

        return GenerationResult(
            text=text,
            model=self.cfg.model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            eval_duration_ms=elapsed_ms,
            stop_reason=self._stop_reason(response),
        )

    def stream(self, req: GenerationRequest) -> Iterator[str]:
        """Streaming call — yields text deltas as they arrive."""
        try:
            for chunk in self._client.models.generate_content_stream(
                model=self.cfg.model,
                contents=self._build_contents(req),
                config=self._build_config(req),
            ):
                delta = chunk.text or ""
                if delta:
                    yield delta
        except Exception as exc:
            raise RuntimeError(f"Gemini streaming failed: {exc}") from exc

    def health_check(self) -> bool:
        """Return True if the API key is valid and Gemini is reachable."""
        try:
            models = list(self._client.models.list())
            return len(models) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_contents(self, req: GenerationRequest) -> list:
        """Build contents list with system prompt prepended as first user turn."""
        contents = []
        # System instruction as first user message, model acknowledges
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=req.system)],
        ))
        contents.append(types.Content(
            role="model",
            parts=[types.Part(text="Understood. I will follow these instructions.")],
        ))
        for msg in req.messages:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg.content)],
            ))
        return contents

    def _build_config(self, req: GenerationRequest) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
        )

    @staticmethod
    def _stop_reason(response) -> str | None:
        try:
            return response.candidates[0].finish_reason.name
        except Exception:
            return None
