"""Schemas para reranking de resultados de búsqueda."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sri_dx.core.schemas.search.search_result_schema import HybridSearchResult


@dataclass(frozen=True)
class RerankRequest:
    """
    Request para reranking de resultados de búsqueda híbrida.
    
    Atributos:
        query: Query original del usuario
        results: Resultados de búsqueda híbrida a rerankear
        top_k: Número de resultados a retornar tras reranking
        content_field: Campo en metadata que contiene el texto (default: "content")
    """
    query: str
    results: List[HybridSearchResult]
    top_k: int
    content_field: str = "content"


@dataclass(frozen=True)
class RerankResponse:
    """
    Response del reranking con resultados reordenados.
    
    Atributos:
        query: Query original
        ranked_results: Resultados rerankeados con nuevo score
        model_name: Nombre del modelo usado para reranking
        model_version: Versión del modelo
    """
    query: str
    ranked_results: List[RerankResult]
    model_name: str
    model_version: str


@dataclass(frozen=True)
class RerankResult:
    """
    Resultado individual tras reranking.
    
    Extiende HybridSearchResult añadiendo información del reranking.
    
    Atributos:
        original_result: Resultado original de búsqueda híbrida
        rerank_score: Score asignado por el cross-encoder
        original_position: Posición antes del reranking (base 0)
        new_position: Posición tras el reranking (base 0)
    """
    original_result: HybridSearchResult
    rerank_score: float
    original_position: int
    new_position: Optional[int] = None  # Se asigna después del sorting
    
    @property
    def doc_id(self) -> str:
        """Acceso rápido al doc_id."""
        return self.original_result.doc_id
    
    @property
    def combined_score(self) -> float:
        """
        Score combinado híbrido + rerank.
        
        Puede ser útil para fusiones posteriores o análisis.
        """
        return (self.original_result.score + self.rerank_score) / 2.0


# Excepciones del dominio de reranking
class RerankingError(Exception):
    """Error base durante el proceso de reranking."""


class EmptyResultsError(RerankingError):
    """Se intentó rerankear una lista vacía de resultados."""


class MissingContentError(RerankingError):
    """No se pudo extraer contenido de uno o más resultados."""
