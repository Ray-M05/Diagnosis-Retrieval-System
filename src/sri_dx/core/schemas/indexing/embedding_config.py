# core/schemas/indexing/embedding_config.py
"""Configuración para generación de embeddings."""

from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuración para generación de embeddings."""
    
    model_name: str = Field(
        default="Bio_ClinicalBERT",
        description="Nombre del modelo de embeddings"
    )
    
    embedding_dim: int = Field(
        default=768,
        description="Dimensionalidad del vector resultante"
    )
    
    normalize: bool = Field(
        default=True,
        description="Si true, normaliza los vectores a norma 1"
    )
    
    batch_size: int = Field(
        default=32,
        description="Tamaño de batch para procesamiento"
    )
    
    max_length: int = Field(
        default=512,
        description="Longitud máxima de secuencia en tokens"
    )
