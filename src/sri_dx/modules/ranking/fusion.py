# modules/ranking/fusion.py
"""Utilidades para fusión de rankings (RRF, weighted sum, etc.)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RankedItem(Generic[T]):
    """Item con score y ranking."""
    item: T
    score: float
    rank: int
    source: str  # 'lexical', 'semantic', etc.


def reciprocal_rank_fusion(
    rankings: List[List[str]],
    k: int = 60,
    scores: Optional[List[List[float]]] = None
) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF) - Combina múltiples rankings.
    
    Formula: RRF_score(d) = sum_r ( 1 / (k + rank_r(d)) )
    donde rank_r(d) es la posición del documento d en el ranking r.
    
    Args:
        rankings: Lista de rankings (cada ranking es lista de doc_ids ordenados)
        k: Constante de RRF (default=60, usado en papers)
        scores: Scores originales (opcional, solo para logging)
        
    Returns:
        Lista de (doc_id, rrf_score) ordenada por score descendente
        
    Ref: Cormack et al. "Reciprocal Rank Fusion outperforms Condorcet and
         individual Rank Learning" (SIGIR 2009)
    """
    if not rankings:
        return []
    
    rrf_scores: Dict[str, float] = {}
    
    # Calcular RRF para cada documento
    for ranking_idx, ranking in enumerate(rankings):
        for position, doc_id in enumerate(ranking):
            rank = position + 1  # 1-indexed
            rrf_contribution = 1.0 / (k + rank)
            
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
            
            rrf_scores[doc_id] += rrf_contribution
    
    # Ordenar por score descendente
    sorted_items = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    logger.debug(
        f"RRF fusion: {len(rankings)} rankings → "
        f"{len(rrf_scores)} docs únicos"
    )
    
    return sorted_items


def weighted_sum_fusion(
    rankings_with_scores: List[Tuple[List[str], List[float]]],
    weights: Optional[List[float]] = None,
    normalize: bool = True
) -> List[Tuple[str, float]]:
    """
    Fusión por suma ponderada de scores.
    
    Args:
        rankings_with_scores: Lista de (ranking, scores) pares
        weights: Pesos para cada ranking (default: iguales)
        normalize: Si True, normaliza scores a [0,1] antes de combinar
        
    Returns:
        Lista de (doc_id, combined_score) ordenada descendente
    """
    if not rankings_with_scores:
        return []
    
    n_rankings = len(rankings_with_scores)
    
    # Pesos por defecto (iguales)
    if weights is None:
        weights = [1.0 / n_rankings] * n_rankings
    
    if len(weights) != n_rankings:
        raise ValueError(
            f"Número de pesos ({len(weights)}) != "
            f"número de rankings ({n_rankings})"
        )
    
    combined_scores: Dict[str, float] = {}
    
    for (ranking, scores), weight in zip(rankings_with_scores, weights):
        # Normalizar scores si es necesario
        if normalize and scores:
            max_score = max(scores) if scores else 1.0
            if max_score > 0:
                normalized_scores = [s / max_score for s in scores]
            else:
                normalized_scores = scores
        else:
            normalized_scores = scores
        
        # Sumar scores ponderados
        for doc_id, score in zip(ranking, normalized_scores):
            if doc_id not in combined_scores:
                combined_scores[doc_id] = 0.0
            
            combined_scores[doc_id] += weight * score
    
    # Ordenar por score descendente
    sorted_items = sorted(
        combined_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    logger.debug(
        f"Weighted sum fusion: {n_rankings} rankings → "
        f"{len(combined_scores)} docs únicos"
    )
    
    return sorted_items


def borda_count_fusion(
    rankings: List[List[str]],
    max_points: Optional[int] = None
) -> List[Tuple[str, float]]:
    """
    Fusión por Borda Count.
    
    Cada ranking otorga puntos: mejor ranking obtiene más puntos.
    
    Args:
        rankings: Lista de rankings ordenados
        max_points: Puntos para el primer lugar (default: len del ranking más largo)
        
    Returns:
        Lista de (doc_id, borda_score) ordenada descendente
    """
    if not rankings:
        return []
    
    if max_points is None:
        max_points = max(len(r) for r in rankings)
    
    borda_scores: Dict[str, float] = {}
    
    for ranking in rankings:
        for position, doc_id in enumerate(ranking):
            points = max_points - position
            
            if doc_id not in borda_scores:
                borda_scores[doc_id] = 0.0
            
            borda_scores[doc_id] += points
    
    # Ordenar por score descendente
    sorted_items = sorted(
        borda_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    logger.debug(
        f"Borda count fusion: {len(rankings)} rankings → "
        f"{len(borda_scores)} docs únicos"
    )
    
    return sorted_items


def get_unique_results(
    rankings: List[List[str]]
) -> Set[str]:
    """Obtiene el conjunto de IDs únicos a través de todos los rankings."""
    unique_ids: Set[str] = set()
    for ranking in rankings:
        unique_ids.update(ranking)
    return unique_ids


def interleave_rankings(
    rankings: List[List[str]],
    max_results: Optional[int] = None
) -> List[str]:
    """
    Interleave (entrelaza) múltiples rankings round-robin.
    
    Útil para diversidad de resultados.
    
    Args:
        rankings: Lista de rankings
        max_results: Número máximo de resultados (optional)
        
    Returns:
        Ranking combinado con docs intercalados
    """
    result = []
    seen: Set[str] = set()
    
    max_len = max(len(r) for r in rankings) if rankings else 0
    
    for position in range(max_len):
        for ranking in rankings:
            if position < len(ranking):
                doc_id = ranking[position]
                if doc_id not in seen:
                    result.append(doc_id)
                    seen.add(doc_id)
                    
                    if max_results and len(result) >= max_results:
                        return result
    
    return result
