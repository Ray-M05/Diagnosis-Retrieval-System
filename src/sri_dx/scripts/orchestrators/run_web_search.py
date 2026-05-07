"""
Executable script that wires up all components and runs
``SearchWebAndEnrichUseCase`` for a test query.

Usage::

    uv run python -m sri_dx.scripts.orchestrators.run_web_search

Or with a custom query via environment variable::

    WEBSEARCH_QUERY="fever and cough" uv run python -m sri_dx.scripts.orchestrators.run_web_search

The query defaults to ``"chest pain and shortness of breath"`` for development.

The script:
- Loads configuration from ``config.toml``.
- Sets up structured logging (INFO → stdout, DEBUG → file).
- Instantiates all adapters, sinks, and the two-stage retrieval pipeline.
- Runs the full web-search-and-enrich pipeline.
- Prints the run report summary to stdout.
- Saves the full JSON report to ``data/web_search/reports/``.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Logging setup (before any module imports that log at module level)

def _setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"web_search_{ts}.log"

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    # Reduce noise from httpx / httpcore internals
    for noisy in ("httpx", "httpcore", "urllib3", "opensearchpy"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.info("Logging initialised — debug log: %s", log_file)


# Component wiring

def _build_use_case():  # noqa: ANN201
    """Build and return a fully wired ``SearchWebAndEnrichUseCase``."""

    from sri_dx.adapters.medical_apis.europe_pmc_client import EuropePmcClient
    from sri_dx.adapters.medical_apis.medical_api_search_service import (
        MedicalApiSearchService,
    )
    from sri_dx.adapters.medical_apis.medlineplus_client import MedlinePlusClient
    from sri_dx.adapters.medical_apis.pubmed_client import PubMedClient
    from sri_dx.adapters.embeddings.clinical_bert_adapter import ClinicalBERTAdapter
    from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
    from sri_dx.adapters.stores.opensearch_search_backend import OpenSearchSearchBackend
    from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
    from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
    from sri_dx.core.config import load_config
    from sri_dx.modules.indexing.chunking import ChunkingConfig
    from sri_dx.modules.web_search.delta_writer import JsonlDeltaWriter
    from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
    from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
    from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig
    from sri_dx.usecases.search.tow_stage_retrieval_pipeline import (
        TwoStageRetrievalConfig,
        TwoStageRetrievalPipeline,
    )
    from sri_dx.usecases.web_search.search_web_and_enrich import (
        SearchWebAndEnrichUseCase,
    )

    cfg = load_config()
    ws_cfg = cfg.web_search
    suf_cfg = ws_cfg.sufficiency
    os_cfg = cfg.opensearch

    logging.info("Loaded config: OpenSearch %s:%d", os_cfg.host, os_cfg.port)

    # ---- OpenSearch sinks ----
    doc_sink = OpenSearchIndexSink(cfg=os_cfg)
    chunk_sink = OpenSearchChunksSink(cfg=os_cfg)

    # ---- Manifest ----
    manifest = SqliteManifestStore(cfg.indexing.manifest_path)

    # ---- Retrieval pipeline ----
    lexical_backend = OpenSearchSearchBackend(cfg=os_cfg)
    bert_adapter = ClinicalBERTAdapter.get_instance()
    from sri_dx.adapters.stores.opensearch_embedding_sink import (
        OpenSearchEmbeddingSink,
        OpenSearchEmbeddingConfig,
    )
    # Ensure we use the correct embedding index config, not the doc index config
    emb_cfg = OpenSearchEmbeddingConfig(
        host=os_cfg.host,
        port=os_cfg.port,
        use_ssl=os_cfg.use_ssl,
        verify_certs=os_cfg.verify_certs,
        request_timeout=os_cfg.request_timeout,
    )
    embedding_store = OpenSearchEmbeddingSink(cfg=emb_cfg)

    hybrid_cfg = HybridSearchConfig(
        fusion_method="rrf",
        lexical_k=100,
        semantic_k=100,
        use_reranking=False,  # reranking handled by TwoStageRetrievalPipeline
    )
    hybrid_search = SearchHybridUseCase(
        lexical_backend=lexical_backend,
        embedding_store=embedding_store,
        config=hybrid_cfg,
        bert_adapter=bert_adapter,
    )
    pipeline_cfg = TwoStageRetrievalConfig(
        hybrid_candidates=100,
        final_results=10,
    )
    pipeline = TwoStageRetrievalPipeline(
        hybrid_search=hybrid_search,
        config=pipeline_cfg,
    )

    # ---- Web search services ----
    api_service = MedicalApiSearchService(
        medlineplus=MedlinePlusClient(
            retmax=ws_cfg.retmax_medlineplus, timeout=ws_cfg.http_timeout
        ),
        europe_pmc=EuropePmcClient(
            retmax=ws_cfg.retmax_europe_pmc, timeout=ws_cfg.http_timeout
        ),
        pubmed=PubMedClient(
            retmax=ws_cfg.retmax_pubmed, timeout=ws_cfg.http_timeout
        ),
    )

    evaluator = LocalSufficiencyEvaluator.from_config(suf_cfg)

    delta_writer = JsonlDeltaWriter(ws_cfg.delta_dir)

    chunk_cfg = ChunkingConfig(max_chars=1200, overlap_chars=200, min_chars=100)

    return SearchWebAndEnrichUseCase(
        pipeline=pipeline,
        sufficiency_evaluator=evaluator,
        api_service=api_service,
        delta_writer=delta_writer,
        doc_sink=doc_sink,
        chunk_sink=chunk_sink,
        manifest=manifest,
        report_dir=ws_cfg.report_dir,
        chunk_cfg=chunk_cfg,
    )


# Entry point

def main() -> None:
    query = os.environ.get(
        "WEBSEARCH_QUERY", "chest pain and shortness of breath"
    )

    _setup_logging(Path("data/web_search/logs"))

    logging.info("=" * 70)
    logging.info("Web Search Orchestrator")
    logging.info("Query: %s", query)
    logging.info("=" * 70)

    try:
        use_case = _build_use_case()
    except Exception as exc:
        logging.critical("Failed to wire components: %s", exc, exc_info=True)
        sys.exit(1)

    try:
        report = use_case.run(query)
    except Exception as exc:
        logging.critical("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)

    # ---- Print summary ----
    print("\n" + "=" * 70)
    print("WEB SEARCH RUN REPORT")
    print("=" * 70)
    print(f"Query           : {report.query}")
    print(f"Query hash      : {report.query_hash}")
    print(f"Web search      : {'YES' if report.web_search_triggered else 'NO'}")
    print(
        f"Sufficiency     : score={report.sufficiency.insufficiency_score:.3f}  "
        f"sufficient={report.sufficiency.sufficient}"
    )
    if report.web_search_triggered:
        print(f"APIs retrieved  : {report.api_retrieval.total} total"
              f"  (MedlinePlus={report.api_retrieval.medlineplus}"
              f", EuropePMC={report.api_retrieval.europe_pmc}"
              f", PubMed={report.api_retrieval.pubmed})")
        print(
            f"Dedup           : retrieved={report.deduplication.retrieved_total}"
            f"  removed={report.deduplication.duplicates_removed}"
            f"  new={report.deduplication.new_documents}"
        )
        print(
            f"Indexed         : docs={report.indexing.docs_indexed}"
            f"  chunks={report.indexing.chunks_indexed}"
        )
    print(f"\nFinal results   : {len(report.results)}")
    for res in report.results:
        print(
            f"  #{res['rank']:2d}  [{res['rerank_score']:.4f}]  {res['title'][:70]}"
            f"  ({res['source_domain']})"
        )
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
