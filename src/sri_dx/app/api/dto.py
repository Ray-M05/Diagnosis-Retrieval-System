"""HTTP-layer DTOs — pydantic models for FastAPI request/response bodies.

Kept separate from domain schemas so the API contract can evolve independently.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from sri_dx.core.schemas.rag.patient_chart import Demographics, PatientChart, VitalSigns
from sri_dx.core.schemas.rag.rag_response import (
    Citation,
    DifferentialDiagnosis,
    RAGResponse,
    RAGUsage,
)


# ---------------------------------------------------------------------------
# /search/diseases
# ---------------------------------------------------------------------------

class SearchDiseasesRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    k: int = Field(default=10, ge=1, le=30)


class DiseaseDTO(BaseModel):
    """Shape expected by the React DiseaseCard component."""
    id: str
    name: str
    description: str          # first evidence preview used as description
    symptoms: list[str]       # concept_ids or NER terms from evidence
    source: str               # source_domain of top evidence
    sourceUrl: str            # url of top evidence
    evidence_count: int
    rank: int
    feedback_chunk_id: str | None = None
    feedback_doc_id: str | None = None
    score: float = 0.0        # aggregated_score (NER mode) or rerank_score (web mode)
    doc_title: str | None = None  # title of the top evidence document


class SearchDiseasesResponse(BaseModel):
    diseases: list[DiseaseDTO]
    query: str
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# /rag/parse-chart  (multipart upload → PatientChart JSON)
# ---------------------------------------------------------------------------

class ParseChartResponse(BaseModel):
    chart: PatientChart
    extraction_failed: bool
    warning: str | None = None   # human-readable message when extraction_failed


# ---------------------------------------------------------------------------
# /rag/clinical  (streaming + final response)
# ---------------------------------------------------------------------------

class ClinicalRAGRequest(BaseModel):
    chart: PatientChart
    query: str = Field(..., min_length=1, max_length=2000)


# The SSE final event carries the full RAGResponse — reexport for convenience
ClinicalRAGResponse = RAGResponse


# ---------------------------------------------------------------------------
# /pipeline — composable retrieval + (web enrichment) + (positioning) + (RAG)
# ---------------------------------------------------------------------------

class PipelineStages(BaseModel):
    """Toggles for optional stages. Hybrid retrieval is always executed."""
    web_enrichment: bool = False
    positioning: bool = False
    generation: bool = False   # RAG. Requires `chart`.
    raw_hybrid: bool = False   # Return raw reranked chunks in `hybrid_chunks`.


class PipelineRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    stages: PipelineStages = Field(default_factory=PipelineStages)
    chart: PatientChart | None = None   # required if stages.generation
    k: int = Field(default=10, ge=1, le=30)


class WebEnrichmentSummary(BaseModel):
    triggered: bool
    docs_added: int
    chunks_added: int
    api_retrieved: int = 0
    api_new_documents: int = 0
    duplicates_removed: int = 0


class SufficiencyInfo(BaseModel):
    """Knowledge-sufficiency evaluation for the current hybrid retrieval result."""
    sufficient: bool
    insufficiency_score: float
    rank_confidence: float
    useful_count: int
    symptom_coverage: float
    source_diversity: int
    failed_criteria: list[str]


class HybridChunkDTO(BaseModel):
    """Raw reranked chunk — used by Research/Hybrid+Reranking mode.

    Distinct from `DiseaseDTO` which carries NER-aggregated diseases.
    """
    doc_id: str
    chunk_id: str
    score: float                          # rerank_score (final ranking)
    rerank_score: float
    vector_score: float | None = None
    lexical_score: float | None = None
    fusion_method: str = "cross-encoder"
    title: str | None = None              # from doc metadata or URL slug
    section_heading: str | None = None
    url: str | None = None
    source_domain: str | None = None
    chunk_text_preview: str = ""          # first ~400 chars


class PipelineResponse(BaseModel):
    """Non-streaming response (when stages.generation is False).

    Each section is present only if the corresponding stage was activated.
    """
    query: str
    hybrid: list[DiseaseDTO] = []
    hybrid_chunks: Optional[list[HybridChunkDTO]] = None   # only when stages.raw_hybrid
    positioned: Optional[list] = None     # list[dict] from search_positioned
    web_enriched: Optional[WebEnrichmentSummary] = None
    sufficiency: Optional[SufficiencyInfo] = None
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    llm: Literal["ready", "unreachable"]
    opensearch: Literal["ready", "unreachable"]
    version: str = "0.1.0"
