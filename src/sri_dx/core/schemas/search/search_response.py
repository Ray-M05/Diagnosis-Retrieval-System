from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FacetBucket:
    key: str
    doc_count: int


@dataclass(frozen=True)
class SearchHit:
    doc_id: str
    score: float

    url: str
    title: str
    source_domain: str
    mime_type: str
    fetched_at: str

    highlights: dict[str, list[str]] = field(default_factory=dict)
    concept_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchResponse:
    total_hits: int
    hits: list[SearchHit]
    facets: dict[str, list[FacetBucket]] = field(default_factory=dict)
    took_ms: Optional[int] = None


@dataclass(frozen=True)
class DocumentRecord:
    doc_id: str
    source: dict
