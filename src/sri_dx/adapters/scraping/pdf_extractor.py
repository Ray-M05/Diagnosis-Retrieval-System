from __future__ import annotations
from io import BytesIO
from typing import Optional
from pypdf import PdfReader

from sri_dx.modules.acquisition.models import Section


class SimplePdfExtractor:
    """
    Extractor PDF minimalista (offline):
    - title: metadata del PDF si existe
    - sections: una sección main con el texto
    - body: texto concatenado
    - page_meta_partial: author si viene en metadata (opcional)
    """

    def extract(
        self, url: str, pdf: bytes
    ) -> tuple[Optional[str], list[Section], str, dict]:
        reader = PdfReader(BytesIO(pdf))

        texts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            t = t.strip()
            if t:
                texts.append(t)

        body = "\n\n".join(texts).strip()

        # metadata best-effort
        title: Optional[str] = None
        page_meta: dict = {}

        meta = reader.metadata or {}
        # pypdf suele exponer /Title, /Author, etc.
        try:
            raw_title = getattr(meta, "title", None)
            if raw_title:
                title = str(raw_title).strip()
        except Exception:
            pass

        try:
            raw_author = getattr(meta, "author", None)
            if raw_author:
                page_meta["author"] = str(raw_author).strip()
        except Exception:
            pass

        sections = [Section(heading="main", text=body)] if body else []
        return title, sections, body, page_meta