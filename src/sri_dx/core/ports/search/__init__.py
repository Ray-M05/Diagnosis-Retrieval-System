# Ports para el módulo de Búsqueda
# Interfaces para búsqueda léxica, vectorial e híbrida

from .search_backend import SearchBackendPort
from .lexical_index_port import LexicalIndexPort
from .hybrid_search_port import HybridSearchPort
from .set_operations_port import SetOperationsPort
from .embedding_store_port import EmbeddingStorePort

# Re-export schemas para retrocompatibilidad
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
    "EmbeddingSearchResult",
    "EmbeddingStoreConfig",
]
