from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sri_dx.core.schemas.acquisition.acquired_document import Section

logger = logging.getLogger(__name__)



@dataclass
class ExternalApiDocument:
    """
    Intermediate format that unifies the heterogeneous responses from the three
    medical APIs before they are converted to AcquiredDocument.

    Fields
    ------
    source:
        One of ``"medlineplus"``, ``"europe_pmc"``, ``"pubmed"``.
    external_id:
        Source-specific stable identifier (PMID, PMCID, URL hash, …).
    canonical_url:
        Normalised canonical URL for the resource.
    title:
        Document title in English.
    abstract_or_summary:
        Full abstract or summary text in English.
    sections:
        Structured content sections ready to be stored in AcquiredDocument.
    """

    source: str
    external_id: str
    canonical_url: str
    title: str
    abstract_or_summary: str
    sections: list[Section]
    language: str = "en"
    published_at: datetime | None = None
    updated_at: datetime | None = None
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    mesh_terms: list[str] = field(default_factory=list)
    raw: Any = None


# Local retrieval result (input to the sufficiency evaluator)

@dataclass
class RetrievedChunkResult:
    """
    Represents a single chunk returned by the hybrid retriever.

    Scores are optional because a result may come from only one retrieval
    branch (e.g. only lexical, with no semantic score).
    """

    chunk_id: str
    doc_id: str
    title: str
    url: str
    source_domain: str
    chunk_text: str
    final_score: float
    bm25_score: float | None = None
    vector_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    section_heading: str | None = None


@dataclass
class LocalRetrievalResult:
    """
    Bundles the original query, extracted symptom terms, and the ranked chunks
    returned by the local hybrid retriever.  This is the input to
    :class:`LocalSufficiencyEvaluator`.
    """

    query: str
    extracted_symptoms: list[str]
    results: list[RetrievedChunkResult]


# Sufficiency decision

@dataclass
class SufficiencyDecision:
    """
    Output of :class:`LocalSufficiencyEvaluator`.

    ``sufficient=True`` means no web search is needed.
    ``failed_criteria`` lists which individual thresholds were not met.
    """

    sufficient: bool
    insufficiency_score: float
    rank_confidence: float
    useful_count: int
    symptom_coverage: float
    source_diversity: int
    failed_criteria: list[str]


# Web search run report

@dataclass
class ApiRetrievalStats:
    """Per-source document counts returned by the APIs.

    ``failed_sources`` lists the sources whose request errored out (timeout,
    HTTP error, network failure) rather than genuinely returning zero results.
    This lets the UI distinguish "the APIs found nothing" from "the APIs could
    not be reached" (e.g. rate-limiting after a burst of identical queries).
    """

    medlineplus: int = 0
    europe_pmc: int = 0
    pubmed: int = 0
    failed_sources: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.medlineplus + self.europe_pmc + self.pubmed

    @property
    def had_failures(self) -> bool:
        return bool(self.failed_sources)


@dataclass
class DeduplicationStats:
    """Summary of deduplication applied to external API documents."""

    retrieved_total: int = 0
    duplicates_removed: int = 0
    new_documents: int = 0


@dataclass
class IndexingStats:
    """Summary of the delta indexing step."""

    delta_path: str = ""
    docs_indexed: int = 0
    chunks_indexed: int = 0


@dataclass
class WebSearchRunReport:
    """
    Complete execution report for a single web-search-and-enrich run.

    This dataclass is serialised to JSON and saved to
    ``data/web_search/reports/web_search_run_<timestamp>.json``.
    """

    query: str
    query_hash: str
    web_search_triggered: bool
    sufficiency: SufficiencyDecision
    api_retrieval: ApiRetrievalStats = field(default_factory=ApiRetrievalStats)
    deduplication: DeduplicationStats = field(default_factory=DeduplicationStats)
    indexing: IndexingStats = field(default_factory=IndexingStats)
    results: list[dict] = field(default_factory=list)
    error: str | None = None
