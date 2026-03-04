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
