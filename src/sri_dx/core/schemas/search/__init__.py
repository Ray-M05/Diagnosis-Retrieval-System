# Schemas para el módulo de Búsqueda
# Modelos de datos para requests y responses de búsqueda

from .search_request import SearchRequest, SearchFilters
from .search_response import SearchResponse, SearchHit
from .search_result_schema import (
    SearchResult,
    LexicalSearchResult,
    VectorSearchResult,
    HybridSearchResult,
)
from .search_query_schema import LexicalQuery, HybridQuery
from .vector_search_schema import EmbeddingSearchResult, EmbeddingStoreConfig

__all__ = [
    "SearchRequest",
    "SearchFilters",
    "SearchResponse",
    "SearchHit",
    "SearchResult",
    "LexicalSearchResult",
    "VectorSearchResult",
    "HybridSearchResult",
    "LexicalQuery",
    "HybridQuery",
    "EmbeddingSearchResult",
    "EmbeddingStoreConfig",
]
