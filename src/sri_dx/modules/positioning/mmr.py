"""Maximal Marginal Relevance for clinical groups."""

from __future__ import annotations

import re

from sri_dx.modules.positioning.models import ClinicalGroup


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _concepts(group: ClinicalGroup) -> set[str]:
    values: set[str] = set()
    for evidence in group.evidences:
        values.update(evidence.concept_ids or [])
    return values


def _domains(group: ClinicalGroup) -> set[str]:
    return set(group.source_domains or [])


def _tokens(group: ClinicalGroup) -> set[str]:
    text = " ".join(e.text for e in group.evidences[:3])
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) >= 3
    }


def group_similarity(group_a: ClinicalGroup, group_b: ClinicalGroup) -> float:
    """Similarity for MMR V1 without embeddings."""

    if group_a.disease_name == group_b.disease_name:
        return 1.0

    concept_sim = _jaccard(_concepts(group_a), _concepts(group_b))
    lexical_sim = _jaccard(_tokens(group_a), _tokens(group_b))
    source_sim = _jaccard(_domains(group_a), _domains(group_b))
    return max(0.0, min(1.0, (0.50 * concept_sim) + (0.30 * lexical_sim) + (0.20 * source_sim)))


def mmr_rerank(
    groups: list[ClinicalGroup],
    top_k: int,
    lambda_mmr: float,
) -> list[ClinicalGroup]:
    """Select diverse groups with MMR."""

    selected: list[ClinicalGroup] = []
    remaining = sorted(groups, key=lambda g: g.relevance_score, reverse=True)

    while remaining and len(selected) < top_k:
        best_group: ClinicalGroup | None = None
        best_score = float("-inf")

        for group in remaining:
            if not selected:
                mmr_score = group.relevance_score
            else:
                redundancy = max(group_similarity(group, chosen) for chosen in selected)
                mmr_score = (lambda_mmr * group.relevance_score) - (
                    (1.0 - lambda_mmr) * redundancy
                )

            if best_group is None or (mmr_score, group.relevance_score) > (
                best_score,
                best_group.relevance_score,
            ):
                best_group = group
                best_score = mmr_score

        if best_group is None:
            break

        best_group.mmr_score = round(best_score, 6)
        selected.append(best_group)
        remaining.remove(best_group)

    return selected
