# Core Schemas - Modelos de Datos del Sistema
# Organizados por dominio para fácil navegación

from .acquisition import (
    AcquiredDocument,
    CrawlMeta,
    Content,
    PageMeta,
    Section,
    FetchResult,
)
from .indexing import (
    ChunkDocument,
    IndexDocument,
    ChunkingConfig,
)
from .search import (
    SearchRequest,
    SearchResponse,
    SearchHit,
)

__all__ = [
    # Acquisition
    "AcquiredDocument",
    "CrawlMeta",
    "Content",
    "PageMeta",
    "Section",
    "FetchResult",
    # Indexing
    "ChunkDocument",
    "IndexDocument",
    "ChunkingConfig",
    # Search
    "SearchRequest",
    "SearchResponse",
    "SearchHit",
]
