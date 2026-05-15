"""
Integration test — Web Search end-to-end flow.

Requires:
- OpenSearch running and accessible (docker compose up -d)
- clinical_docs and clinical_chunks indices to exist (or be created by the test)

Run only with the ``integration`` marker::

    uv run pytest tests/integration/web_search/ -v -m integration

This test does NOT call real external APIs.  It mocks the API service and
verifies the full pipeline: delta write → IndexCombinedUseCase → hybrid search.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.modules.web_search.schemas import ApiRetrievalStats, ExternalApiDocument


@pytest.mark.integration
class TestWebSearchEndToEnd:
    """
    Smoke test for the full web-search pipeline (without real APIs).

    Flow:
    1. Build real sinks, manifest, pipeline.
    2. Mock api_service to return 2 synthetic documents.
    3. Mock the local pipeline to return insufficient results.
    4. Run SearchWebAndEnrichUseCase.
    5. Verify delta file exists, report is saved, results list is non-empty.
    """

    def test_full_pipeline_smoke(self, tmp_path: Path):
        """Full pipeline smoke test with mocked APIs and real OpenSearch."""
        # Import inside test to avoid loading heavy models at collection time
        from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
        from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
        from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
        from sri_dx.core.config import load_config
        from sri_dx.modules.indexing.chunking import ChunkingConfig
        from sri_dx.modules.web_search.delta_writer import JsonlDeltaWriter
        from sri_dx.modules.web_search.schemas import SufficiencyDecision
        from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
        from sri_dx.usecases.search.two_stage_retrieval_pipeline import RetrievalResult
        from sri_dx.usecases.web_search.search_web_and_enrich import SearchWebAndEnrichUseCase

        cfg = load_config()

        # ---- sinks & manifest ----
        doc_sink = OpenSearchIndexSink(cfg=cfg.opensearch)
        chunk_sink = OpenSearchChunksSink(cfg=cfg.opensearch)
        manifest = SqliteManifestStore(tmp_path / "manifest.sqlite")

        # ---- mock pipeline: insufficient first run, returns results second ----
        pipeline = MagicMock()
        pipeline.search.side_effect = [
            [],  # initial search → no results
            [   # re-search after enrichment → some results
                RetrievalResult(
                    doc_id="synthetic_d1",
                    rerank_score=0.85,
                    original_hybrid_score=0.75,
                    lexical_score=0.5,
                    vector_score=0.3,
                    original_position=0,
                    final_position=0,
                    metadata={
                        "title": "Chest Pain Review",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/99999/",
                        "source_domain": "pubmed.ncbi.nlm.nih.gov",
                        "content": "Chest pain and shortness of breath are common presentations.",
                        "chunk_id": "synthetic_d1:0:0",
                    },
                    content="Chest pain and shortness of breath are common presentations.",
                )
            ],
        ]

        # ---- mock api service: return 2 synthetic docs ----
        api_service = MagicMock()
        ext_docs = [
            ExternalApiDocument(
                source="pubmed",
                external_id="99999",
                canonical_url="https://pubmed.ncbi.nlm.nih.gov/99999/",
                title="Chest Pain Review",
                abstract_or_summary="Chest pain and shortness of breath are common presentations.",
                sections=[
                    Section(
                        heading="Abstract",
                        text="Chest pain and shortness of breath are common presentations of cardiac disease.",
                    )
                ],
                pmid="99999",
                language="en",
            ),
            ExternalApiDocument(
                source="medlineplus",
                external_id="ml_chest_pain",
                canonical_url="https://medlineplus.gov/chestpain.html",
                title="Chest Pain",
                abstract_or_summary="Chest pain has many possible causes.",
                sections=[
                    Section(heading="Summary", text="Chest pain has many possible causes.")
                ],
                language="en",
            ),
        ]
        api_service.search_sync.return_value = (
            ext_docs,
            ApiRetrievalStats(medlineplus=1, europe_pmc=0, pubmed=1),
        )

        # ---- evaluator: insufficient ----
        evaluator = LocalSufficiencyEvaluator(
            theta_rank_confidence=0.99,  # force insufficient
        )

        uc = SearchWebAndEnrichUseCase(
            pipeline=pipeline,
            sufficiency_evaluator=evaluator,
            api_service=api_service,
            delta_writer=JsonlDeltaWriter(tmp_path / "deltas"),
            doc_sink=doc_sink,
            chunk_sink=chunk_sink,
            manifest=manifest,
            report_dir=tmp_path / "reports",
            chunk_cfg=ChunkingConfig(max_chars=800, overlap_chars=100, min_chars=50),
        )

        report = uc.run("chest pain and shortness of breath")

        # ---- assertions ----
        assert report.web_search_triggered is True

        delta_files = list((tmp_path / "deltas").glob("api_query_*.jsonl"))
        assert len(delta_files) == 1, "Delta file should have been written"

        lines = delta_files[0].read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2, "Both synthetic docs should be in the delta"

        # Verify each line is a valid AcquiredDocument-compatible dict
        for line in lines:
            obj = json.loads(line)
            assert "doc_id" in obj
            assert "content" in obj
            assert "content_hash" in obj

        report_files = list((tmp_path / "reports").glob("web_search_run_*.json"))
        assert len(report_files) == 1

        assert report.api_retrieval.total == 2
        assert report.deduplication.new_documents == 2
