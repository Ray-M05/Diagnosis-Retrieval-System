# Core Ports - Interfaces del Sistema
# Organizados por dominio para fácil navegación

from .acquisition import IndexDocumentSinkPort, DocumentSourcePort, ManifestStorePort
from .search import (
    SearchBackendPort,
    LexicalIndexPort,
    HybridSearchPort,
    SetOperationsPort,
)
from .indexing import ChunkerPort, EmbeddingPort

__all__ = [
    # Acquisition
    "IndexDocumentSinkPort",
    "DocumentSourcePort",
    "ManifestStorePort",
    # Search
    "SearchBackendPort",
    "LexicalIndexPort",
    "HybridSearchPort",
    "SetOperationsPort",
    # Indexing
    "ChunkerPort",
    "EmbeddingPort",
]
