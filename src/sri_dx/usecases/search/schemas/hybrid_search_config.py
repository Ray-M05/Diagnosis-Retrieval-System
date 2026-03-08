"""Schemas para configuración de búsqueda híbrida."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class HybridSearchConfig(BaseModel):
    """Configuración para SearchHybridUseCase.

    Campos equivalentes a la antigua dataclass, ahora como Pydantic model.
    """

    model_config = ConfigDict(title="HybridSearchConfig")

    fusion_method: str = "rrf"
    lexical_weight: float = 0.5
    semantic_weight: float = 0.5
    rrf_k: int = 60
    lexical_k: int = 100
    semantic_k: int = 100
    min_semantic_score: float = 0.3
    normalize_scores: bool = True
