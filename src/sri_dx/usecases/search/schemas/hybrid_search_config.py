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

    # Reranking configuration
    use_reranking: bool = False
    rerank_top_k: int = 10
    rerank_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_batch_size: int = 32
    rerank_score_threshold: Optional[float] = None
    rerank_content_field: str = "content"
