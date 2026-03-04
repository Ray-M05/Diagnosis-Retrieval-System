# core/schemas/indexing/chunk_config.py
"""Configuración para estrategias de chunking."""

from pydantic import BaseModel, Field
from typing import Optional


class ChunkingConfig(BaseModel):
    """Configuración para estrategia de chunking."""
    
    chunk_size: int = Field(
        default=512, 
        ge=64, 
        le=4096,
        description="Tamaño máximo del chunk en tokens"
    )
    
    strategy: str = Field(
        default="sliding_window",
        description="Estrategia: sliding_window, semantic, medical_section"
    )
    
    preserve_sentences: bool = Field(
        default=True,
        description="Si true, no rompe oraciones"
    )
    
    min_chunk_size: int = Field(
        default=100,
        description="Tamaño mínimo (chunks más pequeños se descartan/fusionan)"
    )
    
    metadata_fields: Optional[list[str]] = Field(
        default=None,
        description="Campos de metadata a preservar en cada chunk"
    )
