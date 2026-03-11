# Core Ports - Interfaces del Sistema
# Organizados por dominio para fácil navegación

from .acquisition import (
    IndexDocumentSinkPort,
    DocumentSourcePort,
    ManifestStorePort,
    HttpClientPort,
    RobotsPolicyPort,
    HtmlExtractorPort,
    PdfExtractorPort,
    JsonlSinkPort,
)
from .search import (
    SearchBackendPort,
    LexicalIndexPort,
    HybridSearchPort,
    SetOperationsPort,
)
from .indexing import ChunkerPort, EmbeddingPort

__all__ = [
    # Acquisition (indexing pipeline)
    "IndexDocumentSinkPort",
    "DocumentSourcePort",
    "ManifestStorePort",
    # Acquisition (scraping)
    "HttpClientPort",
    "RobotsPolicyPort",
    "HtmlExtractorPort",
    "PdfExtractorPort",
    "JsonlSinkPort",
    # Search
    "SearchBackendPort",
    "LexicalIndexPort",
    "HybridSearchPort",
    "SetOperationsPort",
    # Indexing
    "ChunkerPort",
    "EmbeddingPort",
]
