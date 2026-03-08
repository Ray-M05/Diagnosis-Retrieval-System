# src/sri_dx/core/schemas/indexing/ner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NerEntity:
    """
    Representation of a Named Entity recognized in the text.
    Used for appending context to clinical documents and chunks.
    """
    text: str
    label: str
    start_char: int
    end_char: int
    score: Optional[float] = None
