# core/ports/set_operations_port.py
from abc import ABC, abstractmethod
from typing import Dict, List, Callable
from sri_dx.core.schemas.search.search_result_schema import SearchResult


class SetOperationsPort(ABC):
    """Port for set operations over search result lists."""

    @abstractmethod
    def intersect(
        self,
        result_sets: List[List[SearchResult]],
        merge_strategy: str = "max_score"
    ) -> List[SearchResult]:
        """Returns documents present in ALL result sets."""

    @abstractmethod
    def negate(
        self,
        positive_results: List[SearchResult],
        negative_results: List[SearchResult]
    ) -> List[SearchResult]:
        """Returns results in positive that are NOT in negative."""

    @abstractmethod
    def filter_by_metadata(
        self,
        results: List[SearchResult],
        filter_fn: Callable[[Dict], bool]
    ) -> List[SearchResult]:
        """Filters results by a metadata predicate."""

    @abstractmethod
    def filter_by_score_threshold(
        self,
        results: List[SearchResult],
        min_score: float
    ) -> List[SearchResult]:
        """Filters results below the minimum score."""