from __future__ import annotations

from typing import Optional, Protocol

from sri_dx.core.schemas.acquisition.acquired_document import Section


class PdfExtractorPort(Protocol):
    """Puerto: extractor de contenido PDF estructurado."""

    def extract(
        self, url: str, pdf: bytes
    ) -> tuple[Optional[str], list[Section], str, dict]: ...
