from __future__ import annotations

from typing import Optional
from bs4 import BeautifulSoup

from sri_dx.modules.acquisition.models import Section


def _safe_text(el) -> str:
    """Texto “plano” estable."""
    return " ".join(el.get_text(" ", strip=True).split())


def _pick_main_container(soup: BeautifulSoup):
    """
    Heurística simple para reducir ruido:
    prioriza <article> o <main>, luego <body>.
    """
    for tag in ("article", "main"):
        found = soup.find(tag)
        if found:
            return found
    return soup.body or soup


class SimpleHtmlExtractor:
    """
    Extractor HTML minimalista (offline):
    - title: og:title -> <title> -> <h1>
    - sections: headings (h1/h2/h3) + texto de p/li bajo cada heading
    - body: concatenación estable de secciones (fallback: texto del container)
    - out_links: href de <a>
    - page_meta_partial: lang/author/published/updated si son explícitos
    """

    def extract(
        self, url: str, html: bytes
    ) -> tuple[Optional[str], list[Section], str, list[str], dict]:
        soup = BeautifulSoup(html, "lxml")
        container = _pick_main_container(soup)

        # ---- title (best-effort)
        title: Optional[str] = None
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            title = str(og["content"]).strip()
        elif soup.title and soup.title.string:
            title = str(soup.title.string).strip()
        else:
            h1 = container.find("h1") if container else soup.find("h1")
            title = _safe_text(h1) if h1 else None

        # ---- out links (sin filtrar aquí; el módulo los filtrará)
        out_links: list[str] = []
        for a in container.find_all("a", href=True):
            href = str(a.get("href", "")).strip()
            if href:
                out_links.append(href)

        # ---- sections por headings
        sections: list[Section] = []
        current_heading = "main"
        current_parts: list[str] = []

        def flush():
            nonlocal current_parts, current_heading
            txt = " ".join(current_parts).strip()
            if txt:
                sections.append(Section(heading=current_heading, text=txt))
            current_parts = []

        # Recorremos headings + texto típico
        for el in container.find_all(["h1", "h2", "h3", "p", "li"]):
            if el.name in {"h1", "h2", "h3"}:
                flush()
                h = _safe_text(el)
                current_heading = h if h else "main"
            else:
                t = _safe_text(el)
                if t:
                    current_parts.append(t)
        flush()

        # ---- body (fallback si no hay secciones)
        if sections:
            parts = []
            for s in sections:
                if s.heading and s.heading.lower() != "main":
                    parts.append(s.heading)
                parts.append(s.text)
            body = "\n\n".join(parts)
        else:
            body = _safe_text(container)

        # ---- page_meta_partial (solo explícito)
        page_meta: dict = {}

        # language
        if soup.html and soup.html.get("lang"):
            lang = str(soup.html.get("lang")).strip()
            if lang:
                page_meta["language"] = lang.split("-")[0].lower()

        # author
        author = soup.find("meta", attrs={"name": "author"})
        if author and author.get("content"):
            page_meta["author"] = str(author["content"]).strip()

        # published/updated (metas comunes)
        pub = soup.find("meta", attrs={"property": "article:published_time"})
        if pub and pub.get("content"):
            page_meta["published_at"] = str(pub["content"]).strip()

        upd = soup.find("meta", attrs={"property": "article:modified_time"})
        if upd and upd.get("content"):
            page_meta["updated_at"] = str(upd["content"]).strip()

        return title, sections, body, out_links, page_meta