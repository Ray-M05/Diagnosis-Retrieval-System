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
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    llm: Literal["ready", "unreachable"]
    opensearch: Literal["ready", "unreachable"]
    version: str = "0.1.0"
