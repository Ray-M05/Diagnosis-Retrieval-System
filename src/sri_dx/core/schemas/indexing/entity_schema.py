# core/schemas/indexing/entity_schema.py
"""Schemas for clinical entity extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class ClinicalEntity:
    """Clinical entity extracted from text."""

    text: str
    """Original entity text."""

    label: str
    """Entity type: PROBLEM, TREATMENT, TEST, ANATOMY, etc."""

    start_char: int
    """Start position in the original text."""

    end_char: int
    """End position in the original text."""

    confidence: float
    """Confidence score [0.0, 1.0]."""

    normalized_text: Optional[str] = None
    """Normalised text (lowercase, no accents, etc.)."""

    umls_cui: Optional[str] = None
    """UMLS code if a mapping was found."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional extractor-specific metadata."""


@dataclass
class EntityExtractionConfig:
    """Configuration for entity extraction."""

    labels_to_extract: Optional[List[str]] = None
    """If None, extracts all labels. E.g.: ['PROBLEM', 'TREATMENT']"""

    min_confidence: float = 0.5
    """Minimum confidence threshold."""

    batch_size: int = 8
    """Batch size for processing."""

    max_length: int = 512
    """Maximum sequence length in tokens."""

    overlap_tokens: int = 64
    """Token overlap for long documents (sliding window)."""
