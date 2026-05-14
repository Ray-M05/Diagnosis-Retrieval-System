"""Schemas for explicit feedback API contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=2000)
    chunk_id: str = Field(..., min_length=1)
    doc_id: str = Field(..., min_length=1)
    relevant: bool


class FeedbackResponse(BaseModel):
    ok: bool
    message: str


class RefineSearchRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=10, ge=1, le=30)


class RefineSearchResponse(BaseModel):
    original_query: str
    refined_query: str
    strategy: Literal["feedback_textual"]
    results: dict[str, Any]
