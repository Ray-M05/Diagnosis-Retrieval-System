"""Internal models for clinical positioning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PositioningCandidate:
    """A reranked chunk translated into a positioning-friendly shape."""

    chunk_id: str
    doc_id: str
    text: str

    title: Optional[str] = None
    url: Optional[str] = None
    source_domain: Optional[str] = None
    section_heading: Optional[str] = None
    section_index: Optional[int] = None
    chunk_index: Optional[int] = None
    fetched_at: Optional[str] = None
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    mime_type: Optional[str] = None
    seed_group: Optional[str] = None

    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    hybrid_score: Optional[float] = None
    cross_encoder_score: Optional[float] = None

    concept_ids: list[str] = field(default_factory=list)
    ner_entities: list[dict[str, Any]] = field(default_factory=list)
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    normalized_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class ClinicalGroup:
    """A group of evidences associated with one clinical condition."""

    disease_name: str
    display_name: str
    evidences: list[PositioningCandidate] = field(default_factory=list)

    relevance_score: float = 0.0
    mmr_score: float = 0.0
    component_scores: dict[str, float] = field(default_factory=dict)
    matched_symptoms: list[str] = field(default_factory=list)
    source_domains: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)


@dataclass
class PositioningEvidence:
    """Evidence selected for presentation in a positioned result."""

    chunk_id: str
    doc_id: str
    text: str
    content_preview: str
    url: str
    source_domain: str
    section_heading: Optional[str]
    cross_encoder_score: Optional[float]
    hybrid_score: Optional[float]
    lexical_score: Optional[float]
    vector_score: Optional[float]
    authority_score: float


@dataclass
class PositionedClinicalResult:
    """Final user-facing clinical condition after positioning."""

    rank: int
    disease_name: str
    disease_name_display: str
    final_score: float
    relevance_label: str
    matched_symptoms: list[str]
    evidences: list[PositioningEvidence]
    explanation: list[str]
    source_domains: list[str]
    component_scores: dict[str, float]
