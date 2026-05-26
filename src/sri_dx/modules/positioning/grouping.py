"""Clinical grouping utilities for positioning."""

from __future__ import annotations

import re
from collections import OrderedDict
from urllib.parse import urlparse

from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.models import ClinicalGroup, PositioningCandidate


_ACRONYM_MAP: dict[str, str] = {
    "uti": "urinary tract infection",
    "utis": "urinary tract infection",
    "dka": "diabetic ketoacidosis",
    "copd": "chronic obstructive pulmonary disease",
    "chf": "congestive heart failure",
    "cad": "coronary artery disease",
    "ckd": "chronic kidney disease",
    "htn": "hypertension",
    "mi": "myocardial infarction",
    "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism",
    "tb": "tuberculosis",
    "hiv": "human immunodeficiency virus",
    "aids": "acquired immunodeficiency syndrome",
    "ms": "multiple sclerosis",
    "ra": "rheumatoid arthritis",
    "sle": "systemic lupus erythematosus",
    "gerd": "gastroesophageal reflux disease",
    "ibs": "irritable bowel syndrome",
    "afib": "atrial fibrillation",
    "t2dm": "type 2 diabetes mellitus",
    "t1dm": "type 1 diabetes mellitus",
}


def normalize_disease_name(text: str) -> str:
    """Normalize a disease/condition display string into a stable grouping key."""

    name = (text or "").strip().lower()
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"^\d+\s+", "", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\s+(symptoms?|signs?|disease|disorder|syndrome)\s*$", "", name)
    name = name.strip(" .,:;")
    return _ACRONYM_MAP.get(name, name)


def _slug_from_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return parsed.netloc or None

    slug = path.split("/")[-1]
    slug = re.sub(r"\.[a-zA-Z0-9]+$", "", slug)
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug or None


def _fallback_display(candidate: PositioningCandidate) -> str:
    # Prefer human-readable identifiers over opaque hashes. doc_id is a last
    # resort so the UI never shows raw hex strings to clinicians.
    candidates_in_order = (
        candidate.title,
        candidate.section_heading,
        _slug_from_url(candidate.url),
    )
    for value in candidates_in_order:
        if value and str(value).strip():
            return str(value).strip()
    return "unknown condition"


def _valid_problem_entities(
    candidate: PositioningCandidate,
    config: PositioningConfig,
) -> list[tuple[str, str, float]]:
    entities: list[tuple[str, str, float]] = []

    for entity in candidate.ner_entities:
        if str(entity.get("label", "")).upper() != "PROBLEM":
            continue

        try:
            score = float(entity.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0

        if score < config.min_ner_score:
            continue

        display = str(entity.get("text") or entity.get("word") or "").strip()
        normalized = normalize_disease_name(display)
        if display and normalized:
            entities.append((normalized, display, score))

    deduped: OrderedDict[str, tuple[str, str, float]] = OrderedDict()
    for normalized, display, score in sorted(entities, key=lambda item: item[2], reverse=True):
        deduped.setdefault(normalized, (normalized, display, score))

    return list(deduped.values())[: config.max_diseases_per_chunk]


def group_candidates(
    candidates: list[PositioningCandidate],
    config: PositioningConfig | None = None,
) -> list[ClinicalGroup]:
    """Group positioning candidates by clinical condition."""

    cfg = config or PositioningConfig()
    groups: OrderedDict[str, ClinicalGroup] = OrderedDict()

    for candidate in candidates:
        entities = _valid_problem_entities(candidate, cfg)
        if not entities:
            display = _fallback_display(candidate)
            # Use doc_id as the grouping key so multiple chunks from the same
            # document without NER hits don't produce separate groups.
            key = f"__doc__{candidate.doc_id}" if candidate.doc_id else normalize_disease_name(display)
            entities = [(key, display, 1.0)]

        for normalized, display, _ in entities:
            if not normalized:
                continue

            group = groups.get(normalized)
            if group is None:
                group = ClinicalGroup(disease_name=normalized, display_name=display)
                groups[normalized] = group

            if all(ev.chunk_id != candidate.chunk_id for ev in group.evidences):
                group.evidences.append(candidate)

    return list(groups.values())
