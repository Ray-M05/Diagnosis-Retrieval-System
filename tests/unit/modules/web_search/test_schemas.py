"""Unit tests — web_search schemas."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.modules.web_search.schemas import (
    ApiRetrievalStats,
    DeduplicationStats,
    ExternalApiDocument,
    IndexingStats,
    LocalRetrievalResult,
    RetrievedChunkResult,
    SufficiencyDecision,
    WebSearchRunReport,
)


class TestExternalApiDocument:
    def test_defaults(self):
        doc = ExternalApiDocument(
            source="medlineplus",
            external_id="abc",
            canonical_url="https://example.com",
            title="Chest Pain",
            abstract_or_summary="Summary text",
            sections=[Section(heading="Summary", text="Summary text")],
        )
        assert doc.language == "en"
        assert doc.authors == []
        assert doc.mesh_terms == []
        assert doc.doi is None
        assert doc.pmid is None
        assert doc.pmcid is None
        assert doc.raw is None

    def test_full_construction(self):
        dt = datetime(2020, 6, 15, tzinfo=timezone.utc)
        doc = ExternalApiDocument(
            source="pubmed",
            external_id="12345678",
            canonical_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            title="Chest pain in primary care",
            abstract_or_summary="Objective: ...",
            sections=[Section(heading="Abstract", text="Objective: ...")],
            published_at=dt,
            authors=["Smith J", "Doe A"],
            journal="BMJ Open",
            doi="10.1136/bmjopen-2020",
            pmid="12345678",
            pmcid="PMC7654321",
            mesh_terms=["Chest Pain", "Dyspnea"],
        )
        assert doc.source == "pubmed"
        assert doc.published_at == dt
        assert len(doc.authors) == 2
        assert "Chest Pain" in doc.mesh_terms


class TestRetrievedChunkResult:
    def test_minimal(self):
        chunk = RetrievedChunkResult(
            chunk_id="doc1:0:0",
            doc_id="doc1",
            title="Test",
            url="https://example.com",
            source_domain="example.com",
            chunk_text="Some text about chest pain",
            final_score=0.75,
        )
        assert chunk.bm25_score is None
        assert chunk.vector_score is None
        assert chunk.rerank_score is None
        assert chunk.section_heading is None


class TestLocalRetrievalResult:
    def test_construction(self):
        chunk = RetrievedChunkResult(
            chunk_id="c1", doc_id="d1", title="T", url="u",
            source_domain="dom", chunk_text="txt", final_score=0.5,
        )
        result = LocalRetrievalResult(
            query="chest pain",
            extracted_symptoms=["chest pain"],
            results=[chunk],
        )
        assert result.query == "chest pain"
        assert len(result.results) == 1


class TestSufficiencyDecision:
    def test_sufficient(self):
        dec = SufficiencyDecision(
            sufficient=True,
            insufficiency_score=0.1,
            rank_confidence=0.9,
            useful_count=5,
            symptom_coverage=0.8,
            source_diversity=3,
            failed_criteria=[],
        )
        assert dec.sufficient is True
        assert dec.failed_criteria == []

    def test_insufficient(self):
        dec = SufficiencyDecision(
            sufficient=False,
            insufficiency_score=0.72,
            rank_confidence=0.3,
            useful_count=1,
            symptom_coverage=0.33,
            source_diversity=1,
            failed_criteria=["low_ranking_confidence", "few_useful_docs", "low_symptom_coverage"],
        )
        assert dec.sufficient is False
        assert len(dec.failed_criteria) == 3


class TestApiRetrievalStats:
    def test_total(self):
        stats = ApiRetrievalStats(medlineplus=8, europe_pmc=7, pubmed=5)
        assert stats.total == 20

    def test_defaults_zero(self):
        stats = ApiRetrievalStats()
        assert stats.total == 0


class TestWebSearchRunReport:
    def _decision(self, sufficient: bool) -> SufficiencyDecision:
        return SufficiencyDecision(
            sufficient=sufficient,
            insufficiency_score=0.0 if sufficient else 0.7,
            rank_confidence=0.9 if sufficient else 0.3,
            useful_count=5 if sufficient else 1,
            symptom_coverage=1.0 if sufficient else 0.2,
            source_diversity=3 if sufficient else 1,
            failed_criteria=[] if sufficient else ["few_useful_docs"],
        )

    def test_no_web_search(self):
        report = WebSearchRunReport(
            query="test",
            query_hash="abcd1234",
            web_search_triggered=False,
            sufficiency=self._decision(True),
        )
        assert report.web_search_triggered is False
        assert report.results == []
        assert report.error is None

    def test_with_web_search(self):
        report = WebSearchRunReport(
            query="chest pain",
            query_hash="ef123456",
            web_search_triggered=True,
            sufficiency=self._decision(False),
            api_retrieval=ApiRetrievalStats(medlineplus=8, europe_pmc=7, pubmed=5),
            deduplication=DeduplicationStats(retrieved_total=20, duplicates_removed=4, new_documents=16),
            indexing=IndexingStats(delta_path="data/api_deltas/foo.jsonl", docs_indexed=16, chunks_indexed=48),
            results=[{"rank": 1, "title": "Chest Pain", "score": 0.92}],
        )
        assert report.api_retrieval.total == 20
        assert report.deduplication.new_documents == 16
        assert report.indexing.docs_indexed == 16
        assert len(report.results) == 1
