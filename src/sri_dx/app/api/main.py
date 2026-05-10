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
    SearchDiseasesRequest,
    SearchDiseasesResponse,
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


@app.post("/search/diseases", response_model=SearchDiseasesResponse)
async def search_diseases(req: SearchDiseasesRequest):
    if _pipeline is None:
        raise HTTPException(503, detail="Retrieval pipeline not available (OpenSearch unreachable).")

    t0 = time.monotonic()
    try:
        diseases = _pipeline.search_diseases(query=req.query, final_results=req.k)
    except Exception as exc:
        logger.exception("search_diseases failed")
        raise HTTPException(500, detail=str(exc)) from exc

    dtos: list[DiseaseDTO] = []
    for d in diseases:
        top_ev = d.evidence[0] if d.evidence else None
        dtos.append(DiseaseDTO(
            id=str(d.rank),
            name=d.disease_name_display,
            description=top_ev.content_preview if top_ev else "",
            symptoms=[],          # filled by NER aggregator; enrich if needed
            source=top_ev.url.split("/")[2] if top_ev and "://" in top_ev.url else "",
            sourceUrl=top_ev.url if top_ev else "",
            evidence_count=d.evidence_count,
            rank=d.rank,
        ))

    return SearchDiseasesResponse(
        diseases=dtos,
        query=req.query,
        elapsed_seconds=time.monotonic() - t0,
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


@app.post("/rag/clinical")
async def clinical_rag(req: ClinicalRAGRequest):
    """
    Streaming clinical RAG via Server-Sent Events.

    SSE events:
      data: <token>\\n\\n           — text delta while generating
      event: response\\ndata: <RAGResponse JSON>\\n\\n  — final complete response
      event: error\\ndata: <message>\\n\\n             — on failure
    """
    if _rag_uc is None:
        if _llm_status == "unreachable":
            raise HTTPException(
                503,
                detail="LLM not available. Verify GROQ_API_KEY is set and valid.",
            )
        raise HTTPException(503, detail="RAG pipeline not initialised.")

    def generate():
        try:
            logger.info("RAG streaming started")
            count = 0
            for item in _rag_uc.run_streaming(req.chart, req.query):
                if isinstance(item, RAGResponse):
                    logger.info("RAG streaming done — %d deltas, error=%s", count, item.error)
                    payload = item.model_dump_json()
                    yield f"event: response\ndata: {payload}\n\n"
                else:
                    count += 1
                    if count <= 3:
                        logger.info("RAG delta #%d: %r", count, str(item)[:60])
                    safe = str(item).replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
        except Exception as exc:
            logger.exception("Streaming RAG failed")
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if behind proxy
        },
    )


from pydantic import BaseModel as _BaseModel

class PositioningRequest(_BaseModel):
    query: str
    k: int = 10
    min_ner_score: float = 0.5
    hybrid_candidates: int = 100
    final_results: int = 10


@app.post("/search/positioned")
async def positioned_search(req: PositioningRequest):
    """Positioned clinical search — returns ranked clinical groups with explanations."""
    if _pipeline is None:
        raise HTTPException(503, detail="Retrieval pipeline not available.")

    try:
        results = _pipeline.search_positioned(
            query=req.query,
            hybrid_candidates=req.hybrid_candidates,
            final_results=req.final_results,
            positioned_results=req.k,
        )
        return results
    except AttributeError:
        raise HTTPException(501, detail="Positioning module not available in this pipeline build.")
    except Exception as exc:
        logger.exception("positioned_search failed")
        raise HTTPException(500, detail=str(exc)) from exc


class WebSearchRequest(_BaseModel):
    query: str
    k: int = 10
    hybrid_candidates: int = 100
    final_results: int = 10
    min_ner_score: float = 0.5


@app.post("/search/web")
async def web_search(req: WebSearchRequest):
    """
    Hybrid search with automatic web enrichment.
    If the local index results are insufficient, queries PubMed/EuropePMC/MedlinePlus,
    indexes the delta, and re-runs the retrieval.
    Returns results plus a 'web_enriched' flag.
    """
    if _pipeline is None:
        raise HTTPException(503, detail="Retrieval pipeline not available.")

    try:
        from sri_dx.usecases.web_search.search_web_and_enrich import SearchWebAndEnrichUseCase
        from sri_dx.core.config import load_config

        cfg = load_config()
        use_case = SearchWebAndEnrichUseCase(pipeline=_pipeline, config=cfg.web_search)
        report = use_case.run(query=req.query)

        diseases = [
            {
                "disease_name": d.disease_name,
                "disease_name_display": d.disease_name_display,
                "aggregated_score": d.aggregated_score,
                "evidence_count": d.evidence_count,
                "rank": d.rank,
                "evidence": [
                    {
                        "chunk_id": e.chunk_id,
                        "rerank_score": e.rerank_score,
                        "ner_score": e.ner_score,
                        "content_preview": e.content_preview,
                        "url": e.url,
                    }
                    for e in d.evidence
                ],
            }
            for d in report.final_results
        ]
        return {
            "diseases": diseases,
            "web_enriched": report.web_search_triggered,
            "docs_added": report.docs_added,
            "elapsed_seconds": report.elapsed_seconds,
        }
    except ImportError:
        raise HTTPException(501, detail="Web search module not available in this build.")
    except Exception as exc:
        logger.exception("web_search failed")
        raise HTTPException(500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "sri_dx.app.api.main:app",
        host=os.environ.get("SRI_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("SRI_API_PORT", "8000")),
        reload=False,
    )
