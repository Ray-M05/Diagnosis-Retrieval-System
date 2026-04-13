# core/schemas/search/search_query_schema.py
"""Schemas para queries de búsqueda."""

from pydantic import BaseModel, Field
from typing import List, Optional


class LexicalQuery(BaseModel):
    """Query para búsqueda léxica."""
    text: str = Field(..., description="Texto de la consulta")
    fields: Optional[List[str]] = None  # Campos donde buscar
    boost_fields: Optional[dict] = None  # Campo -> factor de boost
    operator: str = Field(default="OR", description="AND/OR entre términos")


class HybridQuery(BaseModel):
    """Query para búsqueda híbrida."""
    text: str = Field(..., description="Texto de la consulta")
    lexical_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    fusion_method: str = Field(default="rrf", description="rrf, weighted_sum, etc.")
