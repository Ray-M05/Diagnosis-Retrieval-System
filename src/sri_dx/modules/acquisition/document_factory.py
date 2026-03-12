from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from .models import CrawlTask
from sri_dx.core.schemas.acquisition.acquired_document import Section
from .urls import get_domain, normalize_url
from .cleaning import clean_text, clean_sections, build_body_from_sections


def iso_utc(dt: datetime) -> str:
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def doc_id_from_url(url: str) -> str:
    """
    ID estable: hash de URL normalizada.
    (Truncado para que sea corto; suficiente para el proyecto.)
    """
    u = normalize_url(url)
    return hashlib.sha1(u.encode("utf-8", errors="ignore")).hexdigest()[:16]


def content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()


def build_document(
    *,
    task: CrawlTask,
    final_url: str,
    mime_type: str,
    fetched_at: datetime,
    title: Optional[str],
    sections: list[Section],
    body: str,
    page_meta_partial: Optional[dict] = None,
) -> dict:
    """
    Construye el documento final (dict) con el esquema JSONL acordado.
    No incluye parser/canonical/acquisition_tags/integrity.
    """
    page_meta_partial = page_meta_partial or {}

    url_norm = normalize_url(final_url)
    secs = clean_sections(sections)
    b = clean_text(body) if body else build_body_from_sections(secs)
    if not b:
        # último recurso: body desde secciones (por si body vacío)
        b = build_body_from_sections(secs)

    ch = content_hash(b)

    # Si no hay secciones, crea una main
    if not secs:
        secs = [Section(heading="main", text=b)]

    return {
        "doc_id": doc_id_from_url(url_norm),
        "url": url_norm,
        "source_domain": get_domain(url_norm),
        "fetched_at": iso_utc(fetched_at),
        "crawl": {
            "depth": task.depth,
            "parent_url": task.parent_url,
            "seed_id": task.seed_id,
            "seed_group": task.seed_group,
        },
        "content": {
            "mime_type": mime_type,
            "title": title.strip() if isinstance(title, str) and title.strip() else None,
            "sections": [{"heading": s.heading, "text": s.text} for s in secs],
            "body": b,
        },
        "page_meta": {
            "published_at": page_meta_partial.get("published_at"),
            "updated_at": page_meta_partial.get("updated_at"),
            "author": page_meta_partial.get("author"),
            "language": page_meta_partial.get("language"),
        },
        "content_hash": ch,
    }