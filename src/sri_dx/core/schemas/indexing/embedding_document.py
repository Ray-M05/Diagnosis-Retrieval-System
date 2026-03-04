# core/schemas/indexing/embedding_document.py
"""Schema para documentos de embedding almacenados en BD."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class EmbeddingDocument:
    """
    Representa un embedding almacenado en el índice de embeddings.
    
    Diseño:
    - Índice separado de chunks para flexibilidad
    - Contiene metadata del chunk para filtros sin JOIN
    - Vector con dimensión fija (768 para Bio_ClinicalBERT)
    """
    
    # Identificadores
    embedding_id: str
    """ID único del embedding (formato: emb_{chunk_id}_{model_hash})"""
    
    chunk_id: str
    """ID del chunk al que pertenece este embedding"""
    
    doc_id: str
    """ID del documento padre (para filtros rápidos)"""
    
    # Vector
    vector: List[float]
    """Embedding vector (768 dims para Bio_ClinicalBERT)"""
    
    # Modelo info
    model_name: str = "Bio_ClinicalBERT"
    """Nombre del modelo de embeddings"""
    
    model_version: str = "1.0"
    """Versión del modelo para control de re-embedding"""
    
    embedding_dim: int = 768
    """Dimensionalidad del vector"""
    
    similarity_metric: str = "cosine"
    """Métrica de similitud: cosine, dot_product, l2"""
    
    # Metadata del chunk (desnormalizada para filtros)
    chunk_text_preview: Optional[str] = None
    """Primeros N caracteres del chunk (para debug/preview)"""
    
    chunk_index: int = 0
    """Índice del chunk en el documento"""
    
    section_heading: Optional[str] = None
    """Título de la sección del chunk"""
    
    seed_group: Optional[str] = None
    """Grupo de semilla (para filtros)"""
    
    source_domain: Optional[str] = None
    """Dominio fuente (para filtros)"""
    
    concept_ids: Optional[List[str]] = None
    """Conceptos médicos del chunk (para filtros)"""
    
    # Timestamps
    created_at: str = ""
    """ISO-8601 timestamp de creación"""
    
    chunk_hash: Optional[str] = None
    """Hash del texto del chunk (para detectar si necesita re-embedding)"""


@dataclass
class EmbeddingBatchResult:
    """Resultado del proceso de embedding de un batch."""
    
    total_chunks: int = 0
    """Total de chunks procesados"""
    
    embeddings_generated: int = 0
    """Embeddings generados con éxito"""
    
    embeddings_stored: int = 0
    """Embeddings almacenados en BD"""
    
    errors: List[str] = field(default_factory=list)
    """Errores encontrados"""
    
    skipped_already_embedded: int = 0
    """Chunks que ya tenían embedding (mismo hash)"""
    
    processing_time_seconds: float = 0.0
    """Tiempo total de procesamiento"""
