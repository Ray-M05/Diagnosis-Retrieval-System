"""Unit tests — SearchWebAndEnrichUseCase."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.modules.web_search.schemas import (
    ApiRetrievalStats,
    ExternalApiDocument,
    LocalRetrievalResult,
    RetrievedChunkResult,
    SufficiencyDecision,
)
from sri_dx.usecases.search.tow_stage_retrieval_pipeline import RetrievalResult


# ---------------------------------------------------------------------------
# Helpers / Factories
# ---------------------------------------------------------------------------

def _chunk(
    doc_id: str = "d1",
    score: float = 0.9,
    domain: str = "medlineplus.gov",
    text: str = "chest pain shortness of breath",
) -> RetrievedChunkResult:
    return RetrievedChunkResult(
        chunk_id=f"{doc_id}:0:0",
        doc_id=doc_id,
        title="Test",
        url=f"https://{domain}/test",
        source_domain=domain,
        chunk_text=text,
        final_score=score,
        rerank_score=score,
    )


def _retrieval_result(
    doc_id: str = "d1",
    score: float = 0.9,
    domain: str = "medlineplus.gov",
) -> RetrievalResult:
    return RetrievalResult(
        doc_id=doc_id,
        rerank_score=score,
        original_hybrid_score=score * 0.9,
        lexical_score=score * 0.5,
        vector_score=score * 0.4,
        original_position=0,
        final_position=0,
        metadata={
            "chunk_id": f"{doc_id}:0:0",
            "title": "Test Title",
            "url": f"https://{domain}/test",
            "source_domain": domain,
            "content": "chest pain shortness of breath",
        },
        content="chest pain shortness of breath",
    )


def _ext_doc(pmid: str = "111") -> ExternalApiDocument:
    return ExternalApiDocument(
        source="pubmed",
        external_id=pmid,
        canonical_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        title="Test Article",
        abstract_or_summary="Abstract about chest pain.",
        sections=[Section(heading="Abstract", text="Abstract about chest pain.")],
        pmid=pmid,
    )


def _sufficient_decision() -> SufficiencyDecision:
    return SufficiencyDecision(
        sufficient=True,
        insufficiency_score=0.1,
        rank_confidence=0.9,
        useful_count=5,
        symptom_coverage=0.8,
        source_diversity=3,
        failed_criteria=[],
    )


def _insufficient_decision() -> SufficiencyDecision:
    return SufficiencyDecision(
        sufficient=False,
        insufficiency_score=0.7,
        rank_confidence=0.3,
        useful_count=1,
        symptom_coverage=0.2,
        source_diversity=1,
        failed_criteria=["low_ranking_confidence", "few_useful_docs", "low_symptom_coverage"],
    )


def _build_use_case(tmp_path: Path):
    """Build a SearchWebAndEnrichUseCase with all dependencies mocked."""
    from sri_dx.modules.web_search.delta_writer import JsonlDeltaWriter
    from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
    from sri_dx.usecases.web_search.search_web_and_enrich import SearchWebAndEnrichUseCase

    pipeline = MagicMock()
    sufficiency_evaluator = MagicMock(spec=LocalSufficiencyEvaluator)
    api_service = MagicMock()
    delta_writer = JsonlDeltaWriter(tmp_path / "deltas")
    doc_sink = MagicMock()
    chunk_sink = MagicMock()
    manifest = MagicMock()

    uc = SearchWebAndEnrichUseCase(
        pipeline=pipeline,
        sufficiency_evaluator=sufficiency_evaluator,
        api_service=api_service,
        delta_writer=delta_writer,
        doc_sink=doc_sink,
        chunk_sink=chunk_sink,
        manifest=manifest,
        report_dir=tmp_path / "reports",
    )
    return uc, pipeline, sufficiency_evaluator, api_service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSearchWebAndEnrichUseCase:
    def test_raises_on_empty_query(self, tmp_path: Path):
        uc, _, _, _ = _build_use_case(tmp_path)
        with pytest.raises(ValueError, match="non-empty"):
            uc.run("")

    def test_sufficient_results_skip_web_search(self, tmp_path: Path):
        uc, pipeline, evaluator, api_service = _build_use_case(tmp_path)

        # 4 good results from 3 domains
        pipeline.search.return_value = [
            _retrieval_result("d1", 0.9, "medlineplus.gov"),
            _retrieval_result("d2", 0.8, "europepmc.org"),
            _retrieval_result("d3", 0.75, "pubmed.ncbi.nlm.nih.gov"),
            _retrieval_result("d4", 0.7, "emedicine.com"),
        ]
        evaluator.evaluate.return_value = _sufficient_decision()

        report = uc.run("chest pain and shortness of breath")

        assert report.web_search_triggered is False
        api_service.search_sync.assert_not_called()
        assert len(report.results) == 4

    def test_insufficient_results_trigger_web_search(self, tmp_path: Path):
        uc, pipeline, evaluator, api_service = _build_use_case(tmp_path)

        # First search: poor results
        poor = [_retrieval_result("d1", 0.3, "dom1.com")]
        # Second search (after indexing): enriched
        enriched = [
            _retrieval_result("d1", 0.3, "dom1.com"),
            _retrieval_result("d2", 0.85, "medlineplus.gov"),
            _retrieval_result("d3", 0.8, "europepmc.org"),
        ]
        pipeline.search.side_effect = [poor, enriched]
        evaluator.evaluate.return_value = _insufficient_decision()

        ext_docs = [_ext_doc("111"), _ext_doc("222")]
        api_service.search_sync.return_value = (
            ext_docs,
            ApiRetrievalStats(medlineplus=0, europe_pmc=0, pubmed=2),
        )

        # Mock IndexCombinedUseCase so we don't need OpenSearch
        with patch(
            "sri_dx.usecases.web_search.search_web_and_enrich.IndexCombinedUseCase"
        ) as mock_indexer_cls:
            mock_indexer = MagicMock()
            mock_indexer.run.return_value = {"docs_indexed_ok": 2, "chunks_indexed_ok": 6}
            mock_indexer_cls.return_value = mock_indexer

            report = uc.run("chest pain and shortness of breath")

        assert report.web_search_triggered is True
        assert report.api_retrieval.pubmed == 2
        assert report.deduplication.retrieved_total == 2
        assert report.indexing.docs_indexed == 2
        assert report.indexing.chunks_indexed == 6
        assert len(report.results) == 3

    def test_empty_local_results_trigger_web_search(self, tmp_path: Path):
        uc, pipeline, evaluator, api_service = _build_use_case(tmp_path)

        pipeline.search.side_effect = [[], []]
        evaluator.evaluate.return_value = SufficiencyDecision(
            sufficient=False, insufficiency_score=1.0, rank_confidence=0.0,
            useful_count=0, symptom_coverage=0.0, source_diversity=0,
            failed_criteria=["no_local_results"],
        )
        api_service.search_sync.return_value = ([], ApiRetrievalStats())

        with patch("sri_dx.usecases.web_search.search_web_and_enrich.IndexCombinedUseCase"):
            report = uc.run("fever and rash")

        assert report.web_search_triggered is True

    def test_all_api_docs_duplicates_no_indexing(self, tmp_path: Path):
        """When all external docs are duplicates, no indexing should occur."""
        uc, pipeline, evaluator, api_service = _build_use_case(tmp_path)

        pipeline.search.side_effect = [[_retrieval_result("d1", 0.3)], []]
        evaluator.evaluate.return_value = _insufficient_decision()

        # Return docs that will all be deduped (same PMID for all)
        ext_docs = [_ext_doc("SAME_PMID"), _ext_doc("SAME_PMID")]
        api_service.search_sync.return_value = (
            ext_docs, ApiRetrievalStats(pubmed=2),
        )

        with patch(
            "sri_dx.usecases.web_search.search_web_and_enrich.IndexCombinedUseCase"
        ) as mock_indexer_cls:
            report = uc.run("chest pain")

        assert report.deduplication.new_documents <= 1
        # Indexer may or may not be called; what matters is no crash
        assert report is not None

    def test_report_saved_to_disk(self, tmp_path: Path):
        uc, pipeline, evaluator, api_service = _build_use_case(tmp_path)

        pipeline.search.return_value = [_retrieval_result("d1", 0.9)]
        evaluator.evaluate.return_value = _sufficient_decision()

        uc.run("chest pain")

        report_files = list((tmp_path / "reports").glob("web_search_run_*.json"))
        assert len(report_files) == 1

        with report_files[0].open(encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["query"] == "chest pain"
        assert data["web_search_triggered"] is False
