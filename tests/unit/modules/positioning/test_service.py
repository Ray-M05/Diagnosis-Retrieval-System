from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.service import ClinicalPositioningService


@dataclass
class FakeRetrievalResult:
    doc_id: str
    rerank_score: float
    original_hybrid_score: float
    lexical_score: float | None
    vector_score: float | None
    metadata: dict[str, Any]
    content: str


def _result(chunk_id: str, disease: str, score: float, text: str, concepts: list[str]):
    return FakeRetrievalResult(
        doc_id=f"{chunk_id}-doc",
        rerank_score=score,
        original_hybrid_score=score / 2,
        lexical_score=score * 10,
        vector_score=score,
        content=text,
        metadata={
            "chunk_id": chunk_id,
            "title": disease,
            "url": f"https://www.cdc.gov/{disease.lower().replace(' ', '-')}",
            "source_domain": "cdc.gov",
            "section_heading": "Symptoms",
            "fetched_at": "2026-01-01T00:00:00Z",
            "concept_ids": concepts,
            "ner_entities": [
                {"label": "PROBLEM", "text": disease, "score": 0.95},
            ],
        },
    )


def test_positioning_service_groups_scores_and_returns_ranked_results():
    service = ClinicalPositioningService(PositioningConfig(top_k=2, top_evidences=2))
    results = [
        _result("c1", "Pneumonia", 0.95, "Fever cough and dyspnea are common.", ["FEVER", "DYSPNEA"]),
        _result("c2", "Pneumonia", 0.85, "Diagnosis considers respiratory symptoms.", ["DYSPNEA"]),
        _result("c3", "Fracture", 0.40, "Bone pain after trauma.", []),
    ]

    positioned = service.position(
        "fever and shortness of breath",
        results,
        reference_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    assert len(positioned) == 2
    assert positioned[0].rank == 1
    assert positioned[0].disease_name == "pneumonia"
    assert positioned[0].evidences
    assert "cross_encoder" in positioned[0].component_scores
    assert set(positioned[0].matched_symptoms) == {"fever", "shortness of breath"}


def test_positioning_service_falls_back_without_ner():
    service = ClinicalPositioningService(PositioningConfig(top_k=1))
    result = FakeRetrievalResult(
        doc_id="doc-1",
        rerank_score=0.7,
        original_hybrid_score=0.3,
        lexical_score=None,
        vector_score=None,
        content="General article about asthma.",
        metadata={
            "chunk_id": "chunk-1",
            "title": "Asthma",
            "source_domain": "mayoclinic.org",
            "concept_ids": [],
        },
    )

    positioned = service.position("wheezing", [result])

    assert positioned[0].disease_name == "asthma"
    assert positioned[0].relevance_label in {"Alta", "Media", "Baja"}


def test_positioning_service_empty_results():
    assert ClinicalPositioningService().position("fever", []) == []
