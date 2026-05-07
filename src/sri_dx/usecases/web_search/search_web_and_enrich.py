"""
Orchestrates the complete web-search-and-enrich pipeline:

1. Run the local hybrid retriever (``TwoStageRetrievalPipeline``).
2. Evaluate whether the local results are sufficient.
3. If sufficient → return local results with no web search.
4. If insufficient →
   a. Extract symptom concepts from the query.
   b. Query all three medical APIs in parallel.
   c. Convert external documents to ``AcquiredDocument`` dicts.
   d. Deduplicate against existing corpus.
   e. Write delta JSONL.
   f. Index delta with ``IndexCombinedUseCase`` (docs + chunks in one pass).
   g. Re-run the hybrid retriever on the now-enriched index.
5. Return a :class:`WebSearchRunReport`.

All text is in English.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
from sri_dx.adapters.medical_apis.medical_api_search_service import (
    MedicalApiSearchService,
)
from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
from sri_dx.modules.indexing.chunking import ChunkingConfig
from sri_dx.modules.web_search.converters import external_to_acquired_dict
from sri_dx.modules.web_search.deduplicator import ApiDocumentDeduplicator
from sri_dx.modules.web_search.delta_writer import JsonlDeltaWriter
from sri_dx.modules.web_search.schemas import (
    DeduplicationStats,
    ExternalApiDocument,
    IndexingStats,
    LocalRetrievalResult,
    RetrievedChunkResult,
    WebSearchRunReport,
)
from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
from sri_dx.usecases.indexing.index_combined import IndexCombinedUseCase
from sri_dx.usecases.search.tow_stage_retrieval_pipeline import (
    RetrievalResult,
    TwoStageRetrievalPipeline,
)

logger = logging.getLogger(__name__)


def _query_hash(query: str) -> str:
    """Return the first 8 hex digits of the SHA-1 of the query."""
    return hashlib.sha1(query.encode("utf-8", errors="ignore")).hexdigest()[:8]


def _retrieval_results_to_chunks(
    results: list[RetrievalResult],
) -> list[RetrievedChunkResult]:
    """
    Convert :class:`RetrievalResult` objects from the pipeline to the
    :class:`RetrievedChunkResult` schema used by the sufficiency evaluator.
    """
    chunks: list[RetrievedChunkResult] = []
    for r in results:
        meta = r.metadata or {}
        chunks.append(
            RetrievedChunkResult(
                chunk_id=meta.get("chunk_id", r.doc_id),
                doc_id=r.doc_id,
                title=meta.get("title", ""),
                url=meta.get("url", ""),
                source_domain=meta.get("source_domain", ""),
                chunk_text=r.content or meta.get("content", ""),
                final_score=r.rerank_score,
                bm25_score=r.lexical_score,
                vector_score=r.vector_score,
                rerank_score=r.rerank_score,
                section_heading=meta.get("section_heading"),
                concept_ids=meta.get("concept_ids", []),
            )
        )
    return chunks


def _extract_symptoms(query: str) -> list[str]:
    """
    Extract symptom/concept terms from the query using the existing
    :class:`ConceptExtractor`.

    Falls back to splitting by common delimiters if the extractor is
    unavailable.
    """
    try:
        from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
        extractor = ConceptExtractor()
        concepts = extractor.extract(query, language="en")
        if concepts:
            logger.debug("Symptoms extracted: %s", concepts)
            return list(concepts)
    except Exception as exc:  # noqa: BLE001
        logger.debug("ConceptExtractor unavailable (%s), using fallback", exc)

    # Fallback: split on commas / 'and'
    import re
    if "," in query or re.search(r"\band\b", query, flags=re.IGNORECASE):
        parts = re.split(r",\s*|\s+and\s+", query, flags=re.IGNORECASE)
    else:
        # If it's just space-separated keywords, split by space, ignoring small stop words
        parts = [w for w in query.split() if len(w) > 3]
        
    return [p.strip() for p in parts if p.strip()]


def _results_to_response(results: list[RetrievalResult]) -> list[dict]:
    """Serialise retrieval results to plain dicts for the report."""
    out: list[dict] = []
    for i, r in enumerate(results, start=1):
        meta = r.metadata or {}
        out.append({
            "rank": i,
            "doc_id": r.doc_id,
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "source_domain": meta.get("source_domain", ""),
            "rerank_score": round(r.rerank_score, 4),
            "hybrid_score": round(r.original_hybrid_score, 4),
            "chunk_text": (r.content or "")[:400],
        })
    return out


# Use case

@dataclass
class SearchWebAndEnrichUseCase:
    """
    Orchestrates the full web-search-and-enrich pipeline.

    Parameters
    ----------
    pipeline:
        Configured :class:`TwoStageRetrievalPipeline` (hybrid + cross-encoder).
    sufficiency_evaluator:
        :class:`LocalSufficiencyEvaluator` with desired thresholds.
    api_service:
        :class:`MedicalApiSearchService` (parallel async, wraps 3 clients).
    delta_writer:
        :class:`JsonlDeltaWriter` that writes delta files.
    doc_sink:
        OpenSearch sink for ``clinical_docs``.
    chunk_sink:
        OpenSearch sink for ``clinical_chunks``.
    manifest:
        SQLite manifest store for incremental indexing.
    report_dir:
        Directory where JSON run reports are saved.
    chunk_cfg:
        Chunking configuration for ``IndexCombinedUseCase``.
    """

    pipeline: TwoStageRetrievalPipeline
    sufficiency_evaluator: LocalSufficiencyEvaluator
    api_service: MedicalApiSearchService
    delta_writer: JsonlDeltaWriter
    doc_sink: OpenSearchIndexSink
    chunk_sink: OpenSearchChunksSink
    manifest: SqliteManifestStore
    report_dir: Path = Path("data/web_search/reports")
    chunk_cfg: ChunkingConfig = field(default_factory=ChunkingConfig)

    # ------------------------------------------------------------------

    def run(self, query: str) -> WebSearchRunReport:
        """
        Execute the full pipeline for *query* and return a run report.

        Parameters
        ----------
        query:
            User symptom query in English.
        """
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")

        logger.info("=== SearchWebAndEnrichUseCase: '%s...' ===", query[:80])
        q_hash = _query_hash(query)

        # Stage 1 — Local retrieval
        logger.info("Stage 1: running local two-stage retrieval")
        try:
            local_raw = self.pipeline.search(query)
        except Exception as exc:
            logger.error("Local retrieval failed: %s", exc)
            local_raw = []

        chunks = _retrieval_results_to_chunks(local_raw)
        symptoms = _extract_symptoms(query)
        local_result = LocalRetrievalResult(
            query=query,
            extracted_symptoms=symptoms,
            results=chunks,
        )

        # Stage 2 — Sufficiency evaluation
        decision = self.sufficiency_evaluator.evaluate(local_result)
        logger.info(
            "Sufficiency: sufficient=%s  score=%.3f  failed=%s",
            decision.sufficient,
            decision.insufficiency_score,
            decision.failed_criteria,
        )

        if decision.sufficient:
            logger.info("Local results are sufficient — skipping web search")
            report = WebSearchRunReport(
                query=query,
                query_hash=q_hash,
                web_search_triggered=False,
                sufficiency=decision,
                results=_results_to_response(local_raw),
                local_results=_results_to_response(local_raw),
            )
            self._save_report(report)
            return report

        # Stage 3 — External API search (parallel)
        logger.info("Stage 3: querying external medical APIs")
        external_docs, api_stats = self.api_service.search_sync(symptoms)
        logger.info("APIs returned %d document(s) total", api_stats.total)

        # Stage 4 — Convert + Deduplicate
        logger.info("Stage 4: converting and deduplicating")
        pairs: list[tuple[ExternalApiDocument, dict]] = []
        for ext in external_docs:
            try:
                acq_dict = external_to_acquired_dict(
                    ext, query_id=q_hash, original_query=query
                )
                pairs.append((ext, acq_dict))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Converter error for '%s': %s", ext.title[:60], exc
                )

        deduplicator = ApiDocumentDeduplicator()
        kept_pairs = deduplicator.filter(pairs)
        new_docs = [acq_dict for _, acq_dict in kept_pairs]

        dedup_stats = DeduplicationStats(
            retrieved_total=len(pairs),
            duplicates_removed=len(pairs) - len(kept_pairs),
            new_documents=len(new_docs),
        )
        logger.info(
            "Dedup: total=%d  removed=%d  new=%d",
            dedup_stats.retrieved_total,
            dedup_stats.duplicates_removed,
            dedup_stats.new_documents,
        )

        if not new_docs:
            logger.info("No new documents after dedup — re-running retrieval without indexing")
            final_raw = self.pipeline.search(query)
            report = WebSearchRunReport(
                query=query,
                query_hash=q_hash,
                web_search_triggered=True,
                sufficiency=decision,
                api_retrieval=api_stats,
                deduplication=dedup_stats,
                results=_results_to_response(final_raw),
                local_results=_results_to_response(local_raw),
            )
            self._save_report(report)
            return report

        # Stage 5 — Write delta JSONL
        logger.info("Stage 5: writing delta JSONL (%d docs)", len(new_docs))
        delta_path = self.delta_writer.write(new_docs, q_hash)
        logger.info("Delta written to '%s'", delta_path)

        # Stage 6 — Index delta (docs + chunks in one pass)
        logger.info("Stage 6: indexing delta with IndexCombinedUseCase")
        source = JsonlDocumentSource([delta_path])
        indexer = IndexCombinedUseCase(
            source=source,
            doc_sink=self.doc_sink,
            chunk_sink=self.chunk_sink,
            manifest=self.manifest,
            chunk_cfg=self.chunk_cfg,
        )
        try:
            index_report = indexer.run(refresh=True, with_concepts=True)
        except Exception as exc:
            logger.error("Indexing failed: %s", exc)
            index_report = {}

        idx_stats = IndexingStats(
            delta_path=str(delta_path),
            docs_indexed=index_report.get("docs_indexed_ok", 0),
            chunks_indexed=index_report.get("chunks_indexed_ok", 0),
        )
        logger.info(
            "Indexing: docs=%d  chunks=%d",
            idx_stats.docs_indexed, idx_stats.chunks_indexed,
        )

        # Stage 7 — Re-run retrieval on enriched index
        logger.info("Stage 7: re-running retrieval on enriched index")
        try:
            final_raw = self.pipeline.search(query)
        except Exception as exc:
            logger.error("Final retrieval failed: %s", exc)
            final_raw = local_raw

        # Build and save report
        report = WebSearchRunReport(
            query=query,
            query_hash=q_hash,
            web_search_triggered=True,
            sufficiency=decision,
            api_retrieval=api_stats,
            deduplication=dedup_stats,
            indexing=idx_stats,
            results=_results_to_response(final_raw),
            local_results=_results_to_response(local_raw),
        )
        self._save_report(report)
        logger.info(
            "=== SearchWebAndEnrichUseCase complete: %d final result(s) ===",
            len(final_raw),
        )
        return report

    def _save_report(self, report: WebSearchRunReport) -> None:
        """Serialise *report* to a timestamped JSON file."""
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = self.report_dir / f"web_search_run_{ts}_{report.query_hash}.json"

            def _default(obj: Any) -> Any:
                if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                    return dataclasses.asdict(obj)
                return str(obj)

            with path.open("w", encoding="utf-8") as fh:
                json.dump(dataclasses.asdict(report), fh, indent=2, ensure_ascii=False, default=_default)

            logger.info("Report saved to '%s'", path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not save report: %s", exc)
