"""Ranking Module - Re-ranking de Resultados

Módulo para re-ordenar y filtrar resultados de búsqueda.

Componentes implementados:
- RRF (Reciprocal Rank Fusion): Fusión de rankings múltiples ✅
- Weighted Sum: Suma ponderada de scores ✅
- Borda Count: Sistema de votación Borda ✅
- Interleave: Entrelazado round-robin ✅

Componentes por implementar:
- MedicalReranker: Re-ranking basado en criterios médicos
- CrossEncoderReranker: Re-ranking usando cross-encoders
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

__all__ = [
    "reciprocal_rank_fusion",
    "weighted_sum_fusion",
    "borda_count_fusion",
    "interleave_rankings",
    "get_unique_results",
    "RankedItem",
]
