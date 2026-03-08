"""Schemas de configuración para el módulo de chunking (modules).

Modelos Pydantic para configuraciones específicas de estrategias
de chunking implementadas dentro de `sri_dx.modules.chunking`.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SemanticChunkingConfig(BaseModel):
    """Configuración para `SemanticChunker` (chunking semántico).
    """

    similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Umbral de similitud. Debajo de este valor se crea un nuevo chunk."
    )

    min_sentences_per_chunk: int = Field(
        default=2,
        ge=1,
        description="Mínimo de oraciones por chunk."
    )

    max_sentences_per_chunk: int = Field(
        default=15,
        ge=1,
        description="Máximo de oraciones por chunk (fuerza split si se excede)."
    )

    min_chunk_chars: int = Field(
        default=100,
        ge=0,
        description="Chunks más pequeños se fusionan con el anterior."
    )

    max_chunk_chars: int = Field(
        default=2000,
        ge=1,
        description="Chunks más grandes se fuerzan a dividir."
    )

    combine_short_sentences: bool = Field(
        default=True,
        description="Si True, combina oraciones muy cortas antes del análisis."
    )

    short_sentence_threshold: int = Field(
        default=20,
        ge=0,
        description="Oraciones con menos caracteres se consideran 'cortas'."
    )

    batch_size: int = Field(
        default=32,
        ge=1,
        description="Batch size para encoding de embeddings."
    )
