"""Scoring functions for clinical positioning."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime
from typing import Iterable, Sequence

from sri_dx.modules.positioning.authority import group_authority_score, normalize_domain
from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.freshness import (
    days_since,
    group_freshness_score,
    parse_optional_datetime,
)
from sri_dx.modules.positioning.models import ClinicalGroup, PositioningCandidate
from sri_dx.modules.positioning.symptoms import compute_symptom_coverage

__all__ = [
    "aggregate_group_signal",
    "days_since",
    "minmax_normalize",
    "normalize_candidate_scores",
    "parse_optional_datetime",
    "score_clinical_group",
    "score_clinical_groups",
    "sigmoid",
]


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def minmax_normalize(values: Sequence[float | None]) -> list[float | None]:
    """Min-max normalize present values and preserve None positions."""

    if not values:
        return []

    present = [float(v) for v in values if v is not None]
    if not present:
        return [None for _ in values]

    min_value = min(present)
    max_value = max(present)
    if max_value == min_value:
        return [1.0 if v is not None else None for v in values]

    return [
        (float(v) - min_value) / (max_value - min_value) if v is not None else None
        for v in values
    ]


def _maybe_sigmoid_scores(values: list[float | None]) -> list[float | None]:
    present = [v for v in values if v is not None]
    if not present:
        return values
    if min(present) < 0.0 or max(present) > 1.0:
        return [sigmoid(v) if v is not None else None for v in values]
    return values


def normalize_candidate_scores(
    candidates: Iterable[PositioningCandidate],
) -> list[PositioningCandidate]:
    """Return candidates with normalized score maps while preserving raw scores."""

    original = list(candidates)
    ce_norm = minmax_normalize(
        _maybe_sigmoid_scores([c.cross_encoder_score for c in original])
    )
    hybrid_norm = minmax_normalize([c.hybrid_score for c in original])
    lexical_norm = minmax_normalize([c.lexical_score for c in original])
    vector_norm = minmax_normalize([c.vector_score for c in original])

    normalized: list[PositioningCandidate] = []
    for index, candidate in enumerate(original):
        normalized_scores = {
            "cross_encoder": ce_norm[index] or 0.0,
            "hybrid": hybrid_norm[index] or 0.0,
            "lexical": lexical_norm[index] or 0.0,
            "vector": vector_norm[index] or 0.0,
        }
        normalized.append(replace(candidate, normalized_scores=normalized_scores))

    return normalized


def aggregate_group_signal(
    scores: Sequence[float | None],
    evidences: Sequence[PositioningCandidate] | None = None,
) -> float:
    """Aggregate per-evidence scores without rewarding long documents too much."""

    present = sorted((float(s) for s in scores if s is not None), reverse=True)
    if not present:
        return 0.0

    best = present[0]
    top_3 = present[:3]
    avg_top_3 = sum(top_3) / len(top_3)

    if evidences:
        unique_chunks = {e.chunk_id for e in evidences}
        density = min(1.0, math.log(1 + len(unique_chunks)) / math.log(1 + 5))
    else:
        density = min(1.0, math.log(1 + len(present)) / math.log(1 + 5))

    return max(0.0, min(1.0, (0.70 * best) + (0.20 * avg_top_3) + (0.10 * density)))


def score_clinical_group(
    query: str,
    group: ClinicalGroup,
    config: PositioningConfig | None = None,
    reference_date: datetime | None = None,
) -> ClinicalGroup:
    cfg = config or PositioningConfig()

    ce_score = aggregate_group_signal(
        [e.normalized_scores.get("cross_encoder") for e in group.evidences],
        group.evidences,
    )
    hybrid_score = aggregate_group_signal(
        [e.normalized_scores.get("hybrid") for e in group.evidences],
        group.evidences,
    )
    coverage_score, matched_symptoms = compute_symptom_coverage(query, group)
    authority_score = group_authority_score(group, cfg)
    freshness_score = group_freshness_score(group, cfg, reference_date)

    components = {
        "cross_encoder": ce_score,
        "hybrid": hybrid_score,
        "symptom_coverage": coverage_score,
        "authority": authority_score,
        "freshness": freshness_score,
    }

    relevance = 0.0
    total_weight = 0.0
    for key, weight in cfg.weights.items():
        relevance += weight * components.get(key, 0.0)
        total_weight += weight
    if total_weight:
        relevance = relevance / total_weight

    domains = sorted(
        {
            normalize_domain(e.source_domain or e.url)
            for e in group.evidences
            if normalize_domain(e.source_domain or e.url)
        }
    )

    group.component_scores = {k: round(max(0.0, min(1.0, v)), 6) for k, v in components.items()}
    group.relevance_score = round(max(0.0, min(1.0, relevance)), 6)
    group.matched_symptoms = matched_symptoms
    group.source_domains = domains
    return group


def score_clinical_groups(
    query: str,
    groups: Iterable[ClinicalGroup],
    config: PositioningConfig | None = None,
    reference_date: datetime | None = None,
) -> list[ClinicalGroup]:
    return [
        score_clinical_group(query, group, config, reference_date)
        for group in groups
    ]
