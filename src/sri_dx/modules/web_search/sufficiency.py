"""
Evaluates whether the local hybrid retrieval result is good enough to
answer the user's query, or whether web search should be triggered.

Four criteria are checked independently; any single failure triggers
web search (OR logic — appropriate for clinical use cases where any
gap can compromise quality).

"""
from __future__ import annotations

import logging
import math

from sri_dx.modules.web_search.schemas import (
    LocalRetrievalResult,
    RetrievedChunkResult,
    SufficiencyDecision,
)

logger = logging.getLogger(__name__)


# Score helpers

def _sigmoid(x: float) -> float:
    """Map a real-valued logit to [0, 1]."""
    return 1.0 / (1.0 + math.exp(-x))


def _normalise_score(score: float) -> float:
    """
    Best-effort normalisation of a final retrieval score to [0, 1].

    If the score is already in [0, 1] it is returned as-is.
    If it looks like a raw cross-encoder logit (outside [0, 1]) it is
    passed through sigmoid.
    """
    if 0.0 <= score <= 1.0:
        return score
    return _sigmoid(score)


# Individual criterion functions

def _rank_confidence(results: list[RetrievedChunkResult]) -> float:
    """Return the normalised score of the top-ranked chunk (0 if empty)."""
    if not results:
        return 0.0
    return _normalise_score(results[0].final_score)


def _useful_document_count(
    results: list[RetrievedChunkResult],
    theta_useful_doc_score: float,
) -> int:
    """
    Count distinct documents whose best chunk score exceeds the threshold.

    Aggregates by ``doc_id`` and takes the maximum score per document.
    """
    best_by_doc: dict[str, float] = {}
    for r in results:
        best_by_doc[r.doc_id] = max(
            best_by_doc.get(r.doc_id, 0.0),
            _normalise_score(r.final_score),
        )
    return sum(1 for s in best_by_doc.values() if s >= theta_useful_doc_score)


def _symptom_coverage(
    symptoms: list[str],
    results: list[RetrievedChunkResult],
    top_k: int = 10,
) -> float:
    """
    Fraction of query symptoms that appear (exact substring match) in the
    top-K chunk texts.

    Returns 1.0 when *symptoms* is empty (no symptoms → no gap).
    """
    if not symptoms:
        return 1.0

    evidence = "\n".join(r.chunk_text for r in results[:top_k]).lower()

    covered = sum(
        1 for symptom in symptoms
        if symptom.lower() in evidence
    )
    return covered / len(symptoms)


def _source_diversity(
    results: list[RetrievedChunkResult],
    theta_useful_doc_score: float,
) -> int:
    """
    Count distinct source domains among useful documents
    (score >= ``theta_useful_doc_score``).
    """
    domains: dict[str, str] = {}
    for r in results:
        if _normalise_score(r.final_score) >= theta_useful_doc_score:
            domains[r.doc_id] = r.source_domain
    return len(set(domains.values()))


# Evaluator

class LocalSufficiencyEvaluator:
    """
    Decides whether local retrieval results are sufficient.

    Parameters
    ----------
    theta_rank_confidence:
        Minimum normalised score for the top-ranked result (default 0.55).
    theta_useful_doc_score:
        Minimum score for a document to be considered "useful" (default 0.50).
    min_useful_docs:
        Minimum number of useful documents required (default 3).
    theta_symptom_coverage:
        Minimum fraction of symptoms that must appear in evidence (default 0.60).
    min_source_diversity:
        Minimum number of distinct source domains (default 2).
    theta_insufficiency:
        Composite score threshold above which web search is triggered (default 0.45).
    """

    def __init__(
        self,
        theta_rank_confidence: float = 0.55,
        theta_useful_doc_score: float = 0.50,
        min_useful_docs: int = 3,
        theta_symptom_coverage: float = 0.60,
        min_source_diversity: int = 2,
        theta_insufficiency: float = 0.45,
    ) -> None:
        self.theta_rank_confidence = theta_rank_confidence
        self.theta_useful_doc_score = theta_useful_doc_score
        self.min_useful_docs = min_useful_docs
        self.theta_symptom_coverage = theta_symptom_coverage
        self.min_source_diversity = min_source_diversity
        self.theta_insufficiency = theta_insufficiency

    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, cfg: object) -> "LocalSufficiencyEvaluator":
        """
        Build an evaluator from a :class:`WebSearchSufficiencyConfig` instance.
        """
        return cls(
            theta_rank_confidence=cfg.theta_rank_confidence,  # type: ignore[attr-defined]
            theta_useful_doc_score=cfg.theta_useful_doc_score,  # type: ignore[attr-defined]
            min_useful_docs=cfg.min_useful_docs,  # type: ignore[attr-defined]
            theta_symptom_coverage=cfg.theta_symptom_coverage,  # type: ignore[attr-defined]
            min_source_diversity=cfg.min_source_diversity,  # type: ignore[attr-defined]
            theta_insufficiency=cfg.theta_insufficiency,  # type: ignore[attr-defined]
        )

    # ------------------------------------------------------------------

    def evaluate(self, local_result: LocalRetrievalResult) -> SufficiencyDecision:
        """
        Evaluate whether *local_result* is sufficient.

        Parameters
        ----------
        local_result:
            Result from the local hybrid retriever including the original
            query, extracted symptoms, and ranked chunk results.

        Returns
        -------
        SufficiencyDecision
            ``sufficient=True`` means no web search is needed.
        """
        results = local_result.results

        # Edge case: empty results — definitely insufficient
        if not results:
            logger.info("Sufficiency: no local results — triggering web search")
            return SufficiencyDecision(
                sufficient=False,
                insufficiency_score=1.0,
                rank_confidence=0.0,
                useful_count=0,
                symptom_coverage=0.0,
                source_diversity=0,
                failed_criteria=[
                    "no_local_results",
                    "low_ranking_confidence",
                    "few_useful_docs",
                    "low_symptom_coverage",
                    "low_source_diversity",
                ],
            )

        rank_conf = _rank_confidence(results)
        useful_cnt = _useful_document_count(results, self.theta_useful_doc_score)
        sym_cov = _symptom_coverage(
            local_result.extracted_symptoms, results
        )
        diversity = _source_diversity(results, self.theta_useful_doc_score)

        failed: list[str] = []
        if rank_conf < self.theta_rank_confidence:
            failed.append("low_ranking_confidence")
        if useful_cnt < self.min_useful_docs:
            failed.append("few_useful_docs")
        if sym_cov < self.theta_symptom_coverage:
            failed.append("low_symptom_coverage")
        if diversity < self.min_source_diversity:
            failed.append("low_source_diversity")

        # Weighted composite deficit score
        rank_deficit = 1.0 - rank_conf
        useful_deficit = max(0, self.min_useful_docs - useful_cnt) / self.min_useful_docs
        coverage_deficit = 1.0 - sym_cov
        diversity_deficit = (
            max(0, self.min_source_diversity - diversity) / self.min_source_diversity
        )

        score = (
            0.35 * rank_deficit
            + 0.25 * useful_deficit
            + 0.25 * coverage_deficit
            + 0.15 * diversity_deficit
        )

        sufficient = (not failed) and (score < self.theta_insufficiency)

        logger.info(
            "Sufficiency: score=%.3f sufficient=%s failed=%s",
            score, sufficient, failed,
        )

        return SufficiencyDecision(
            sufficient=sufficient,
            insufficiency_score=round(score, 4),
            rank_confidence=round(rank_conf, 4),
            useful_count=useful_cnt,
            symptom_coverage=round(sym_cov, 4),
            source_diversity=diversity,
            failed_criteria=failed,
        )
