from __future__ import annotations

import re
import unicodedata
from html import unescape
from sri_dx.core.schemas.acquisition.acquired_document import Section

_ws = re.compile(r"[ \t]+")
_nl = re.compile(r"\n{2,}")
_html_break = re.compile(r"</?(?:p|div|br|li|ul|ol|h[1-6]|section|article|tr|td|th)\b[^>]*>", re.IGNORECASE)
_html_tag = re.compile(r"<[^>]+>")


def clean_text(text: str) -> str:
    """
    Normalización básica:
    - unicode NFKC
    - saltos de línea consistentes
    - colapsa espacios repetidos
    - colapsa bloques enormes de saltos de línea
    """
    if not text:
        return ""

    t = unescape(text)
    t = _html_break.sub("\n", t)
    t = _html_tag.sub("", t)
    t = unicodedata.normalize("NFKC", t)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = _ws.sub(" ", t)
    t = _nl.sub("\n", t)
    return t.strip()


def clean_sections(sections: list[Section]) -> list[Section]:
    """
    Limpia headings/text. Elimina secciones vacías.
    """
    cleaned: list[Section] = []
    for s in sections:
        heading = clean_text(s.heading) if s.heading else "main"
        body = clean_text(s.text)
        if body:
            cleaned.append(Section(heading=heading or "main", text=body))
    return cleaned


def build_body_from_sections(sections: list[Section]) -> str:
    """
    Construye un body estable a partir de secciones limpias.
    No depende del extractor.
    """
    parts: list[str] = []
    for s in sections:
        if s.heading and s.heading.lower() != "main":
            parts.append(s.heading)
        parts.append(s.text)
    return clean_text("\n\n".join(parts))
