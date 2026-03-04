# core/schemas/search/vector_search_schema.py
"""Schemas para búsqueda vectorial y embedding store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class EmbeddingSearchResult:
    """Resultado de búsqueda en el índice de embeddings."""
    
    embedding_id: str
    chunk_id: str
    doc_id: str
    score: float
    """Similarity score (0-1 para cosine)"""
    
    chunk_text_preview: Optional[str] = None
    section_heading: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingStoreConfig:
    """Configuración para el store de embeddings."""
    
    index_name: str = "clinical_embeddings_v1"
    alias_name: str = "clinical_embeddings"
    vector_dim: int = 768
    similarity_metric: str = "cosine"  # cosine, dot_product, l2
    ef_search: int = 100  # Parámetro HNSW para calidad de búsqueda
