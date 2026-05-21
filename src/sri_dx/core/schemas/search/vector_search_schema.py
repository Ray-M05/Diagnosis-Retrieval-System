# core/schemas/search/vector_search_schema.py
"""Schemas for vector search and the embedding store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class EmbeddingSearchResult:
    """Result from the embeddings index."""

    embedding_id: str
    chunk_id: str
    doc_id: str
    score: float  # similarity score (0-1 for cosine)
    
    chunk_text_preview: Optional[str] = None
    section_heading: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingStoreConfig:
    """Configuration for the embedding store."""

    index_name: str = "clinical_embeddings_v1"
    alias_name: str = "clinical_embeddings"
    vector_dim: int = 768
    similarity_metric: str = "cosine"  # cosine, dot_product, l2
    ef_search: int = 100  # HNSW search quality parameter
