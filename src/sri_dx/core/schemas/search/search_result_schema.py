# core/schemas/search/search_result_schema.py
"""Schemas for search results of different types."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SearchResult(BaseModel):
    """Base search result."""
    doc_id: str
    chunk_id: Optional[str] = None
    score: float
    metadata: Optional[Dict[str, Any]] = None


class LexicalSearchResult(SearchResult):
    """Lexical search result (BM25/TF-IDF)."""
    bm25_score: Optional[float] = None
    tf_idf_score: Optional[float] = None
    matched_terms: Optional[List[str]] = None


class VectorSearchResult(SearchResult):
    """Vector search result."""
    vector_score: float = Field(..., description="Similarity score (cosine, dot, etc.)")
    embedding_model: Optional[str] = None


class HybridSearchResult(SearchResult):
    """Hybrid search result."""
    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    rerank_score: Optional[float] = None
    fusion_method: Optional[str] = "rrf"  # reciprocal rank fusion, cross-encoder, etc.
