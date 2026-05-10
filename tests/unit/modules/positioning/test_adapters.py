from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sri_dx.modules.positioning.adapters import candidates_from_retrieval_results


@dataclass
class FakeRetrievalResult:
    doc_id: str
    rerank_score: float = 0.8
    original_hybrid_score: float = 0.2
    lexical_score: float | None = None
    vector_score: float | None = None
    metadata: dict[str, Any] | None = None
    content: str | None = None


def test_candidate_adapter_preserves_complete_metadata():
    result = FakeRetrievalResult(
        doc_id="doc-1",
        lexical_score=4.0,
        vector_score=0.7,
        content="primary text",
        metadata={
            "chunk_id": "chunk-1",
            "title": "Pneumonia",
            "url": "https://www.cdc.gov/pneumonia",
            "source_domain": "cdc.gov",
            "section_heading": "Symptoms",
            "section_index": 2,
            "chunk_index": 1,
            "fetched_at": "2026-01-01T00:00:00Z",
            "published_at": "2025-01-01",
            "updated_at": "2026-02-01",
            "mime_type": "text/html",
            "seed_group": "trusted",
            "concept_ids": ["FEVER"],
            "ner_entities": [{"label": "PROBLEM", "text": "Pneumonia", "score": 0.9}],
        },
    )

    candidate = candidates_from_retrieval_results([result])[0]

    assert candidate.chunk_id == "chunk-1"
    assert candidate.doc_id == "doc-1"
    assert candidate.text == "primary text"
    assert candidate.title == "Pneumonia"
    assert candidate.source_domain == "cdc.gov"
    assert candidate.section_heading == "Symptoms"
    assert candidate.fetched_at == "2026-01-01T00:00:00Z"
    assert candidate.cross_encoder_score == 0.8
    assert candidate.hybrid_score == 0.2
    assert candidate.lexical_score == 4.0
    assert candidate.vector_score == 0.7
    assert candidate.concept_ids == ["FEVER"]
    assert candidate.ner_entities[0]["text"] == "Pneumonia"


def test_candidate_adapter_uses_text_fallbacks_and_chunk_id_fallback():
    result = FakeRetrievalResult(
        doc_id="doc-fallback",
        content=None,
        metadata={"chunk_text_preview": "preview text"},
    )

    candidate = candidates_from_retrieval_results([result])[0]

    assert candidate.chunk_id == "doc-fallback"
    assert candidate.text == "preview text"


def test_candidate_adapter_tolerates_missing_metadata():
    result = FakeRetrievalResult(doc_id="doc-empty", metadata=None, content=None)

    candidate = candidates_from_retrieval_results([result])[0]

    assert candidate.chunk_id == "doc-empty"
    assert candidate.text == ""
    assert candidate.concept_ids == []
    assert candidate.ner_entities == []
