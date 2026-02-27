from __future__ import annotations
from typing import Optional, Protocol
from .models import FetchResult, Section


class HttpClient(Protocol):
    """Puerto: cliente HTTP (requests/httpx en adapters)."""
    def get(self, url: str, *, timeout_s: float) -> FetchResult: ...


class RobotsPolicy(Protocol):
    """Puerto: política robots.txt (cache por dominio en adapters)."""
    def allowed(self, url: str, user_agent: str) -> bool: ...


class HtmlExtractor(Protocol):
    """
    Puerto: extractor HTML.
    Retorna:
      - title (best-effort)
      - sections (por headings si es posible)
      - body (texto principal)
      - out_links (hrefs descubiertos)
      - page_meta_partial (solo metadatos explícitos: author/fechas/lang)
    """
    def extract(
        self, url: str, html: bytes
    ) -> tuple[Optional[str], list[Section], str, list[str], dict]: ...


class PdfExtractor(Protocol):
    """
    Puerto: extractor PDF.
    Retorna:
      - title (best-effort)
      - sections (mínimo main)
      - body
      - page_meta_partial
    """
    def extract(
        self, url: str, pdf: bytes
    ) -> tuple[Optional[str], list[Section], str, dict]: ...


class JsonlSink(Protocol):
    """Puerto: persistencia JSONL (append 1 doc por línea)."""
    def write(self, doc: dict) -> None: ...