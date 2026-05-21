"""
Converts :class:`ExternalApiDocument` objects into ``AcquiredDocument``-compatible
dicts that can be written directly to a JSONL file and consumed by
:class:`JsonlDocumentSource`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sri_dx.modules.acquisition.cleaning import (
    build_body_from_sections,
    clean_sections,
    clean_text,
)
from sri_dx.modules.acquisition.document_factory import (
    content_hash as compute_content_hash,
    doc_id_from_url,
    iso_utc,
)
from sri_dx.modules.acquisition.urls import get_domain, normalize_url
from sri_dx.modules.web_search.schemas import ExternalApiDocument

logger = logging.getLogger(__name__)


def _to_iso(dt: datetime | None) -> str | None:
    """Return an ISO-8601 UTC string or None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return iso_utc(dt)


def external_to_acquired_dict(
    ext: ExternalApiDocument,
    *,
    query_id: str,
    original_query: str,
) -> dict | None:
    canonical_url = normalize_url(ext.canonical_url)
    clean_secs = clean_sections(ext.sections)

    body = build_body_from_sections(clean_secs)
    if not body and ext.abstract_or_summary:
        body = clean_text(ext.abstract_or_summary)
    if not body:
        body = clean_text(ext.title)

    # Reject documents that have no real content (abstract/sections empty).
    # Falling back to the title alone produces near-useless chunks that score
    # poorly and pollute the index when a web search returns stub records.
    has_real_content = bool(
        any(s.text.strip() for s in clean_secs if s.heading not in ("Publication metadata", "MeSH terms", "Journal"))
        or (ext.abstract_or_summary and ext.abstract_or_summary.strip())
    )
    if not has_real_content:
        logger.debug(
            "converters: skipping '%s' — no abstract or section content", ext.canonical_url
        )
        return None

    ch = compute_content_hash(body)
    doc_id = doc_id_from_url(canonical_url)

    return {
        "doc_id": doc_id,
        "url": canonical_url,
        "source_domain": get_domain(canonical_url),
        "fetched_at": iso_utc(datetime.now(tz=timezone.utc)),
        "crawl": {
            "depth": 0,
            "parent_url": None,
            "seed_id": query_id,
            "seed_group": f"api_{ext.source}",
        },
        "content": {
            "mime_type": "application/json",
            "title": clean_text(ext.title) or None,
            "sections": [
                {"heading": s.heading, "text": s.text}
                for s in clean_secs
            ],
            "body": body,
        },
        "page_meta": {
            "published_at": _to_iso(ext.published_at),
            "updated_at": _to_iso(ext.updated_at),
            "author": ", ".join(ext.authors) if ext.authors else None,
            "language": ext.language or "en",
        },
        "content_hash": ch,
    }
