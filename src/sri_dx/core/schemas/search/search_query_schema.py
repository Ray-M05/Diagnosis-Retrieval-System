# core/schemas/search/search_query_schema.py
"""Schemas for search queries."""

from pydantic import BaseModel, Field
from typing import List, Optional


class LexicalQuery(BaseModel):
    """Query for lexical search."""
    text: str = Field(..., description="Query text")
    fields: Optional[List[str]] = None  # Fields to search
    boost_fields: Optional[dict] = None  # Field -> boost factor
    operator: str = Field(default="OR", description="AND/OR between terms")


class HybridQuery(BaseModel):
    """Query for hybrid search."""
    text: str = Field(..., description="Query text")
    lexical_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    fusion_method: str = Field(default="rrf", description="rrf, weighted_sum, etc.")
