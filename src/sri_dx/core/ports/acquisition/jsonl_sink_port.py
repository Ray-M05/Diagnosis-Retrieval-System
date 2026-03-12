from __future__ import annotations

from typing import Protocol


class JsonlSinkPort(Protocol):
    """Puerto: persistencia JSONL (append 1 doc por línea, thread-safe)."""

    def write(self, doc: dict) -> None: ...
