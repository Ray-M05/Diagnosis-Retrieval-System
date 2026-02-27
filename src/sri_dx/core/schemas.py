from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class Section:
    heading: str
    text: str


@dataclass(frozen=True)
class CrawlMeta:
    depth: int
    parent_url: Optional[str]
    seed_id: str
    seed_group: str


@dataclass(frozen=True)
class PageMeta:
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None


@dataclass(frozen=True)
class Content:
    mime_type: str                 # "text/html" | "application/pdf"
    title: Optional[str]
    sections: List[Section]
    body: str


@dataclass(frozen=True)
class AcquiredDocument:
    """
    Representa EXACTAMENTE lo que viene del JSONL del módulo de adquisición.
    """
    doc_id: str
    url: str
    source_domain: str
    fetched_at: str                # ISO-8601 UTC string
    crawl: CrawlMeta
    content: Content
    page_meta: Optional[PageMeta] = None
    content_hash: Optional[str] = None


@dataclass(frozen=True)
class IndexDocument:
    """
    Documento listo para indexación (forma interna).
    Importante: no inventa semántica clínica; solo prepara campos y derivados.
    """
    doc_id: str
    url: str
    source_domain: str
    fetched_at: str

    mime_type: str
    title: str
    body: str
    sections_text: str

    # Facets/filtros derivables desde el contrato de adquisición
    seed_group: str
    seed_id: str
    depth: int

    # Metadatos opcionales
    language: Optional[str]
    published_at: Optional[str]
    updated_at: Optional[str]
    author: Optional[str]

    # Para incrementalidad
    content_hash: str

    # Estadísticas útiles (debug + features futuras)
    char_len: int
    word_count: int
    section_count: int