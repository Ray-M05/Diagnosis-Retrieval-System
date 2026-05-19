"""Evaluation API router — multipart qrels upload + batch run + run history.

Endpoints:
  POST   /evaluation/run         — multipart qrels JSONL + form mode/k → report
  GET    /evaluation/seed-qrels  — raw contents of the committed seed JSONL
  GET    /evaluation/runs        — list past runs (summary)
  GET    /evaluation/runs/{id}   — full report for a single run
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from sri_dx.modules.evaluation.evaluation_store import EvaluationStore
from sri_dx.modules.evaluation.evaluator import BatchEvaluator
from sri_dx.modules.evaluation.qrels import Qrels


SEED_QRELS_PATH = Path("data/qrels/test_cases.jsonl")


def build_evaluation_router(
    execute_stages: Callable[[str, object, int], object],
    PipelineStagesCls: type,
    get_evaluation_store: Callable[[], EvaluationStore | None],
    get_corpus_size: Callable[[], int],
) -> APIRouter:
    router = APIRouter(prefix="/evaluation", tags=["evaluation"])

    @router.post("/run")
    async def run_evaluation(
        qrels: UploadFile = File(...),
        mode: Literal["hybrid", "diagnostic", "positioned", "web"] = Form(...),
        k: int = Form(10),
    ):
        store = get_evaluation_store()
        if store is None:
            raise HTTPException(503, detail="Evaluation store not available.")

        if k < 1 or k > 50:
            raise HTTPException(400, detail="k must be between 1 and 50.")

        raw_bytes = await qrels.read()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, detail=f"Qrels file must be UTF-8: {exc}") from exc

        try:
            parsed_qrels = Qrels.load_jsonl(content)
        except ValueError as exc:
            raise HTTPException(400, detail=f"Invalid qrels: {exc}") from exc

        corpus_size = get_corpus_size()

        def _do_run():
            evaluator = BatchEvaluator(
                execute_stages=execute_stages,
                PipelineStagesCls=PipelineStagesCls,
                qrels=parsed_qrels,
                mode=mode,
                k=k,
                corpus_size=corpus_size,
            )
            report = evaluator.run()
            store.save_run(report)
            return report

        report = await run_in_threadpool(_do_run)
        return report.to_dict()

    @router.get("/seed-qrels", response_class=PlainTextResponse)
    async def get_seed_qrels():
        if not SEED_QRELS_PATH.exists():
            raise HTTPException(
                404,
                detail=(
                    f"Seed qrels not found at {SEED_QRELS_PATH}. "
                    "Run `python scripts/build_seed_qrels.py` to generate it."
                ),
            )
        return SEED_QRELS_PATH.read_text(encoding="utf-8")

    @router.get("/runs")
    async def list_runs():
        store = get_evaluation_store()
        if store is None:
            raise HTTPException(503, detail="Evaluation store not available.")
        return {"runs": store.list_runs()}

    @router.get("/runs/{run_id}")
    async def get_run(run_id: int):
        store = get_evaluation_store()
        if store is None:
            raise HTTPException(503, detail="Evaluation store not available.")
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(404, detail=f"Run {run_id} not found.")
        return run

    return router
