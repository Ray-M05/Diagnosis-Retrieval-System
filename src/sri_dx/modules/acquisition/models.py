from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CrawlTask:
    """Unidad de trabajo del crawler."""
    url: str
    depth: int
    parent_url: Optional[str]
    seed_id: str
    seed_group: str


@dataclass(frozen=True)
class FetchResult:
    """Resultado de descargar un recurso (HTML/PDF)."""
    url: str
    status_code: int
    mime_type: str
    content: bytes
    fetched_at: datetime
    headers: dict[str, str]


@dataclass(frozen=True)
class Section:
    """Sección de un documento: heading + texto."""
    heading: str
    text: str