"""Service orchestration for clinical positioning."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sri_dx.modules.positioning.adapters import candidates_from_retrieval_results
from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.evidence import select_top_evidences
from sri_dx.modules.positioning.explanations import generate_explanation, relevance_label
from sri_dx.modules.positioning.grouping import group_candidates
from sri_dx.modules.positioning.mmr import mmr_rerank
from sri_dx.modules.positioning.models import PositionedClinicalResult
from sri_dx.modules.positioning.scoring import (
    normalize_candidate_scores,
    score_clinical_groups,
)


class ClinicalPositioningService:
    """Position clinical conditions from already retrieved and reranked chunks."""

    def __init__(self, config: PositioningConfig | None = None) -> None:
        self.config = config or PositioningConfig()

    def position(
        self,
        query: str,
        retrieval_results: list[Any],
        top_k: int | None = None,
        reference_date: datetime | None = None,
    ) -> list[PositionedClinicalResult]:
        """Return positioned clinical condition results."""

        if not retrieval_results:
            return []

        candidates = candidates_from_retrieval_results(retrieval_results)
        candidates = normalize_candidate_scores(candidates)
        groups = group_candidates(candidates, self.config)
        if not groups:
            return []

        scored_groups = score_clinical_groups(query, groups, self.config, reference_date)
        ranked_groups = mmr_rerank(
            scored_groups,
            top_k or self.config.top_k,
            self.config.lambda_mmr,
        )

        results: list[PositionedClinicalResult] = []
        for rank, group in enumerate(ranked_groups, start=1):
            evidences = select_top_evidences(group, self.config)
            group.explanation = generate_explanation(group)
            component_scores = dict(group.component_scores)
            component_scores["mmr"] = round(group.mmr_score, 6)

            results.append(
                PositionedClinicalResult(
                    rank=rank,
                    disease_name=group.disease_name,
                    disease_name_display=group.display_name,
                    final_score=group.relevance_score,
                    relevance_label=relevance_label(group),
                    matched_symptoms=list(group.matched_symptoms),
                    evidences=evidences,
                    explanation=list(group.explanation),
                    source_domains=list(group.source_domains),
                    component_scores=component_scores,
                )
            )

        return results
