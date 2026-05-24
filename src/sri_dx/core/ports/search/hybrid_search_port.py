# core/ports/hybrid_search_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from sri_dx.core.schemas.search.search_query_schema import HybridQuery
from sri_dx.core.schemas.search.search_result_schema import HybridSearchResult

class HybridSearchPort(ABC):
    """
    Port for hybrid search (fusion of vector + lexical).
    """

    @abstractmethod
    def search(
        self,
        query: HybridQuery,
        k: int = 10,
        alpha: float = 0.5,  # Balance between vector and lexical
        filter_criteria: Optional[Dict] = None
    ) -> List[HybridSearchResult]:
        """
        Hybrid search with result fusion.

        Args:
            query: Query with semantic and lexical components
            k: Number of final results
            alpha: Weight (0=lexical only, 1=vector only, 0.5=balanced)
            filter_criteria: Metadata filters

        Returns:
            Fused results with combined scores
        """

    @abstractmethod
    def get_fusion_strategy(self) -> str:
        """Returns the fusion strategy in use (RRF, CombSUM, etc.)."""
        