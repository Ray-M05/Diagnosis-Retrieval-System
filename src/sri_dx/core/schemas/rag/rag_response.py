"""RAG response schemas — structured output from the clinical RAG pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_index: int          # n from [CHUNK n] in the generated text
    chunk_id: str
    doc_id: str
    url: str
    source_domain: str
    section_heading: str
    text_preview: str         # first ~200 chars of the chunk
    valid: bool = True        # False if the LLM referenced a non-existent chunk


class DifferentialDiagnosis(BaseModel):
    name: str
    rank: int
    evidence_count: int
    urls: list[str] = Field(default_factory=list)


class RAGUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    eval_duration_ms: int = 0
    model: str = ""


class RAGResponse(BaseModel):
    answer_markdown: str
    citations: list[Citation] = Field(default_factory=list)
    candidate_diseases: list[DifferentialDiagnosis] = Field(default_factory=list)
    composed_query: str = ""
    elapsed_seconds: float = 0.0
    usage: RAGUsage = Field(default_factory=RAGUsage)
    error: str | None = None   # set when retrieval fails or LLM is unreachable
