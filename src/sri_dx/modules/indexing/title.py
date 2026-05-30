"""Deterministic title derivation shared by indexing and the API layer.

The docs index must always carry a non-empty ``title`` so cards can render a
header. When a document has no explicit title we derive one from its URL path,
skipping noise slugs (e.g. ``syc-20352557``, ``PMC1234``, ``symptoms-causes``).

This is the single source of truth for URL→title slugging; ``app.api.main``
re-exports a thin wrapper so display and indexing stay consistent.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

_SLUG_NOISE_PATTERNS = (
    re.compile(r"^syc[\s\-_]?\d+$", re.IGNORECASE),
    re.compile(r"^pmc\d+$", re.IGNORECASE),
    re.compile(r"^\d+$"),
    re.compile(r"^(symptoms?[\s\-_]causes?|causes?|symptoms?|diagnosis|treatment|prevention)$", re.IGNORECASE),
    re.compile(r"^(health[\s\-_]topics?|article|ency|medlineplus)$", re.IGNORECASE),
)


def is_noise_slug(slug: str) -> bool:
    s = slug.replace("-", " ").replace("_", " ").strip()
    return any(p.match(s) for p in _SLUG_NOISE_PATTERNS)


def title_from_url(url: str | None) -> str | None:
    """Best-effort human title from a URL path.

    Walks path segments from the end, returning the first non-noise slug
    title-cased. Falls back to the last segment if all are noise. Returns
    ``None`` when no usable slug exists.
    """
    if not url:
        return None
    try:
        path = urlparse(url).path.strip("/")
        if not path:
            return None
        segments = [s for s in path.split("/") if s]
        for seg in reversed(segments):
            seg_clean = re.sub(r"\.(html?|aspx?|php)$", "", seg, flags=re.IGNORECASE)
            if is_noise_slug(seg_clean):
                continue
            slug = seg_clean.replace("-", " ").replace("_", " ").strip()
            if slug:
                return slug.title()
        slug = segments[-1].replace("-", " ").replace("_", " ").strip()
        return slug.title() if slug else None
    except Exception:
        return None


def humanize_doc_id(doc_id: str | None) -> str:
    """Last-resort readable label from a doc id (used only when all else fails)."""
    if not doc_id:
        return "Untitled document"
    return f"Document {str(doc_id)[:8]}"


def derive_title(
    *,
    explicit_title: str | None,
    section_headings: list[str] | None = None,
    url: str | None = None,
    source_domain: str | None = None,
    doc_id: str | None = None,
) -> str:
    """Resolve a guaranteed non-empty title via a deterministic fallback chain.

    Order: explicit title → first non-empty section heading → URL-derived
    title → source domain → humanized doc id.
    """
    if explicit_title and explicit_title.strip():
        return explicit_title.strip()

    for heading in section_headings or []:
        if heading and heading.strip() and heading.strip().lower() not in ("main", "summary"):
            return heading.strip()

    from_url = title_from_url(url)
    if from_url:
        return from_url

    if source_domain and source_domain.strip():
        return source_domain.strip()

    return humanize_doc_id(doc_id)
