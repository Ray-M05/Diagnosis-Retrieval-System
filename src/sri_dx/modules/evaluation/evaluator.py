"""BatchEvaluator — runs a qrels file against the retrieval pipeline.

Replicates the four research-mode dispatches from
`frontend/src/views/ResearchView/research.api.ts`:

  - hybrid     → raw_hybrid chunks (chunk-level natively)
  - diagnostic → NER-aggregated diseases
  - positioned → clinical-positioning + NER-aggregated diseases
  - web        → web enrichment + NER-aggregated diseases

For each query we compute disease-level metrics always, and chunk-level
metrics only when the qrels entry carries `relevant_chunk_ids` or
`relevant_doc_ids`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sri_dx.modules.evaluation import metrics as M
from sri_dx.modules.evaluation.normalization import normalize_disease_name
from sri_dx.modules.evaluation.qrels import QrelEntry, Qrels


SearchMode = str  # "hybrid" | "diagnostic" | "positioned" | "web"


@dataclass
class PerQueryResult:
    query: str
    retrieved_disease_names: list[str]
    relevant_disease_names: list[str]
    disease_metrics: dict[str, float]
    retrieved_chunk_ids: list[str] | None = None
    relevant_chunk_ids: list[str] | None = None
    chunk_metrics: dict[str, float] | None = None


@dataclass
class EvaluationReport:
    mode: SearchMode
    k: int
    level: str  # "disease" | "chunk" | "both"
    qrels_hash: str
    corpus_size: int
    timestamp: str
    macro_disease: dict[str, float]
    macro_chunk: dict[str, float] | None
    per_query: list[PerQueryResult]
    run_id: int | None = None
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "k": self.k,
            "level": self.level,
            "qrels_hash": self.qrels_hash,
            "corpus_size": self.corpus_size,
            "timestamp": self.timestamp,
            "macro": self.macro_disease,
            "macro_chunk": self.macro_chunk,
            "per_query": [
                {
                    "query": r.query,
                    "retrieved_disease_names": r.retrieved_disease_names,
                    "relevant_disease_names": r.relevant_disease_names,
                    "disease_metrics": r.disease_metrics,
                    "retrieved_chunk_ids": r.retrieved_chunk_ids,
                    "relevant_chunk_ids": r.relevant_chunk_ids,
                    "chunk_metrics": r.chunk_metrics,
                }
                for r in self.per_query
            ],
            "errors": self.errors,
        }


def _get(item: Any, *keys: str) -> Any:
    """Read attribute or dict key, returning None if missing."""
    for key in keys:
        val = getattr(item, key, None) if not isinstance(item, dict) else item.get(key)
        if val:
            return val
    return None


def _extract_disease_aliases_from_dtos(dtos: list[Any]) -> list[list[str]]:
    """For each DTO, return a list of normalized aliases to match against qrels.

    Aliases include the NER-aggregated disease name AND the title of the top
    evidence document (when present). Either alias is sufficient for a hit.
    Empty aliases are filtered out.
    """
    out: list[list[str]] = []
    for d in dtos:
        name = _get(d, "name", "disease_name_display", "disease_name")
        title = _get(d, "doc_title", "title")
        aliases: list[str] = []
        if name:
            aliases.append(normalize_disease_name(str(name)))
        if title:
            aliases.append(normalize_disease_name(str(title)))
        if aliases:
            out.append(aliases)
    return out


def _extract_disease_aliases_from_positioned(positioned: list[Any]) -> list[list[str]]:
    """Positioned results carry disease_name (and optionally a title)."""
    out: list[list[str]] = []
    for r in positioned or []:
        name = _get(r, "disease_name_display", "disease_name", "name")
        title = _get(r, "doc_title", "title")
        aliases: list[str] = []
        if name:
            aliases.append(normalize_disease_name(str(name)))
        if title:
            aliases.append(normalize_disease_name(str(title)))
        if aliases:
            out.append(aliases)
    return out


def _primary_names(aliases_list: list[list[str]]) -> list[str]:
    """For persistence/UI: keep only the first alias per rank (the NER name)."""
    return [aliases[0] for aliases in aliases_list if aliases]


def _extract_chunk_ids(chunks: list[Any]) -> list[str]:
    out: list[str] = []
    for c in chunks or []:
        cid = getattr(c, "chunk_id", None) or (c.get("chunk_id") if isinstance(c, dict) else None)
        if cid:
            out.append(str(cid))
    return out


def _extract_doc_ids(items: list[Any]) -> list[str]:
    out: list[str] = []
    for c in items or []:
        did = getattr(c, "doc_id", None) or (c.get("doc_id") if isinstance(c, dict) else None)
        if did:
            out.append(str(did))
    return out


def _disease_metrics(
    retrieved: list[list[str]],
    relevant: list[str],
    k: int,
    corpus_size: int,
) -> dict[str, float]:
    return {
        "precision_at_k": M.precision_at_k(retrieved, relevant, k),
        "recall_at_k": M.recall_at_k(retrieved, relevant, k),
        "f1_at_k": M.f1_at_k(retrieved, relevant, k),
        "map": M.average_precision(retrieved, relevant),
        "mrr": M.reciprocal_rank(retrieved, relevant),
        "ndcg_at_k": M.ndcg_at_k(retrieved, relevant, k),
        "fallout_at_k": M.fallout_at_k(retrieved, relevant, k, corpus_size),
        "r_precision": M.r_precision(retrieved, relevant),
        "top_1_hit": M.hit_at_k(retrieved, relevant, 1),
        "top_3_hit": M.hit_at_k(retrieved, relevant, 3),
    }


class BatchEvaluator:
    """Run a qrels set against a configured retrieval mode and compute metrics.

    `execute_stages` is the function `_execute_pipeline_stages(query, stages, k)`
    from the API layer — passed in so this module stays decoupled from FastAPI.
    `PipelineStagesCls` is the `PipelineStages` pydantic model.
    """

    def __init__(
        self,
        execute_stages: Callable[[str, Any, int], Any],
        PipelineStagesCls: type,
        qrels: Qrels,
        mode: SearchMode,
        k: int,
        corpus_size: int,
    ) -> None:
        if mode not in ("hybrid", "diagnostic", "positioned", "web"):
            raise ValueError(f"Unknown mode: {mode!r}")
        self._execute_stages = execute_stages
        self._PipelineStages = PipelineStagesCls
        self.qrels = qrels
        self.mode = mode
        self.k = k
        self.corpus_size = max(corpus_size, 1)

    def _stages_for_mode(self):
        cls = self._PipelineStages
        if self.mode == "hybrid":
            return cls(web_enrichment=False, positioning=False, generation=False, raw_hybrid=True)
        if self.mode == "diagnostic":
            return cls(web_enrichment=False, positioning=False, generation=False, raw_hybrid=False)
        if self.mode == "positioned":
            return cls(web_enrichment=False, positioning=True, generation=False, raw_hybrid=False)
        # web
        return cls(web_enrichment=True, positioning=False, generation=False, raw_hybrid=False)

    def _run_one(self, entry: QrelEntry) -> PerQueryResult:
        stages = self._stages_for_mode()
        response = self._execute_stages(entry.query, stages, self.k)

        # Disease-level retrieved aliases depend on the mode. Each rank carries
        # both the NER-aggregated disease name AND the title of the top
        # evidence document — either alias is enough for a hit.
        if self.mode == "hybrid":
            disease_aliases = _extract_disease_aliases_from_dtos(response.hybrid or [])
        elif self.mode == "positioned":
            disease_aliases = _extract_disease_aliases_from_positioned(response.positioned or [])
            if not disease_aliases:
                disease_aliases = _extract_disease_aliases_from_dtos(response.hybrid or [])
        else:  # diagnostic, web
            disease_aliases = _extract_disease_aliases_from_dtos(response.hybrid or [])

        disease_retrieved = _primary_names(disease_aliases)
        disease_metrics = _disease_metrics(
            disease_aliases, entry.relevant_disease_names, self.k, self.corpus_size
        )

        # Chunk-level metrics — only when the qrels entry provides chunk or doc IDs.
        chunk_retrieved: list[str] | None = None
        chunk_metrics: dict[str, float] | None = None
        chunk_relevant: list[str] | None = None

        if entry.has_chunk_level:
            if self.mode == "hybrid" and response.hybrid_chunks:
                # Prefer chunk_id matching if provided
                if entry.relevant_chunk_ids:
                    chunk_retrieved = _extract_chunk_ids(response.hybrid_chunks)
                    chunk_relevant = list(entry.relevant_chunk_ids)
                else:
                    chunk_retrieved = _extract_doc_ids(response.hybrid_chunks)
                    chunk_relevant = list(entry.relevant_doc_ids or [])
            else:
                # For non-hybrid modes, fall back to DiseaseDTO.feedback_*
                source = response.hybrid or []
                if entry.relevant_chunk_ids:
                    chunk_retrieved = [
                        str(getattr(d, "feedback_chunk_id", "") or "")
                        for d in source
                        if getattr(d, "feedback_chunk_id", None)
                    ]
                    chunk_relevant = list(entry.relevant_chunk_ids)
                else:
                    chunk_retrieved = [
                        str(getattr(d, "feedback_doc_id", "") or "")
                        for d in source
                        if getattr(d, "feedback_doc_id", None)
                    ]
                    chunk_relevant = list(entry.relevant_doc_ids or [])

            if chunk_retrieved is not None and chunk_relevant is not None:
                chunk_metrics = _disease_metrics(
                    [[c] for c in chunk_retrieved],
                    chunk_relevant,
                    self.k,
                    self.corpus_size,
                )

        return PerQueryResult(
            query=entry.query,
            retrieved_disease_names=disease_retrieved,
            relevant_disease_names=list(entry.relevant_disease_names),
            disease_metrics=disease_metrics,
            retrieved_chunk_ids=chunk_retrieved,
            relevant_chunk_ids=chunk_relevant,
            chunk_metrics=chunk_metrics,
        )

    def run(self) -> EvaluationReport:
        per_query: list[PerQueryResult] = []
        errors: list[dict[str, str]] = []

        for entry in self.qrels.entries:
            try:
                per_query.append(self._run_one(entry))
            except Exception as exc:  # noqa: BLE001 — surface but don't abort batch
                errors.append({"query": entry.query, "error": str(exc)})

        macro_disease = M.macro_average(r.disease_metrics for r in per_query)
        chunk_rows = [r.chunk_metrics for r in per_query if r.chunk_metrics is not None]
        macro_chunk = M.macro_average(chunk_rows) if chunk_rows else None

        if macro_chunk is None:
            level = "disease"
        elif len(chunk_rows) == len(per_query):
            level = "both"
        else:
            level = "both"

        return EvaluationReport(
            mode=self.mode,
            k=self.k,
            level=level,
            qrels_hash=self.qrels.qrels_hash,
            corpus_size=self.corpus_size,
            timestamp=datetime.now(timezone.utc).isoformat(),
            macro_disease=macro_disease,
            macro_chunk=macro_chunk,
            per_query=per_query,
            errors=errors,
        )
