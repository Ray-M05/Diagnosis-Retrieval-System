"""Symptom and concept coverage scoring."""

from __future__ import annotations

import re

from sri_dx.modules.positioning.models import ClinicalGroup


CONCEPT_DISPLAY = {
    "DYSPNEA": "shortness of breath",
    "CHEST_PAIN": "chest pain",
    "FEVER": "fever",
    "TACHYCARDIA": "tachycardia",
    "HYPERTENSION": "hypertension",
    "DIABETES": "diabetes",
    "HYPOXEMIA": "hypoxemia",
}


CONCEPT_ALIASES = {
    "DYSPNEA": [
        "shortness of breath",
        "dyspnea",
        "difficulty breathing",
        "breathlessness",
        "falta de aire",
        "disnea",
    ],
    "CHEST_PAIN": [
        "chest pain",
        "thoracic pain",
        "chest discomfort",
        "dolor toracico",
        "dolor en el pecho",
    ],
    "FEVER": ["fever", "pyrexia", "high temperature", "fiebre"],
    "TACHYCARDIA": ["tachycardia", "palpitations", "taquicardia"],
    "HYPERTENSION": ["hypertension", "high blood pressure", "hipertension"],
    "DIABETES": ["diabetes", "diabetes mellitus"],
    "HYPOXEMIA": ["hypoxemia", "low oxygen saturation", "spo2 baja"],
}


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9áéíóúñü]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _contains_phrase(text_norm: str, phrase: str) -> bool:
    phrase_norm = _normalize_text(phrase)
    if not phrase_norm:
        return False
    return re.search(rf"(^|\s){re.escape(phrase_norm)}($|\s)", text_norm) is not None


def _concepts_from_query(query: str) -> set[str]:
    concepts: set[str] = set()

    try:
        from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor

        concepts.update(ConceptExtractor().extract(query))
    except Exception:
        pass

    query_norm = _normalize_text(query)
    for concept_id, aliases in CONCEPT_ALIASES.items():
        if any(_contains_phrase(query_norm, alias) for alias in aliases):
            concepts.add(concept_id)

    return concepts


def compute_symptom_coverage(
    query: str,
    group: ClinicalGroup,
) -> tuple[float, list[str]]:
    """Compute query symptom/concept coverage for a clinical group."""

    query_concepts = _concepts_from_query(query)
    if not query_concepts:
        return 0.5, []

    evidence_concepts: set[str] = set()
    evidence_text = []
    for evidence in group.evidences:
        evidence_concepts.update(evidence.concept_ids or [])
        evidence_text.append(evidence.text or "")

    evidence_norm = _normalize_text(" ".join(evidence_text))
    matched: list[str] = []

    for concept_id in sorted(query_concepts):
        has_concept = concept_id in evidence_concepts
        has_alias = any(
            _contains_phrase(evidence_norm, alias)
            for alias in CONCEPT_ALIASES.get(concept_id, [])
        )
        if has_concept or has_alias:
            matched.append(CONCEPT_DISPLAY.get(concept_id, concept_id.lower()))

    return len(matched) / len(query_concepts), matched
