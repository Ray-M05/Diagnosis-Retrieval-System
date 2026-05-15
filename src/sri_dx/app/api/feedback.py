"""Feedback API router."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from sri_dx.adapters.stores.opensearch_chunk_reader import OpenSearchChunkReader
from sri_dx.adapters.stores.sqlite_feedback_store import SqliteFeedbackStore
from sri_dx.app.api.dto import PipelineResponse
from sri_dx.core.schemas.feedback.feedback_schemas import (
    FeedbackRequest,
    FeedbackResponse,
    RefineSearchRequest,
    RefineSearchResponse,
)
from sri_dx.modules.feedback import FeedbackService, FeedbackTextualExpander


def build_feedback_router(
    get_pipeline: Callable[[], object | None],
    get_feedback_store: Callable[[], SqliteFeedbackStore | None],
    get_chunk_reader: Callable[[], OpenSearchChunkReader],
    diseases_to_response: Callable[[str, list, float], PipelineResponse],
) -> APIRouter:
    router = APIRouter(prefix="/feedback", tags=["feedback"])

    @router.post("/relevance", response_model=FeedbackResponse)
    async def submit_relevance_feedback(req: FeedbackRequest) -> FeedbackResponse:
        store = get_feedback_store()
        if store is None:
            raise HTTPException(503, detail="Feedback store not available.")

        try:
            FeedbackService(store).record_feedback(
                session_id=req.session_id,
                query=req.query,
                chunk_id=req.chunk_id,
                doc_id=req.doc_id,
                relevant=req.relevant,
            )
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc

        return FeedbackResponse(ok=True, message="Feedback registrado correctamente")

    @router.post("/search/refine", response_model=RefineSearchResponse)
    async def refine_search(req: RefineSearchRequest) -> RefineSearchResponse:
        import time

        pipeline = get_pipeline()
        store = get_feedback_store()
        if pipeline is None:
            raise HTTPException(503, detail="Retrieval pipeline not available.")
        if store is None:
            raise HTTPException(503, detail="Feedback store not available.")

        feedback_items = [
            item for item in store.get_feedback_for_session(req.session_id)
            if item["query"] == req.query
        ]
        relevant_ids = [
            item["chunk_id"] for item in feedback_items
            if item["relevant"]
        ]
        non_relevant_ids = {
            item["chunk_id"] for item in feedback_items
            if not item["relevant"]
        }

        relevant_chunks: list[str] = []
        if relevant_ids:
            chunks_by_id = get_chunk_reader().get_chunks_by_ids(relevant_ids)
            relevant_chunks = [
                chunk.chunk_text for chunk in chunks_by_id.values()
                if chunk.chunk_text
            ]

        refined_query = FeedbackTextualExpander().expand_with_relevant_chunks(
            original_query=req.query,
            relevant_chunks=relevant_chunks,
        )
        if refined_query != req.query:
            store.save_query_expansion(
                session_id=req.session_id,
                original_query=req.query,
                expanded_query=refined_query,
                strategy="feedback_textual",
            )

        t0 = time.monotonic()
        diseases = pipeline.search_diseases(
            query=refined_query,
            final_results=req.k,
            excluded_chunk_ids=non_relevant_ids,
            session_id=req.session_id,
        )
        results = diseases_to_response(
            refined_query,
            diseases,
            time.monotonic() - t0,
        )

        return RefineSearchResponse(
            original_query=req.query,
            refined_query=refined_query,
            strategy="feedback_textual",
            results=results.model_dump(),
        )

    return router
