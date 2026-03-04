# core/schemas/chunk_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

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


class Chunk(BaseModel):
    """Representa un chunk de documento."""
    
    chunk_id: str = Field(
        description="ID único del chunk (formato: {doc_id}_chunk_{index})"
    )
    
    document_id: str = Field(
        description="ID del documento padre"
    )
    
    content: str = Field(
        description="Texto del chunk"
    )

    entities: Optional[Dict[str, list[str]]] = Field(
        default=None,
        description="Entidades detectadas en el chunk"
    )
    
    chunk_index: int = Field(
        ge=0,
        description="Índice del chunk dentro del documento (0-based)"
    )
    
    start_char: int = Field(
        ge=0,
        description="Posición de inicio en el documento original"
    )
    
    end_char: int = Field(
        ge=0,
        description="Posición de fin en el documento original"
    )
    
    token_count: int = Field(
        ge=0,
        description="Número aproximado de tokens"
    )
    
    # Metadatos específicos médicos
    section_type: Optional[str] = Field(
        default=None,
        description="Tipo de sección médica: symptoms, diagnosis, treatment, etc."
    )
    
    medical_entities: Optional[list[str]] = Field(
        default=None,
        description="Entidades médicas detectadas (ICD codes, SNOMED, etc.)"
    )
    
    # Metadatos heredados del documento
    original_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos del documento padre"
    )
    
    # Control de calidad
    quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de calidad del chunk (completitud, coherencia)"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de creación"
    )
    