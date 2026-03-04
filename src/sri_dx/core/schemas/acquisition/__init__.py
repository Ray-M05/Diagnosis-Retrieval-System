# Schemas para el módulo de Acquisition
# Modelos de datos para documentos adquiridos

from .acquired_document import AcquiredDocument, CrawlMeta, Content, PageMeta, Section

__all__ = [
    "AcquiredDocument",
    "CrawlMeta",
    "Content",
    "PageMeta",
    "Section",
]
