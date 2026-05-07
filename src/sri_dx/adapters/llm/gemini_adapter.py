"""GeminiAdapter — calls Google Gemini API via the official SDK.

Requires: google-generativeai>=0.7
API key:  set GEMINI_API_KEY environment variable.
Free tier: gemini-1.5-flash supports ~15 RPM / 1M tokens/day at no cost.

Streaming: uses stream=True on generate_content; yields text deltas as they arrive.
Health check: lists available models — verifies API key is valid and network reachable.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterator

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from sri_dx.core.ports.generation.llm_port import (
    GenerationRequest,
    GenerationResult,
    LLMPort,
)

logger = logging.getLogger(__name__)


@dataclass
class GeminiAdapterConfig:
    model: str = "gemini-1.5-flash"
    api_key: str = ""
    default_max_tokens: int = 1500
    default_temperature: float = 0.2
    timeout_s: float = 120.0


class GeminiAdapter(LLMPort):
    """LLMPort implementation backed by Google Gemini API."""

    def __init__(self, config: GeminiAdapterConfig | None = None) -> None:
        self.cfg = config or GeminiAdapterConfig()

        if not self.cfg.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/app/apikey"
            )

        genai.configure(api_key=self.cfg.api_key)

        if not self.health_check():
            raise RuntimeError(
                f"Gemini API not reachable or API key invalid. Model: {self.cfg.model}"
            )

    # ------------------------------------------------------------------
    # LLMPort interface
    # ------------------------------------------------------------------

    def generate(self, req: GenerationRequest) -> GenerationResult:
        """Blocking call — returns the full generated text."""
        model = self._model_with_system(req.system)
        contents = self._build_contents(req)
        gen_cfg = self._build_gen_config(req)
        t0 = time.monotonic()

        try:
            response = model.generate_content(contents, generation_config=gen_cfg)
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
        model = self._model_with_system(req.system)
        contents = self._build_contents(req)
        gen_cfg = self._build_gen_config(req)

        try:
            response = model.generate_content(
                contents,
                generation_config=gen_cfg,
                stream=True,
            )
            for chunk in response:
                delta = chunk.text or ""
                if delta:
                    yield delta
        except Exception as exc:
            raise RuntimeError(f"Gemini streaming failed: {exc}") from exc

    def health_check(self) -> bool:
        """Return True if the API key is valid and Gemini is reachable."""
        try:
            models = list(genai.list_models())
            return len(models) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _model_with_system(self, system: str) -> genai.GenerativeModel:
        """Instantiate a GenerativeModel with system_instruction per request.

        gemini-1.5-flash supports system_instruction natively; this is the
        recommended way to pass a system prompt rather than embedding it in
        the user turn.
        """
        return genai.GenerativeModel(
            self.cfg.model,
            system_instruction=system,
        )

    @staticmethod
    def _build_contents(req: GenerationRequest) -> list[dict]:
        contents = []
        for msg in req.messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [msg.content]})
        return contents

    @staticmethod
    def _build_gen_config(req: GenerationRequest) -> GenerationConfig:
        return GenerationConfig(
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
        )

    @staticmethod
    def _stop_reason(response) -> str | None:
        try:
            return response.candidates[0].finish_reason.name
        except Exception:
            return None
