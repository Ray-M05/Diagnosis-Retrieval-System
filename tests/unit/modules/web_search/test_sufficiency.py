"""Unit tests — LocalSufficiencyEvaluator."""
from __future__ import annotations

import pytest

from sri_dx.modules.web_search.schemas import (
    LocalRetrievalResult,
    RetrievedChunkResult,
)
from sri_dx.modules.web_search.sufficiency import (
    LocalSufficiencyEvaluator,
    _rank_confidence,
    _sigmoid,
    _source_diversity,
    _symptom_coverage,
    _useful_document_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(
    chunk_id: str = "c1",
    doc_id: str = "d1",
    score: float = 0.8,
    source_domain: str = "medlineplus.gov",
    text: str = "chest pain shortness of breath",
) -> RetrievedChunkResult:
    return RetrievedChunkResult(
        chunk_id=chunk_id,
        doc_id=doc_id,
        title="Test doc",
        url=f"https://{source_domain}/test",
        source_domain=source_domain,
        chunk_text=text,
        final_score=score,
    )


def _local(
    query: str = "chest pain and shortness of breath",
    symptoms: list[str] | None = None,
    chunks: list[RetrievedChunkResult] | None = None,
) -> LocalRetrievalResult:
    return LocalRetrievalResult(
        query=query,
        extracted_symptoms=symptoms or ["chest pain", "shortness of breath"],
        results=chunks or [],
    )


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------

class TestSigmoid:
    def test_zero(self):
        assert abs(_sigmoid(0.0) - 0.5) < 1e-6

    def test_large_positive(self):
        assert _sigmoid(100.0) > 0.999

    def test_large_negative(self):
        assert _sigmoid(-100.0) < 0.001


class TestRankConfidence:
    def test_empty(self):
        assert _rank_confidence([]) == 0.0

    def test_score_in_range(self):
        chunks = [_chunk(score=0.7), _chunk(doc_id="d2", score=0.4)]
        assert _rank_confidence(chunks) == pytest.approx(0.7)

    def test_logit_score_normalised(self):
        # score = 2.0 → sigmoid ≈ 0.88
        chunks = [_chunk(score=2.0)]
        conf = _rank_confidence(chunks)
        assert 0.85 < conf < 0.95


class TestUsefulDocumentCount:
    def test_no_chunks(self):
        assert _useful_document_count([], 0.5) == 0

    def test_aggregates_by_doc_id(self):
        # Two chunks from same doc — only one doc counted
        chunks = [
            _chunk(chunk_id="c1", doc_id="d1", score=0.9),
            _chunk(chunk_id="c2", doc_id="d1", score=0.6),
            _chunk(chunk_id="c3", doc_id="d2", score=0.7),
        ]
        assert _useful_document_count(chunks, 0.5) == 2

    def test_threshold_filters(self):
        chunks = [
            _chunk(chunk_id="c1", doc_id="d1", score=0.3),  # below threshold
            _chunk(chunk_id="c2", doc_id="d2", score=0.8),
        ]
        assert _useful_document_count(chunks, 0.5) == 1


class TestSymptomCoverage:
    def test_no_symptoms(self):
        assert _symptom_coverage([], [_chunk()]) == 1.0

    def test_full_coverage(self):
        chunks = [_chunk(text="chest pain shortness of breath fatigue")]
        cov = _symptom_coverage(["chest pain", "shortness of breath", "fatigue"], chunks)
        assert cov == pytest.approx(1.0)

    def test_partial_coverage(self):
        chunks = [_chunk(text="chest pain information")]
        cov = _symptom_coverage(["chest pain", "shortness of breath"], chunks)
        assert cov == pytest.approx(0.5)

    def test_no_coverage(self):
        chunks = [_chunk(text="unrelated content about vitamins")]
        cov = _symptom_coverage(["chest pain", "dyspnea"], chunks)
        assert cov == pytest.approx(0.0)

    def test_case_insensitive(self):
        chunks = [_chunk(text="CHEST PAIN AND DYSPNEA")]
        cov = _symptom_coverage(["chest pain"], chunks)
        assert cov == pytest.approx(1.0)


class TestSourceDiversity:
    def test_no_results(self):
        assert _source_diversity([], 0.5) == 0

    def test_single_domain(self):
        chunks = [
            _chunk(chunk_id="c1", doc_id="d1", score=0.9, source_domain="medlineplus.gov"),
            _chunk(chunk_id="c2", doc_id="d2", score=0.8, source_domain="medlineplus.gov"),
        ]
        assert _source_diversity(chunks, 0.5) == 1

    def test_multiple_domains(self):
        chunks = [
            _chunk(chunk_id="c1", doc_id="d1", score=0.9, source_domain="medlineplus.gov"),
            _chunk(chunk_id="c2", doc_id="d2", score=0.8, source_domain="europepmc.org"),
            _chunk(chunk_id="c3", doc_id="d3", score=0.7, source_domain="pubmed.ncbi.nlm.nih.gov"),
        ]
        assert _source_diversity(chunks, 0.5) == 3

    def test_below_threshold_excluded(self):
        chunks = [
            _chunk(chunk_id="c1", doc_id="d1", score=0.3, source_domain="domain-a.com"),
            _chunk(chunk_id="c2", doc_id="d2", score=0.8, source_domain="domain-b.com"),
        ]
        # Only d2 is above threshold
        assert _source_diversity(chunks, 0.5) == 1


# ---------------------------------------------------------------------------
# Evaluator integration tests
# ---------------------------------------------------------------------------

class TestLocalSufficiencyEvaluator:
    def _evaluator(self) -> LocalSufficiencyEvaluator:
        return LocalSufficiencyEvaluator(
            theta_rank_confidence=0.55,
            theta_useful_doc_score=0.50,
            min_useful_docs=3,
            theta_symptom_coverage=0.60,
            min_source_diversity=2,
            theta_insufficiency=0.45,
        )

    def test_empty_results_always_insufficient(self):
        ev = self._evaluator()
        result = _local(chunks=[])
        decision = ev.evaluate(result)
        assert decision.sufficient is False
        assert decision.insufficiency_score == 1.0
        assert "no_local_results" in decision.failed_criteria

    def test_perfect_results_sufficient(self):
        ev = self._evaluator()
        chunks = [
            _chunk("c1", "d1", 0.9, "medlineplus.gov", "chest pain shortness of breath"),
            _chunk("c2", "d2", 0.8, "europepmc.org", "chest pain shortness of breath"),
            _chunk("c3", "d3", 0.75, "pubmed.ncbi.nlm.nih.gov", "chest pain dyspnea"),
            _chunk("c4", "d4", 0.7, "emedicine.medscape.com", "shortness of breath fatigue"),
        ]
        result = _local(symptoms=["chest pain", "shortness of breath"], chunks=chunks)
        decision = ev.evaluate(result)
        assert decision.sufficient is True
        assert decision.failed_criteria == []

    def test_low_rank_confidence_triggers_web_search(self):
        ev = self._evaluator()
        chunks = [_chunk("c1", "d1", 0.3, text="chest pain shortness of breath")]
        result = _local(chunks=chunks)
        decision = ev.evaluate(result)
        assert "low_ranking_confidence" in decision.failed_criteria
        assert decision.sufficient is False

    def test_few_useful_docs_triggers_web_search(self):
        ev = self._evaluator()
        # Only 1 useful doc (min=3)
        chunks = [_chunk("c1", "d1", 0.9, "dom1.com", "chest pain shortness of breath")]
        result = _local(chunks=chunks)
        decision = ev.evaluate(result)
        assert "few_useful_docs" in decision.failed_criteria
        assert decision.sufficient is False

    def test_low_symptom_coverage_triggers_web_search(self):
        ev = self._evaluator()
        # Enough docs but text doesn't cover symptoms
        chunks = [
            _chunk("c1", "d1", 0.9, "dom1.com", "unrelated content"),
            _chunk("c2", "d2", 0.8, "dom2.com", "unrelated content"),
            _chunk("c3", "d3", 0.75, "dom3.com", "unrelated content"),
        ]
        result = _local(symptoms=["chest pain", "shortness of breath"], chunks=chunks)
        decision = ev.evaluate(result)
        assert "low_symptom_coverage" in decision.failed_criteria
        assert decision.sufficient is False

    def test_low_source_diversity_triggers_web_search(self):
        ev = self._evaluator()
        # All from same domain (min=2)
        chunks = [
            _chunk("c1", "d1", 0.9, "medlineplus.gov", "chest pain shortness of breath"),
            _chunk("c2", "d2", 0.8, "medlineplus.gov", "chest pain fatigue"),
            _chunk("c3", "d3", 0.75, "medlineplus.gov", "shortness of breath"),
        ]
        result = _local(symptoms=["chest pain", "shortness of breath"], chunks=chunks)
        decision = ev.evaluate(result)
        assert "low_source_diversity" in decision.failed_criteria
        assert decision.sufficient is False

    def test_from_config(self):
        """from_config() factory builds a correctly configured evaluator."""
        class _FakeConfig:
            theta_rank_confidence = 0.6
            theta_useful_doc_score = 0.4
            min_useful_docs = 2
            theta_symptom_coverage = 0.5
            min_source_diversity = 1
            theta_insufficiency = 0.5

        ev = LocalSufficiencyEvaluator.from_config(_FakeConfig())
        assert ev.theta_rank_confidence == 0.6
        assert ev.min_useful_docs == 2
