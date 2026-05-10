from __future__ import annotations

from sri_dx.modules.positioning.mmr import group_similarity, mmr_rerank
from sri_dx.modules.positioning.models import ClinicalGroup, PositioningCandidate


def _group(name: str, score: float, text: str, concepts: list[str]):
    candidate = PositioningCandidate(
        chunk_id=f"{name}-chunk",
        doc_id=f"{name}-doc",
        text=text,
        concept_ids=concepts,
    )
    return ClinicalGroup(
        disease_name=name,
        display_name=name.title(),
        evidences=[candidate],
        relevance_score=score,
        source_domains=["cdc.gov"],
    )


def test_group_similarity_uses_concepts_text_and_sources():
    left = _group("pneumonia", 0.9, "fever cough dyspnea", ["FEVER", "DYSPNEA"])
    right = _group("covid", 0.8, "fever cough dyspnea", ["FEVER", "DYSPNEA"])

    assert group_similarity(left, right) > 0.7


def test_mmr_selects_relevant_then_diverse_group():
    pneumonia = _group("pneumonia", 0.95, "fever cough dyspnea", ["FEVER", "DYSPNEA"])
    covid = _group("covid", 0.93, "fever cough dyspnea", ["FEVER", "DYSPNEA"])
    fracture = _group("fracture", 0.74, "bone pain trauma", ["CHEST_PAIN"])

    ranked = mmr_rerank([pneumonia, covid, fracture], top_k=2, lambda_mmr=0.5)

    assert ranked[0].disease_name == "pneumonia"
    assert ranked[1].disease_name == "fracture"


def test_mmr_high_lambda_prioritizes_relevance():
    pneumonia = _group("pneumonia", 0.95, "fever cough dyspnea", ["FEVER", "DYSPNEA"])
    covid = _group("covid", 0.93, "fever cough dyspnea", ["FEVER", "DYSPNEA"])
    fracture = _group("fracture", 0.74, "bone pain trauma", ["CHEST_PAIN"])

    ranked = mmr_rerank([pneumonia, covid, fracture], top_k=3, lambda_mmr=0.95)

    assert [g.disease_name for g in ranked[:2]] == ["pneumonia", "covid"]
