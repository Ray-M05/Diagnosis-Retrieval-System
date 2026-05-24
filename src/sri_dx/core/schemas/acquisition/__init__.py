# Schemas for the Acquisition module
# Data models for acquired documents

from .acquired_document import AcquiredDocument, CrawlMeta, Content, PageMeta, Section
from .fetch_result import FetchResult

__all__ = [
    "AcquiredDocument",
    "CrawlMeta",
    "Content",
    "PageMeta",
    "Section",
    "FetchResult",
]
