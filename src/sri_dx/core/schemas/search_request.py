from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal, Sequence


@dataclass(frozen=True)
class SearchFilters:
    source_domains: Optional[list[str]] = None
    mime_types: Optional[list[str]] = None
    seed_groups: Optional[list[str]] = None
    seed_ids: Optional[list[str]] = None

    # Fase D / opcional: filtrar por conceptos si ya los guardas en OpenSearch
    concept_ids: Optional[list[str]] = None

    # rangos (ISO-8601 o fecha compatible con OpenSearch)
    fetched_from: Optional[str] = None
    fetched_to: Optional[str] = None


@dataclass(frozen=True)
class SearchRequest:
    query: str
    k: int = 10
    offset: int = 0

    operator: Literal["and", "or"] = "and"
    filters: SearchFilters = field(default_factory=SearchFilters)

    # Highlights (snippets)
    return_highlights: bool = True

    # Facetas (aggs). Si está vacío, no se calculan.
    facet_fields: Sequence[str] = ("source_domain", "mime_type", "seed_group")
    facet_size: int = 20
