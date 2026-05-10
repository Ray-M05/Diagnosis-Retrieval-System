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
) -> dict:
    canonical_url = normalize_url(ext.canonical_url)
    clean_secs = clean_sections(ext.sections)

    body = build_body_from_sections(clean_secs)
    if not body and ext.abstract_or_summary:
        body = clean_text(ext.abstract_or_summary)
    if not body:
        body = clean_text(ext.title)

    ch = compute_content_hash(body)
    doc_id = doc_id_from_url(canonical_url)

    # source_meta is stored as an extra section so it remains within the
    # existing AcquiredDocument schema (no schema changes needed).
    from sri_dx.core.schemas.acquisition.acquired_document import Section
    meta_parts = [f"API source: {ext.source}"]
    if ext.pmid:
        meta_parts.append(f"PMID: {ext.pmid}")
    if ext.pmcid:
        meta_parts.append(f"PMCID: {ext.pmcid}")
    if ext.doi:
        meta_parts.append(f"DOI: {ext.doi}")
    if ext.journal:
        meta_parts.append(f"Journal: {ext.journal}")
    if ext.mesh_terms:
        meta_parts.append(f"MeSH: {', '.join(ext.mesh_terms)}")
    meta_parts.append(f"Query: {original_query}")

    meta_section = Section(heading="Source metadata", text="; ".join(meta_parts))
    all_secs = clean_secs + [meta_section]

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
                for s in all_secs
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
