"""Abstract LLM port — provider-agnostic interface for language model calls."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator, Literal

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GenerationRequest(BaseModel):
    system: str
    messages: list[LLMMessage]
    max_tokens: int = 1500
    temperature: float = 0.2


class GenerationResult(BaseModel):
    text: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    eval_duration_ms: int = 0
    stop_reason: str | None = None


class LLMPort(ABC):
    """Abstract base for all LLM adapters."""

    @abstractmethod
    def generate(self, req: GenerationRequest) -> GenerationResult:
        """Blocking call — returns the full generated text."""

    @abstractmethod
    def stream(self, req: GenerationRequest) -> Iterator[str]:
        """Streaming call — yields text deltas as they arrive."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the backend is reachable and the model is available."""
