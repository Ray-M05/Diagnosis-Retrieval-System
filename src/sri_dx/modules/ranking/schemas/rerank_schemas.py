"""Schemas for search result reranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sri_dx.core.schemas.search.search_result_schema import HybridSearchResult


@dataclass(frozen=True)
class RerankRequest:
    """
    Request for reranking hybrid search results.

    Attributes:
        query: Original user query
        results: Hybrid search results to rerank
        top_k: Number of results to return after reranking
        content_field: Metadata field that holds the text content (default: "content")
    """
    query: str
    results: List[HybridSearchResult]
    top_k: int
    content_field: str = "content"


@dataclass(frozen=True)
class RerankResponse:
    """
    Reranking response with reordered results.

    Attributes:
        query: Original query
        ranked_results: Reranked results with new scores
        model_name: Name of the model used for reranking
        model_version: Model version
    """
    query: str
    ranked_results: List[RerankResult]
    model_name: str
    model_version: str


@dataclass(frozen=True)
class RerankResult:
    """
    Individual result after reranking.

    Extends HybridSearchResult with reranking information.

    Attributes:
        original_result: Original hybrid search result
        rerank_score: Score assigned by the cross-encoder
        original_position: Position before reranking (0-based)
        new_position: Position after reranking (0-based)
    """
    original_result: HybridSearchResult
    rerank_score: float
    original_position: int
    new_position: Optional[int] = None  # Assigned after sorting

    @property
    def doc_id(self) -> str:
        """Quick access to doc_id."""
        return self.original_result.doc_id

    @property
    def combined_score(self) -> float:
        """
        Combined hybrid + rerank score.

        Useful for downstream fusion or analysis.
        """
        return (self.original_result.score + self.rerank_score) / 2.0


# Reranking domain exceptions
class RerankingError(Exception):
    """Base error during the reranking process."""


class EmptyResultsError(RerankingError):
    """Attempted to rerank an empty list of results."""


class MissingContentError(RerankingError):
    """Could not extract content from one or more results."""
