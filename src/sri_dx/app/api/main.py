"""FastAPI application — SRI-DX clinical retrieval + RAG API.

Endpoints:
  GET  /health                  — liveness + component status
  POST /search/diseases         — symptom search (connects existing pipeline)
  POST /rag/parse-chart         — upload PDF/TXT → PatientChart JSON
  POST /rag/clinical            — streaming clinical RAG (SSE)

Startup (lifespan):
  - Builds TwoStageRetrievalPipeline (OpenSearch + ClinicalBERT + cross-encoder)
  - Builds ClinicalRAGUseCase (includes GroqAdapter health check)
  - Logs warnings without crashing if Groq is unreachable at startup

SSE format for /rag/clinical:
  data: <text delta>\n\n          (while streaming)
  event: response\ndata: <RAGResponse JSON>\n\n   (final, once)
  event: error\ndata: <message>\n\n              (on failure)
"""

from __future__ import annotations

import json
import logging
import re
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("opensearch").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
from contextlib import asynccontextmanager
from html import unescape
from typing import AsyncIterator
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from sri_dx.app.api.feedback import build_feedback_router
from sri_dx.app.api.evaluation import build_evaluation_router
from sri_dx.app.api.dto import (
    ClinicalRAGRequest,
    DiseaseDTO,
    HealthResponse,
    HybridChunkDTO,
    ParseChartResponse,
    PipelineRequest,
    PipelineResponse,
    PipelineStages,
    SearchDiseasesRequest,
    SearchDiseasesResponse,
    SufficiencyInfo,
    WebEnrichmentSummary,
)
from sri_dx.modules.rag.chart_file_parser import ChartFileParser
from sri_dx.usecases.rag.clinical_rag import ClinicalRAGConfig, ClinicalRAGUseCase
from sri_dx.core.schemas.rag.rag_response import RAGResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App state (singletons initialised at startup)
# ---------------------------------------------------------------------------

_pipeline = None        # TwoStageRetrievalPipeline
_feedback_store = None  # SqliteFeedbackStore
_evaluation_store = None  # EvaluationStore
_corpus_size: int = 1   # Cached at startup; used as denominator for Fallout.
_rag_uc: ClinicalRAGUseCase | None = None
_llm_status: str = "unreachable"
_os_status: str = "unreachable"
_chart_parser = ChartFileParser()


def _opensearch_settings() -> tuple[str, int, bool]:
    """Read OpenSearch host from either SRI_* or docker-compose OPENSEARCH_HOST."""
    raw_host = os.environ.get("SRI_OS_HOST") or os.environ.get("OPENSEARCH_HOST") or "localhost"
    default_port = int(os.environ.get("SRI_OS_PORT", "9200"))

    if "://" in raw_host:
        parsed = urlparse(raw_host)
        host = _normalize_opensearch_host(parsed.hostname or "localhost")
        port = parsed.port or (443 if parsed.scheme == "https" else default_port)
        use_ssl = parsed.scheme == "https"
        return host, port, use_ssl

    if ":" in raw_host:
        host, port_text = raw_host.rsplit(":", 1)
        if port_text.isdigit():
            return _normalize_opensearch_host(host), int(port_text), False

    return _normalize_opensearch_host(raw_host), default_port, False


def _normalize_opensearch_host(host: str) -> str:
    """Use Docker DNS only inside containers; local Windows must use localhost."""
    if host == "opensearch" and not os.path.exists("/.dockerenv"):
        return "localhost"
    return host


def _build_feedback_store():
    import os
    from pathlib import Path

    from sri_dx.adapters.stores.sqlite_feedback_store import SqliteFeedbackStore

    db_path = Path(os.environ.get("SRI_FEEDBACK_DB", "data/feedback/feedback.sqlite"))
    return SqliteFeedbackStore(db_path)


def _build_evaluation_store():
    import os
    from pathlib import Path

    from sri_dx.modules.evaluation.evaluation_store import EvaluationStore

    db_path = Path(os.environ.get("SRI_EVALUATION_DB", "data/evaluation/evaluation.sqlite"))
    return EvaluationStore(db_path)


def _regenerate_seed_qrels() -> None:
    """Rebuild data/qrels/test_cases.jsonl from tests/TEST_CASES.md.

    Runs the same logic as `python scripts/build_seed_qrels.py` so the seed
    qrels served by GET /evaluation/seed-qrels is always in sync with the
    Markdown source — contributors don't have to remember to run the script
    after editing TEST_CASES.md.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3].parent
    script_path = repo_root / "scripts" / "build_seed_qrels.py"
    if not script_path.exists():
        logger.warning("Seed qrels script not found at %s — skipping regeneration.", script_path)
        return

    import runpy
    try:
        runpy.run_path(str(script_path), run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            logger.warning("Seed qrels regeneration exited with code %s.", exc.code)
    except Exception as exc:
        logger.warning("Seed qrels regeneration failed: %s", exc)


def _compute_corpus_size() -> int:
    """Total indexed chunks — used as denominator for Fallout (closed-world)."""
    try:
        reader = _build_chunk_reader()
        return max(int(reader.get_total_chunks()), 1)
    except Exception as exc:
        logger.warning("Could not compute corpus size: %s. Defaulting to 1.", exc)
        return 1


def _build_pipeline(feedback_store=None):
    from sri_dx.adapters.stores.opensearch_search_backend import (
        OpenSearchSearchBackend,
        OpenSearchSearchConfig,
    )
    from sri_dx.adapters.stores import OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig
    from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
    from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig
    from sri_dx.usecases.search.two_stage_retrieval_pipeline import (
        TwoStageRetrievalPipeline,
        TwoStageRetrievalConfig,
    )
    os_host, os_port, use_ssl = _opensearch_settings()
    chunks_index = (
        os.environ.get("SRI_CHUNKS_INDEX")
        or os.environ.get("OPENSEARCH_CHUNKS_INDEX")
        or "clinical_chunks"
    )
    embeddings_index = (
        os.environ.get("SRI_EMBEDDINGS_INDEX")
        or os.environ.get("OPENSEARCH_EMBEDDINGS_INDEX")
        or "clinical_embeddings_v1"
    )

    lexical = OpenSearchSearchBackend(OpenSearchSearchConfig(
        host=os_host,
        port=os_port,
        use_ssl=use_ssl,
        index_alias=chunks_index,
        search_fields=["section_heading^3", "chunk_text^1"],
    ))
    embedding = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
        host=os_host,
        port=os_port,
        use_ssl=use_ssl,
        index_name=embeddings_index,
    ))
    hybrid = SearchHybridUseCase(
        lexical_backend=lexical,
        embedding_store=embedding,
        config=HybridSearchConfig(fusion_method="rrf", lexical_k=100, semantic_k=100, use_reranking=False),
    )
    enable_prf = os.environ.get("SRI_ENABLE_PRF", "false").lower() in {"1", "true", "yes", "on"}
    return TwoStageRetrievalPipeline(
        hybrid_search=hybrid,
        config=TwoStageRetrievalConfig(
            hybrid_candidates=100,
            final_results=10,
            enable_prf=enable_prf,
        ),
        feedback_store=feedback_store,
    )


def _build_chunk_reader():
    from sri_dx.adapters.stores.opensearch_chunk_reader import OpenSearchChunkReader
    from sri_dx.adapters.stores.schemas.opensearch_chunk_reader_config import (
        OpenSearchChunkReaderConfig,
    )

    os_host, os_port, use_ssl = _opensearch_settings()
    chunks_index = (
        os.environ.get("SRI_CHUNKS_INDEX")
        or os.environ.get("OPENSEARCH_CHUNKS_INDEX")
        or "clinical_chunks"
    )
    return OpenSearchChunkReader(
        OpenSearchChunkReaderConfig(
            host=os_host,
            port=os_port,
            use_ssl=use_ssl,
            index_name=chunks_index,
        )
    )


def _build_rag_usecase(pipeline) -> tuple[ClinicalRAGUseCase | None, str]:
    """Returns (use_case, status). status is 'ready' or 'unreachable'."""
    import os
    from sri_dx.adapters.llm.groq_adapter import GroqAdapter, GroqAdapterConfig

    model = os.environ.get("SRI_RAG_MODEL", "llama-3.1-8b-instant")
    api_key = os.environ.get("GROQ_API_KEY", "")

    try:
        llm = GroqAdapter(GroqAdapterConfig(model=model, api_key=api_key))
        uc = ClinicalRAGUseCase(pipeline=pipeline, llm=llm, config=ClinicalRAGConfig())
        return uc, "ready"
    except RuntimeError as exc:
        logger.warning("Groq not available at startup: %s", exc)
        return None, "unreachable"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _pipeline, _feedback_store, _evaluation_store, _corpus_size
    global _rag_uc, _llm_status, _os_status

    logger.info("SRI-DX API starting — building pipeline...")
    try:
        _feedback_store = _build_feedback_store()
        _pipeline = _build_pipeline(_feedback_store)
        _os_status = "ready"
        logger.info("Pipeline ready.")
    except Exception as exc:
        logger.error("Failed to build retrieval pipeline: %s", exc)
        _os_status = "unreachable"

    if _pipeline is not None:
        _rag_uc, _llm_status = _build_rag_usecase(_pipeline)

    _regenerate_seed_qrels()

    try:
        _evaluation_store = _build_evaluation_store()
        logger.info("Evaluation store ready.")
    except Exception as exc:
        logger.warning("Evaluation store unavailable: %s", exc)

    if _os_status == "ready":
        _corpus_size = _compute_corpus_size()
        logger.info("Corpus size cached: %d chunks.", _corpus_size)

    yield  # app runs here

    if _feedback_store is not None:
        _feedback_store.close()
    if _evaluation_store is not None:
        _evaluation_store.close()
    logger.info("SRI-DX API shutting down.")


# ---------------------------------------------------------------------------
# App + CORS
# ---------------------------------------------------------------------------

import os

CORS_ORIGINS = os.environ.get(
    "SRI_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app = FastAPI(
    title="SRI-DX Clinical Retrieval API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    status = "ok" if (_os_status == "ready" and _llm_status == "ready") else "degraded"
    return HealthResponse(
        status=status,
        llm=_llm_status,
        opensearch=_os_status,
    )


@app.get("/")
async def root():
    return {
        "name": "SRI-DX Clinical Retrieval API",
        "health": "/health",
        "docs": "/docs",
        "pipeline": "/pipeline",
    }


@app.post("/rag/parse-chart", response_model=ParseChartResponse)
async def parse_chart(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "text/plain", None):
        # Be lenient — browsers may send generic content types
        pass

    data = await file.read()
    filename = file.filename or "upload.txt"

    result = _chart_parser.parse_bytes(data, filename)

    warning = None
    if result.extraction_failed:
        warning = (
            "Could not extract text from this file. "
            "If it is a scanned PDF, please paste the chart text manually."
        )

    return ParseChartResponse(
        chart=result.chart,
        extraction_failed=result.extraction_failed,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# /pipeline — composable retrieval + (web) + (positioning) + (RAG generation)
# ---------------------------------------------------------------------------
#
# Single composable endpoint. Stages execute in fixed order, each optional:
#   1. Hybrid retrieval                    (always)
#   2. Web enrichment + re-retrieval       (if stages.web_enrichment)
#   3. Positioning aggregation             (if stages.positioning)
#   4. RAG generation (SSE streaming)      (if stages.generation, requires chart)
#
# When stages.generation is False:
#   - Returns JSON PipelineResponse.
# When stages.generation is True:
#   - Returns Server-Sent Events:
#       event: stages\ndata: <PipelineResponse JSON>\n\n   (initial, once)
#       data: <text delta>\n\n                               (LLM stream)
#       event: response\ndata: <RAGResponse JSON>\n\n        (final, once)
#       event: error\ndata: <message>\n\n                    (on failure)
# ---------------------------------------------------------------------------


def _run_web_enrichment(query: str) -> tuple[WebEnrichmentSummary, list[DiseaseDTO]]:
    """Triggers web search + reindexing if local results are insufficient.

    After this returns, _pipeline.search() will hit the enriched index.
    """
    from sri_dx.adapters.medical_apis.europe_pmc_client import EuropePmcClient
    from sri_dx.adapters.medical_apis.medical_api_search_service import (
        MedicalApiSearchService,
    )
    from sri_dx.adapters.medical_apis.medlineplus_client import MedlinePlusClient
    from sri_dx.adapters.medical_apis.pubmed_client import PubMedClient
    from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
    from sri_dx.adapters.stores.opensearch_sink import (
        OpenSearchConfig as OpenSearchIndexConfig,
        OpenSearchIndexSink,
    )
    from sri_dx.adapters.stores.schemas.opensearch_chunks_config import (
        OpenSearchChunksConfig,
    )
    from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
    from sri_dx.modules.indexing.chunking import ChunkingConfig
    from sri_dx.modules.web_search.delta_writer import JsonlDeltaWriter
    from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
    from sri_dx.usecases.web_search.search_web_and_enrich import SearchWebAndEnrichUseCase
    from sri_dx.core.config import load_config

    cfg = load_config()
    if not cfg.web_search.enabled:
        raise HTTPException(503, detail="Web search module is disabled by configuration.")

    ws_cfg = cfg.web_search
    os_host, os_port, use_ssl = _opensearch_settings()
    docs_index = (
        os.environ.get("SRI_OS_INDEX")
        or os.environ.get("OPENSEARCH_DOCS_INDEX")
        or cfg.opensearch.index_name
    )
    docs_alias = (
        os.environ.get("SRI_OS_ALIAS")
        or os.environ.get("OPENSEARCH_DOCS_ALIAS")
        or cfg.opensearch.alias_name
    )
    chunks_index = (
        os.environ.get("SRI_CHUNKS_INDEX")
        or os.environ.get("OPENSEARCH_CHUNKS_INDEX")
        or "clinical_chunks_v1"
    )
    chunks_alias = (
        os.environ.get("SRI_CHUNKS_ALIAS")
        or os.environ.get("OPENSEARCH_CHUNKS_ALIAS")
        or "clinical_chunks"
    )

    api_service = MedicalApiSearchService(
        medlineplus=MedlinePlusClient(
            retmax=ws_cfg.retmax_medlineplus,
            timeout=ws_cfg.http_timeout,
        ),
        europe_pmc=EuropePmcClient(
            retmax=ws_cfg.retmax_europe_pmc,
            timeout=ws_cfg.http_timeout,
        ),
        pubmed=PubMedClient(
            retmax=ws_cfg.retmax_pubmed,
            timeout=ws_cfg.http_timeout,
        ),
    )
    use_case = SearchWebAndEnrichUseCase(
        pipeline=_pipeline,
        sufficiency_evaluator=LocalSufficiencyEvaluator.from_config(ws_cfg.sufficiency),
        api_service=api_service,
        delta_writer=JsonlDeltaWriter(ws_cfg.delta_dir),
        doc_sink=OpenSearchIndexSink(OpenSearchIndexConfig(
            host=os_host,
            port=os_port,
            use_ssl=use_ssl,
            verify_certs=cfg.opensearch.verify_certs,
            index_name=docs_index,
            alias_name=docs_alias,
        )),
        chunk_sink=OpenSearchChunksSink(OpenSearchChunksConfig(
            host=os_host,
            port=os_port,
            use_ssl=use_ssl,
            verify_certs=cfg.opensearch.verify_certs,
            index_name=chunks_index,
            alias_name=chunks_alias,
        )),
        manifest=SqliteManifestStore(cfg.indexing.manifest_path),
        report_dir=ws_cfg.report_dir,
        chunk_cfg=ChunkingConfig(max_chars=1200, overlap_chars=200, min_chars=100),
    )
    report = use_case.run(query=query)
    return (
        WebEnrichmentSummary(
            triggered=report.web_search_triggered,
            docs_added=report.indexing.docs_indexed,
            chunks_added=report.indexing.chunks_indexed,
            api_retrieved=report.api_retrieval.total,
            api_new_documents=report.deduplication.new_documents,
            duplicates_removed=report.deduplication.duplicates_removed,
        ),
        _web_report_results_to_dtos(report.results),
    )


def _web_report_results_to_dtos(results: list[dict]) -> list[DiseaseDTO]:
    """Map web-search chunk ranking to the frontend's existing result DTO."""
    dtos: list[DiseaseDTO] = []
    for i, result in enumerate(results, start=1):
        rank = int(result.get("rank") or i)
        doc_id = str(result.get("doc_id") or f"web-doc-{rank}")
        chunk_id = str(result.get("chunk_id") or doc_id)
        url = str(result.get("url") or "")
        source_domain = str(result.get("source_domain") or "")
        title = _clean_display_title(
            str(result.get("title") or _display_title_from_url(url, source_domain, f"Resultado web #{rank}"))
        )
        rerank_score = float(result.get("rerank_score") or 0.0)
        dtos.append(DiseaseDTO(
            id=f"{doc_id}:{chunk_id}",
            name=title,
            description=str(result.get("chunk_text") or ""),
            symptoms=[],
            source=source_domain,
            sourceUrl=url,
            evidence_count=1,
            rank=rank,
            feedback_chunk_id=chunk_id,
            feedback_doc_id=doc_id,
            score=rerank_score,
            doc_title=title,
        ))
    return dtos


def _display_title_from_url(url: str, source_domain: str, fallback: str) -> str:
    if source_domain:
        parsed = urlparse(url) if url else None
        path = parsed.path.strip("/") if parsed else ""
        if path:
            slug = path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip()
            if slug:
                return f"{slug} ({source_domain})"
        return source_domain
    return fallback


def _clean_display_title(title: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", unescape(str(title or "")))
    return re.sub(r"\s+", " ", cleaned).strip()


_SLUG_NOISE_PATTERNS = (
    re.compile(r"^syc[\s\-_]?\d+$", re.IGNORECASE),
    re.compile(r"^pmc\d+$", re.IGNORECASE),
    re.compile(r"^\d+$"),
    re.compile(r"^(symptoms?[\s\-_]causes?|causes?|symptoms?|diagnosis|treatment|prevention)$", re.IGNORECASE),
    re.compile(r"^(health[\s\-_]topics?|article|ency|medlineplus)$", re.IGNORECASE),
)


def _is_noise_slug(slug: str) -> bool:
    s = slug.replace("-", " ").replace("_", " ").strip()
    return any(p.match(s) for p in _SLUG_NOISE_PATTERNS)


def _title_from_url(url: str) -> str | None:
    """Best-effort title from a URL path. Picks the most meaningful slug,
    skipping noise like 'syc-20352557', 'PMC1234', 'symptoms-causes', etc."""
    if not url:
        return None
    try:
        path = urlparse(url).path.strip("/")
        if not path:
            return None
        segments = [s for s in path.split("/") if s]
        # Walk from end to start, pick first segment that isn't noise.
        for seg in reversed(segments):
            seg_clean = re.sub(r"\.(html?|aspx?|php)$", "", seg, flags=re.IGNORECASE)
            if _is_noise_slug(seg_clean):
                continue
            slug = seg_clean.replace("-", " ").replace("_", " ").strip()
            if slug:
                return slug.title()
        # Fallback: last segment even if noisy
        slug = segments[-1].replace("-", " ").replace("_", " ").strip()
        return slug.title() if slug else None
    except Exception:
        return None


def _load_doc_metadata_by_id(doc_ids: list[str]) -> dict[str, dict[str, str]]:
    """Fetch (title, url) for documents from the docs index via mget.

    DiseaseEvidence does not carry the document title — only the chunk's URL.
    Without this lookup, doc_title can only be slug-inferred which loses real
    titles like "Acromegaly - Symptoms and Causes - Mayo Clinic". This mirrors
    what `SearchWebAndEnrichUseCase._load_doc_records_by_id` does for web cards.
    """
    ids = list(dict.fromkeys(d for d in doc_ids if d))
    if not ids:
        return {}

    from sri_dx.core.config import load_config
    from opensearchpy import OpenSearch

    try:
        cfg = load_config()
        os_host, os_port, use_ssl = _opensearch_settings()
        docs_index = (
            os.environ.get("SRI_OS_INDEX")
            or os.environ.get("OPENSEARCH_DOCS_INDEX")
            or cfg.opensearch.index_name
        )
        client = OpenSearch(
            hosts=[{"host": os_host, "port": os_port}],
            use_ssl=use_ssl,
            verify_certs=cfg.opensearch.verify_certs,
            http_compress=True,
            timeout=10,
        )
        response = client.mget(index=docs_index, body={"ids": ids})
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not load doc metadata: %s", exc)
        return {}

    out: dict[str, dict[str, str]] = {}
    for doc in response.get("docs", []):
        if not doc.get("found"):
            continue
        source = doc.get("_source") or {}
        out[str(doc.get("_id"))] = {
            "title": _clean_display_title(str(source.get("title") or "")),
            "url": str(source.get("url") or "").strip(),
        }
    return out


def _diseases_to_dtos(diseases: list) -> list[DiseaseDTO]:
    doc_ids = [
        d.evidence[0].doc_id for d in diseases if d.evidence and d.evidence[0].doc_id
    ]
    doc_meta = _load_doc_metadata_by_id(doc_ids)

    dtos: list[DiseaseDTO] = []
    for d in diseases:
        top_ev = d.evidence[0] if d.evidence else None
        disease_id = (
            f"{top_ev.doc_id}:{top_ev.chunk_id}"
            if top_ev
            else f"{d.disease_name_display}:{d.rank}"
        )
        meta = doc_meta.get(top_ev.doc_id, {}) if top_ev else {}
        url = meta.get("url") or (top_ev.url if top_ev else "")
        title = meta.get("title") or (_title_from_url(url) if url else None)
        dtos.append(DiseaseDTO(
            id=disease_id,
            name=d.disease_name_display,
            description=top_ev.content_preview if top_ev else "",
            symptoms=[],
            source=url.split("/")[2] if "://" in url else "",
            sourceUrl=url,
            evidence_count=d.evidence_count,
            rank=d.rank,
            feedback_chunk_id=top_ev.chunk_id if top_ev else None,
            feedback_doc_id=top_ev.doc_id if top_ev else None,
            score=float(d.aggregated_score),
            doc_title=title,
        ))
    return dtos


def _diseases_to_pipeline_response(query: str, diseases: list, elapsed_seconds: float) -> PipelineResponse:
    return PipelineResponse(
        query=query,
        hybrid=_diseases_to_dtos(diseases),
        positioned=None,
        web_enriched=None,
        sufficiency=None,
        elapsed_seconds=elapsed_seconds,
    )


def _run_hybrid_diseases(query: str, k: int) -> list[DiseaseDTO]:
    diseases = _pipeline.search_diseases(query=query, final_results=k)
    return _diseases_to_dtos(diseases)


def _run_hybrid_chunks(query: str, k: int) -> list[HybridChunkDTO]:
    """Run the two-stage retrieval and return raw reranked chunks (no NER aggregation)."""
    raw = _pipeline.search(query=query, final_results=k)
    dtos: list[HybridChunkDTO] = []
    for r in raw:
        meta = r.metadata or {}
        url = str(meta.get("url") or "").strip()
        raw_title = meta.get("title") or meta.get("doc_title") or ""
        title = _clean_display_title(str(raw_title)) if raw_title else (_title_from_url(url) or "")
        dtos.append(HybridChunkDTO(
            doc_id=str(r.doc_id),
            chunk_id=str(meta.get("chunk_id") or r.doc_id),
            score=float(r.rerank_score),
            rerank_score=float(r.rerank_score),
            vector_score=float(r.vector_score) if r.vector_score is not None else None,
            lexical_score=float(r.lexical_score) if r.lexical_score is not None else None,
            fusion_method="cross-encoder",
            title=title or None,
            section_heading=str(meta.get("section_heading") or "") or None,
            url=url or None,
            source_domain=str(meta.get("source_domain") or "") or None,
            chunk_text_preview=(r.content or "")[:400],
        ))
    return dtos


def _run_positioning(query: str, k: int) -> list:
    try:
        return _pipeline.search_positioned(
            query=query,
            hybrid_candidates=100,
            positioned_results=k,
        )
    except AttributeError:
        logger.warning("Positioning module not available — skipping.")
        return []


def _evaluate_sufficiency(query: str, k: int) -> SufficiencyInfo | None:
    """Run LocalSufficiencyEvaluator against the current hybrid index."""
    try:
        from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
        from sri_dx.modules.web_search.schemas import LocalRetrievalResult
        from sri_dx.usecases.web_search.search_web_and_enrich import (
            _retrieval_results_to_chunks,
            _extract_symptoms,
        )
        from sri_dx.core.config import load_config

        raw = _pipeline.search(query, final_results=max(k, 20))
        chunks = _retrieval_results_to_chunks(raw)
        symptoms = _extract_symptoms(query)
        evaluator = LocalSufficiencyEvaluator.from_config(
            load_config().web_search.sufficiency
        )
        decision = evaluator.evaluate(LocalRetrievalResult(
            query=query,
            extracted_symptoms=symptoms,
            results=chunks,
        ))
        return SufficiencyInfo(
            sufficient=decision.sufficient,
            insufficiency_score=decision.insufficiency_score,
            rank_confidence=decision.rank_confidence,
            useful_count=decision.useful_count,
            symptom_coverage=decision.symptom_coverage,
            source_diversity=decision.source_diversity,
            failed_criteria=decision.failed_criteria,
        )
    except Exception as exc:
        logger.warning("Sufficiency evaluation failed: %s", exc)
        return None


def _positioned_to_retrieval_results(positioned: list) -> list:
    """Flatten PositionedClinicalResult[] into RetrievalResult[] preserving the
    order chosen by the positioning module.

    Order: outer = positioned[].rank ascending (1, 2, 3...), inner = order of
    evidences as the positioning module emitted them. Duplicates across groups
    are dropped (first occurrence wins) so the RAG context isn't pollued.
    """
    from sri_dx.usecases.search.two_stage_retrieval_pipeline import RetrievalResult

    flat: list = []
    seen_chunks: set[str] = set()
    fp = 0
    for cond in positioned or []:
        for ev in getattr(cond, "evidences", []) or []:
            if ev.chunk_id in seen_chunks:
                continue
            seen_chunks.add(ev.chunk_id)
            metadata = {
                "chunk_id": ev.chunk_id,
                "url": ev.url or "",
                "source_domain": ev.source_domain or "",
                "section_heading": ev.section_heading or "",
                "content": ev.text or ev.content_preview or "",
            }
            flat.append(RetrievalResult(
                doc_id=ev.doc_id,
                rerank_score=float(ev.cross_encoder_score or 0.0),
                original_hybrid_score=float(ev.hybrid_score or 0.0),
                lexical_score=ev.lexical_score,
                vector_score=ev.vector_score,
                original_position=fp,
                final_position=fp,
                metadata=metadata,
                content=ev.text or ev.content_preview or None,
            ))
            fp += 1
    return flat


def _execute_pipeline_stages(
    query: str, stages: PipelineStages, k: int
) -> PipelineResponse:
    """Runs all non-generation stages and returns a PipelineResponse."""
    if _pipeline is None:
        raise HTTPException(503, detail="Retrieval pipeline not available.")

    logger.info(
        "Pipeline request: web_enrichment=%s positioning=%s generation=%s raw_hybrid=%s",
        stages.web_enrichment, stages.positioning, stages.generation, stages.raw_hybrid,
    )
    t0 = time.monotonic()
    web_summary: WebEnrichmentSummary | None = None
    web_ranked_dtos: list[DiseaseDTO] | None = None

    if stages.web_enrichment:
        try:
            web_summary, web_ranked_dtos = _run_web_enrichment(query)
        except ImportError as exc:
            logger.exception("web enrichment import failed")
            raise HTTPException(
                501,
                detail=f"Web search module not available: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception("web enrichment failed")
            raise HTTPException(500, detail=f"web enrichment: {exc}") from exc

    if web_ranked_dtos is not None:
        hybrid_dtos = web_ranked_dtos[:k]
    else:
        try:
            hybrid_dtos = _run_hybrid_diseases(query, k)
        except Exception as exc:
            logger.exception("hybrid retrieval failed")
            raise HTTPException(500, detail=str(exc)) from exc

    positioned = _run_positioning(query, k) if stages.positioning else None

    hybrid_chunks: list[HybridChunkDTO] | None = None
    if stages.raw_hybrid:
        try:
            hybrid_chunks = _run_hybrid_chunks(query, k)
        except Exception as exc:
            logger.exception("raw hybrid retrieval failed")
            raise HTTPException(500, detail=f"raw_hybrid: {exc}") from exc

    # Only evaluate sufficiency when web enrichment was NOT active (if already
    # enriched, the results are implicitly sufficient from the caller's POV).
    sufficiency = None if stages.web_enrichment else _evaluate_sufficiency(query, k)

    return PipelineResponse(
        query=query,
        hybrid=hybrid_dtos,
        hybrid_chunks=hybrid_chunks,
        positioned=positioned,
        web_enriched=web_summary,
        sufficiency=sufficiency,
        elapsed_seconds=time.monotonic() - t0,
    )


app.include_router(build_feedback_router(
    get_pipeline=lambda: _pipeline,
    get_feedback_store=lambda: _feedback_store,
    get_chunk_reader=_build_chunk_reader,
    diseases_to_response=_diseases_to_pipeline_response,
))

def _rag_answer_for_eval(query: str) -> str:
    """Blocking RAG call used by the evaluation `rag` mode.

    Runs the same `ClinicalRAGUseCase` as the live endpoint but with an
    empty `PatientChart`, captures the final answer and returns it as plain
    text so the evaluator can search for the expected diagnosis in it.
    Returns an empty string when the LLM is unavailable.
    """
    if _rag_uc is None:
        return ""
    from sri_dx.core.schemas.rag.patient_chart import PatientChart as _PatientChart
    response = _rag_uc.run(_PatientChart(), query)
    return getattr(response, "answer_markdown", "") or ""


app.include_router(build_evaluation_router(
    execute_stages=_execute_pipeline_stages,
    PipelineStagesCls=PipelineStages,
    get_evaluation_store=lambda: _evaluation_store,
    get_corpus_size=lambda: _corpus_size,
    rag_answer_fn=_rag_answer_for_eval,
    is_rag_available=lambda: _rag_uc is not None,
))


@app.post("/pipeline")
async def pipeline(req: PipelineRequest):
    """Composable retrieval pipeline. See module docstring for stage flow."""
    # Non-streaming path
    if not req.stages.generation:
        return await run_in_threadpool(
            _execute_pipeline_stages,
            req.query,
            req.stages,
            req.k,
        )

    # Streaming (RAG) path
    if _rag_uc is None:
        if _llm_status == "unreachable":
            raise HTTPException(503, detail="LLM not available. Verify GROQ_API_KEY.")
        raise HTTPException(503, detail="RAG pipeline not initialised.")

    # Force positioning ON for generation: the RAG must receive the ranking
    # produced by the positioning module, not the raw cross-encoder rerank.
    stages_for_run = req.stages.model_copy(update={"positioning": True})

    # Execute retrieval stages first (synchronous), then stream the LLM.
    stages_response = await run_in_threadpool(
        _execute_pipeline_stages,
        req.query,
        stages_for_run,
        req.k,
    )

    from sri_dx.core.schemas.rag.patient_chart import PatientChart as _PatientChart
    chart = req.chart if req.chart is not None else _PatientChart()

    # Feed the RAG with the positioned ranking. Fall back to internal retrieval
    # only if positioning produced nothing (which would be an upstream failure).
    preretrieved = _positioned_to_retrieval_results(stages_response.positioned or [])
    if not preretrieved:
        logger.warning(
            "Positioning returned no evidences for query '%s' — RAG will fall back to pipeline.search().",
            req.query[:80],
        )

    def generate():
        try:
            # Emit non-generation stages first so the UI can render them
            yield f"event: stages\ndata: {stages_response.model_dump_json()}\n\n"

            stream = _rag_uc.run_streaming(
                chart,
                req.query,
                preretrieved_chunks=preretrieved or None,
            )
            for item in stream:
                if isinstance(item, RAGResponse):
                    payload = item.model_dump_json()
                    yield f"event: response\ndata: {payload}\n\n"
                else:
                    safe = str(item).replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
        except Exception as exc:
            logger.exception("pipeline (streaming) failed")
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Legacy endpoints — thin wrappers over /pipeline. Kept for backwards compat.
# Will be removed once the frontend fully migrates to /pipeline.
# ---------------------------------------------------------------------------

@app.post("/search/diseases", response_model=SearchDiseasesResponse)
async def search_diseases(req: SearchDiseasesRequest):
    """Deprecated. Use POST /pipeline with stages={}."""
    pr = _execute_pipeline_stages(req.query, PipelineStages(), req.k)
    return SearchDiseasesResponse(
        diseases=pr.hybrid,
        query=req.query,
        elapsed_seconds=pr.elapsed_seconds,
    )


@app.post("/rag/clinical")
async def clinical_rag(req: ClinicalRAGRequest):
    """Deprecated. Use POST /pipeline with stages.generation=true."""
    pipeline_req = PipelineRequest(
        query=req.query,
        chart=req.chart,
        stages=PipelineStages(generation=True),
    )
    return await pipeline(pipeline_req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "sri_dx.app.api.main:app",
        host=os.environ.get("SRI_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("SRI_API_PORT", "8000")),
        reload=False,
    )
