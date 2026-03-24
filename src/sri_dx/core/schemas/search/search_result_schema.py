# core/schemas/search/search_result_schema.py
"""Schemas para resultados de búsqueda de diferentes tipos."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SearchResult(BaseModel):
    """Resultado base de búsqueda."""
    doc_id: str
    chunk_id: Optional[str] = None
    score: float
    metadata: Optional[Dict[str, Any]] = None


class LexicalSearchResult(SearchResult):
    """Resultado de búsqueda léxica (BM25/TF-IDF)."""
    bm25_score: Optional[float] = None
    tf_idf_score: Optional[float] = None
    matched_terms: Optional[List[str]] = None


class VectorSearchResult(SearchResult):
    """Resultado de búsqueda vectorial."""
    vector_score: float = Field(..., description="Similarity score (cosine, dot, etc.)")
    embedding_model: Optional[str] = None


class HybridSearchResult(SearchResult):
    """Resultado de búsqueda híbrida."""
    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    fusion_method: Optional[str] = "rrf"  # reciprocal rank fusion
