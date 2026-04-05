"""Schemas de configuración para el módulo de chunking (modules).

Modelos Pydantic para configuraciones específicas de estrategias
de chunking implementadas dentro de `sri_dx.modules.chunking`.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SemanticChunkingConfig(BaseModel):
    """Configuración para `SemanticChunker` (chunking semántico).

    El SemanticChunker actúa como segunda estrategia: solo se activa cuando
    una sección supera `max_chars` en ChunkingConfig. Usa un modelo ligero
    (all-MiniLM-L6-v2) para detectar breakpoints semánticos rápidamente,
    sin cargar Bio_ClinicalBERT.
    """

    # Modelo ligero para detección de breakpoints (no el BERT de 768 dims)
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Modelo para embeddings de oraciones. Usar uno ligero (MiniLM) para velocidad."
    )

    similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Umbral de similitud coseno entre oraciones consecutivas. "
            "Por debajo → nuevo chunk. 0.75 es adecuado para texto médico coherente."
        )
    )

    min_sentences_per_chunk: int = Field(
        default=3,
        ge=1,
        description="Mínimo de oraciones por chunk antes de permitir un breakpoint."
    )

    max_sentences_per_chunk: int = Field(
        default=20,
        ge=1,
        description="Máximo de oraciones por chunk (fuerza breakpoint si se excede)."
    )

    min_chunk_chars: int = Field(
        default=150,
        ge=0,
        description="Chunks más pequeños se fusionan con el anterior."
    )

    max_chunk_chars: int = Field(
        default=2000,
        ge=1,
        description="Chunks más grandes se fuerzan a dividir independientemente de la similitud."
    )

    combine_short_sentences: bool = Field(
        default=True,
        description="Si True, combina oraciones muy cortas antes del análisis semántico."
    )

    short_sentence_threshold: int = Field(
        default=30,
        ge=0,
        description="Oraciones con menos caracteres se consideran 'cortas' y se fusionan."
    )

    batch_size: int = Field(
        default=64,
        ge=1,
        description="Batch size para encoding de oraciones (MiniLM es mucho más ligero)."
    )
