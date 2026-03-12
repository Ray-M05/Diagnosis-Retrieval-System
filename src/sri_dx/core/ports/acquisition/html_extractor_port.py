from __future__ import annotations

from typing import Optional, Protocol

from sri_dx.core.schemas.acquisition.acquired_document import Section


class HtmlExtractorPort(Protocol):
    """Puerto: extractor de contenido HTML estructurado."""

    def extract(
        self, url: str, html: bytes
    ) -> tuple[Optional[str], list[Section], str, list[str], dict]: ...
