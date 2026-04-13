from pydantic import BaseModel, Field
from typing import Optional


class CrossEncoderConfig(BaseModel):
    """Configuración del cross encoder."""

    model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Nombre del modelo"
    )
    model_version: str = Field(
        default="1.0",
        description="Versión del modelo"
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=512,                         # ← límite superior, evita OOM
        description="Batch size para inferencia"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        description="Número de resultados a retornar tras el reranking"
    )
    max_length: int = Field(
        default=512,
        ge=64,
        le=512,
        description="Longitud máxima de tokens para query+doc concatenados"
    )
    device: str = Field(
        default="cpu",
        pattern="^(cpu|cuda|mps)$",    # ← valida que sea un device válido
        description="Device para inferencia"
    )
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score mínimo para incluir un resultado. None = sin filtro"
    )

    class Config:
        frozen = True