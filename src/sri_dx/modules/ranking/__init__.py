"""Ranking Module - Re-ranking de Resultados

Módulo para re-ordenar y filtrar resultados de búsqueda.

Componentes implementados:
- RRF (Reciprocal Rank Fusion): Fusión de rankings múltiples ✅
- Weighted Sum: Suma ponderada de scores ✅
- Borda Count: Sistema de votación Borda ✅
- Interleave: Entrelazado round-robin ✅
- CrossEncoderReranker: Re-ranking usando cross-encoders ✅

Componentes por implementar:
- MedicalReranker: Re-ranking basado en criterios médicos
- EvidenceScorer: Scoring por nivel de evidencia

Estado: ✅ PARCIAL
"""

from .fusion import (
    reciprocal_rank_fusion,
    weighted_sum_fusion,
    borda_count_fusion,
    interleave_rankings,
    get_unique_results,
    RankedItem,
)

from .schemas import (
    CrossEncoderConfig,
    RerankRequest,
    RerankResponse,
    RerankResult,
    RerankingError,
    EmptyResultsError,
    MissingContentError,
)

__all__ = [
    # Fusion functions
    "reciprocal_rank_fusion",
    "weighted_sum_fusion",
    "borda_count_fusion",
    "interleave_rankings",
    "get_unique_results",
    "RankedItem",
    # Reranking schemas
    "CrossEncoderConfig",
    "RerankRequest",
    "RerankResponse",
    "RerankResult",
    # Errors
    "RerankingError",
    "EmptyResultsError",
    "MissingContentError",
]
