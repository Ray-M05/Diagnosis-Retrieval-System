from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal, Sequence


@dataclass(frozen=True)
class SearchFilters:
    source_domains: Optional[list[str]] = None
    mime_types: Optional[list[str]] = None
    seed_groups: Optional[list[str]] = None
    seed_ids: Optional[list[str]] = None

    # Phase D / optional: filter by concepts if stored in OpenSearch
    concept_ids: Optional[list[str]] = None

    # date ranges (ISO-8601 or OpenSearch-compatible date)
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

    # Facets (aggs). If empty, no facets are computed.
    facet_fields: Sequence[str] = ("source_domain", "mime_type", "seed_group")
    facet_size: int = 20
