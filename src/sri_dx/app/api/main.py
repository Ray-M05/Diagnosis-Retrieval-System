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
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from sri_dx.app.api.dto import (
    ClinicalRAGRequest,
    DiseaseDTO,
    HealthResponse,
    ParseChartResponse,
    PipelineRequest,
    PipelineResponse,
    PipelineStages,
    SearchDiseasesRequest,
    SearchDiseasesResponse,
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
_rag_uc: ClinicalRAGUseCase | None = None
_llm_status: str = "unreachable"
_os_status: str = "unreachable"
_chart_parser = ChartFileParser()


def _build_pipeline():
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
    import os

    os_host = os.environ.get("SRI_OS_HOST", "localhost")
    os_port = int(os.environ.get("SRI_OS_PORT", "9200"))

    lexical = OpenSearchSearchBackend(OpenSearchSearchConfig(
        host=os_host,
        port=os_port,
        index_alias="clinical_chunks",
        search_fields=["section_heading^3", "chunk_text^1"],
    ))
    embedding = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
        host=os_host,
        port=os_port,
        index_name="clinical_embeddings_v1",
    ))
    hybrid = SearchHybridUseCase(
        lexical_backend=lexical,
        embedding_store=embedding,
        config=HybridSearchConfig(fusion_method="rrf", lexical_k=100, semantic_k=100, use_reranking=False),
    )
    return TwoStageRetrievalPipeline(
        hybrid_search=hybrid,
        config=TwoStageRetrievalConfig(hybrid_candidates=100, final_results=10),
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
    global _pipeline, _rag_uc, _llm_status, _os_status

    logger.info("SRI-DX API starting — building pipeline...")
    try:
        _pipeline = _build_pipeline()
        _os_status = "ready"
        logger.info("Pipeline ready.")
    except Exception as exc:
        logger.error("Failed to build retrieval pipeline: %s", exc)
        _os_status = "unreachable"

    if _pipeline is not None:
        _rag_uc, _llm_status = _build_rag_usecase(_pipeline)

    yield  # app runs here

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


def _run_web_enrichment(query: str) -> WebEnrichmentSummary:
    """Triggers web search + reindexing if local results are insufficient.

    After this returns, _pipeline.search() will hit the enriched index.
    """
    from sri_dx.usecases.web_search.search_web_and_enrich import SearchWebAndEnrichUseCase
    from sri_dx.core.config import load_config

    cfg = load_config()
    use_case = SearchWebAndEnrichUseCase(pipeline=_pipeline, config=cfg.web_search)
    report = use_case.run(query=query)
    return WebEnrichmentSummary(
        triggered=report.web_search_triggered,
        docs_added=report.indexing.docs_indexed,
        chunks_added=report.indexing.chunks_indexed,
    )


def _run_hybrid_diseases(query: str, k: int) -> list[DiseaseDTO]:
    diseases = _pipeline.search_diseases(query=query, final_results=k)
    dtos: list[DiseaseDTO] = []
    for d in diseases:
        top_ev = d.evidence[0] if d.evidence else None
        dtos.append(DiseaseDTO(
            id=str(d.rank),
            name=d.disease_name_display,
            description=top_ev.content_preview if top_ev else "",
            symptoms=[],
            source=top_ev.url.split("/")[2] if top_ev and "://" in top_ev.url else "",
            sourceUrl=top_ev.url if top_ev else "",
            evidence_count=d.evidence_count,
            rank=d.rank,
        ))
    return dtos


def _run_positioning(query: str, k: int) -> list:
    try:
        return _pipeline.search_positioned(
            query=query,
            hybrid_candidates=100,
            final_results=k,
            positioned_results=k,
        )
    except AttributeError:
        logger.warning("Positioning module not available — skipping.")
        return []


def _execute_pipeline_stages(
    query: str, stages: PipelineStages, k: int
) -> PipelineResponse:
    """Runs all non-generation stages and returns a PipelineResponse."""
    if _pipeline is None:
        raise HTTPException(503, detail="Retrieval pipeline not available.")

    t0 = time.monotonic()
    web_summary: WebEnrichmentSummary | None = None

    if stages.web_enrichment:
        try:
            web_summary = _run_web_enrichment(query)
        except ImportError:
            raise HTTPException(501, detail="Web search module not available.")
        except Exception as exc:
            logger.exception("web enrichment failed")
            raise HTTPException(500, detail=f"web enrichment: {exc}") from exc

    try:
        hybrid_dtos = _run_hybrid_diseases(query, k)
    except Exception as exc:
        logger.exception("hybrid retrieval failed")
        raise HTTPException(500, detail=str(exc)) from exc

    positioned = _run_positioning(query, k) if stages.positioning else None

    return PipelineResponse(
        query=query,
        hybrid=hybrid_dtos,
        positioned=positioned,
        web_enriched=web_summary,
        elapsed_seconds=time.monotonic() - t0,
    )


@app.post("/pipeline")
async def pipeline(req: PipelineRequest):
    """Composable retrieval pipeline. See module docstring for stage flow."""
    # Non-streaming path
    if not req.stages.generation:
        return _execute_pipeline_stages(req.query, req.stages, req.k)

    # Streaming (RAG) path
    if req.chart is None:
        raise HTTPException(400, detail="`chart` is required when stages.generation is true.")
    if _rag_uc is None:
        if _llm_status == "unreachable":
            raise HTTPException(503, detail="LLM not available. Verify GROQ_API_KEY.")
        raise HTTPException(503, detail="RAG pipeline not initialised.")

    # Execute retrieval stages first (synchronous), then stream the LLM.
    stages_response = _execute_pipeline_stages(req.query, req.stages, req.k)

    def generate():
        try:
            # Emit non-generation stages first so the UI can render them
            yield f"event: stages\ndata: {stages_response.model_dump_json()}\n\n"

            for item in _rag_uc.run_streaming(req.chart, req.query):
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
