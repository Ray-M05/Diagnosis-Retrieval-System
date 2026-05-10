"""Adapters from retrieval pipeline objects into positioning models."""

from __future__ import annotations

from typing import Any, Iterable

from sri_dx.modules.positioning.models import PositioningCandidate


def _metadata(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _first_text(result: Any, metadata: dict[str, Any]) -> str:
    for value in (
        getattr(result, "content", None),
        metadata.get("content"),
        metadata.get("chunk_text"),
        metadata.get("chunk_text_preview"),
    ):
        if value:
            return str(value)
    return ""


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def candidates_from_retrieval_results(
    retrieval_results: Iterable[Any],
) -> list[PositioningCandidate]:
    """Build positioning candidates from objects compatible with RetrievalResult."""

    candidates: list[PositioningCandidate] = []

    for result in retrieval_results:
        metadata = _metadata(result)
        doc_id = str(getattr(result, "doc_id", metadata.get("doc_id", "")) or "")
        chunk_id = str(metadata.get("chunk_id") or getattr(result, "chunk_id", None) or doc_id)

        concept_ids = metadata.get("concept_ids") or []
        if not isinstance(concept_ids, list):
            concept_ids = []

        ner_entities = metadata.get("ner_entities") or []
        if not isinstance(ner_entities, list):
            ner_entities = []

        candidates.append(
            PositioningCandidate(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=_first_text(result, metadata),
                title=metadata.get("title"),
                url=metadata.get("url"),
                source_domain=metadata.get("source_domain"),
                section_heading=metadata.get("section_heading"),
                section_index=metadata.get("section_index"),
                chunk_index=metadata.get("chunk_index"),
                fetched_at=metadata.get("fetched_at"),
                published_at=metadata.get("published_at"),
                updated_at=metadata.get("updated_at"),
                mime_type=metadata.get("mime_type"),
                seed_group=metadata.get("seed_group"),
                lexical_score=_optional_float(getattr(result, "lexical_score", None)),
                vector_score=_optional_float(getattr(result, "vector_score", None)),
                hybrid_score=_optional_float(
                    getattr(result, "original_hybrid_score", getattr(result, "score", None))
                ),
                cross_encoder_score=_optional_float(
                    getattr(result, "rerank_score", metadata.get("rerank_score"))
                ),
                concept_ids=[str(c) for c in concept_ids],
                ner_entities=[e for e in ner_entities if isinstance(e, dict)],
                embedding=metadata.get("embedding"),
                metadata=dict(metadata),
            )
        )

    return candidates
