# Ports for the Search module
# Interfaces for lexical, vector, and hybrid search

from .search_backend import SearchBackendPort
from .lexical_index_port import LexicalIndexPort
from .hybrid_search_port import HybridSearchPort
from .set_operations_port import SetOperationsPort
from .embedding_store_port import EmbeddingStorePort
from .cross_encoder_port import CrossEncoderPort

# Re-export schemas for backwards compatibility
from sri_dx.core.schemas.search.vector_search_schema import (
    EmbeddingSearchResult,
    EmbeddingStoreConfig,
)

__all__ = [
    "SearchBackendPort",
    "LexicalIndexPort",
    "HybridSearchPort",
    "SetOperationsPort",
    "EmbeddingStorePort",
    "CrossEncoderPort",
    "EmbeddingSearchResult",
    "EmbeddingStoreConfig",
]
