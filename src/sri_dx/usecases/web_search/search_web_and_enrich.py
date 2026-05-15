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
import re
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

from opensearchpy import NotFoundError

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
from sri_dx.usecases.search.two_stage_retrieval_pipeline import (
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
    parts = re.split(r",\s*|\s+and\s+", query, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _results_to_response(
    results: list[RetrievalResult],
    docs_by_doc_id: dict[str, dict[str, str]] | None = None,
) -> list[dict]:
    """Serialise retrieval results to plain dicts for the report."""
    out: list[dict] = []
    doc_lookup = docs_by_doc_id or {}
    for i, r in enumerate(results, start=1):
        meta = r.metadata or {}
        doc_meta = doc_lookup.get(r.doc_id, {})
        chunk_id = meta.get("chunk_id", r.doc_id)
        title = _clean_display_title(doc_meta.get("title") or meta.get("title") or "")
        url = meta.get("url") or doc_meta.get("url") or ""
        source_domain = meta.get("source_domain") or doc_meta.get("source_domain") or ""
        out.append({
            "rank": i,
            "doc_id": r.doc_id,
            "chunk_id": chunk_id,
            "title": title,
            "url": url,
            "source_domain": source_domain,
            "rerank_score": round(r.rerank_score, 4),
            "hybrid_score": round(r.original_hybrid_score, 4),
            "chunk_text": (r.content or "")[:400],
            "seed_group": meta.get("seed_group") or doc_meta.get("seed_group") or "",
        })
    return out


def _renumber_results(results: list[dict]) -> list[dict]:
    for i, result in enumerate(results, start=1):
        result["rank"] = i
    return results


def _clean_display_title(title: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", unescape(str(title or "")))
    return re.sub(r"\s+", " ", cleaned).strip()


def _interleave_api_results(base_results: list[dict], api_results: list[dict], max_api: int = 3) -> list[dict]:
    """Mix a few API hits into the web ranking so fresh evidence is visible."""
    if not api_results:
        return _renumber_results(base_results)

    seen_chunks = {str(r.get("chunk_id") or "") for r in base_results}
    unique_api = [
        result for result in api_results
        if str(result.get("chunk_id") or "") not in seen_chunks
    ][:max_api]
    if not unique_api:
        return _renumber_results(base_results)

    mixed: list[dict] = []
    api_iter = iter(unique_api)
    for i, result in enumerate(base_results, start=1):
        mixed.append(result)
        if i in {2, 5, 8}:
            next_api = next(api_iter, None)
            if next_api is not None:
                mixed.append(next_api)
    mixed.extend(api_iter)
    return _renumber_results(mixed)


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
                results=_results_to_response(
                    local_raw,
                    self._load_docs_by_doc_id(local_raw),
                ),
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
            final_results = _results_to_response(
                final_raw,
                self._load_docs_by_doc_id(final_raw),
            )
            api_results = self._search_api_chunks_for_query(query=query, query_hash=q_hash)
            report = WebSearchRunReport(
                query=query,
                query_hash=q_hash,
                web_search_triggered=True,
                sufficiency=decision,
                api_retrieval=api_stats,
                deduplication=dedup_stats,
                results=_interleave_api_results(final_results, api_results),
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
        final_results = _results_to_response(
            final_raw,
            self._load_docs_by_doc_id(final_raw),
        )
        api_results = self._search_api_chunks_for_query(query=query, query_hash=q_hash)

        # Build and save report
        report = WebSearchRunReport(
            query=query,
            query_hash=q_hash,
            web_search_triggered=True,
            sufficiency=decision,
            api_retrieval=api_stats,
            deduplication=dedup_stats,
            indexing=idx_stats,
            results=_interleave_api_results(final_results, api_results),
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

    def _load_docs_by_doc_id(self, results: list[RetrievalResult]) -> dict[str, dict[str, str]]:
        """Fetch document metadata for chunk-level retrieval results."""
        doc_ids = list(dict.fromkeys(r.doc_id for r in results if r.doc_id))
        return self._load_doc_records_by_id(doc_ids)

    def _search_api_chunks_for_query(self, *, query: str, query_hash: str, size: int = 6) -> list[dict]:
        """Search API-ingested chunks for this web query."""
        body = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["section_heading^3", "chunk_text^1"],
                                "type": "best_fields",
                                "operator": "or",
                            }
                        }
                    ],
                    "filter": [{"term": {"seed_id": query_hash}}],
                }
            },
        }

        try:
            response = self.chunk_sink.client.search(
                index=self.chunk_sink.cfg.index_name,
                body=body,
            )
        except NotFoundError:
            return []
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not search API chunks for web query: %s", exc)
            return []

        hits = response.get("hits", {}).get("hits", [])
        doc_ids = [str((hit.get("_source") or {}).get("doc_id") or "") for hit in hits]
        docs_by_id = self._load_doc_records_by_id(doc_ids)

        results: list[dict] = []
        for hit in hits:
            source = hit.get("_source") or {}
            doc_id = str(source.get("doc_id") or hit.get("_id") or "")
            doc_meta = docs_by_id.get(doc_id, {})
            results.append({
                "rank": 0,
                "doc_id": doc_id,
                "chunk_id": str(source.get("chunk_id") or hit.get("_id") or doc_id),
                "title": _clean_display_title(doc_meta.get("title") or str(source.get("section_heading") or doc_id)),
                "url": doc_meta.get("url") or str(source.get("url") or ""),
                "source_domain": doc_meta.get("source_domain") or str(source.get("source_domain") or ""),
                "rerank_score": 0.0,
                "hybrid_score": float(hit.get("_score") or 0.0),
                "chunk_text": str(source.get("chunk_text") or "")[:400],
                "seed_group": str(source.get("seed_group") or doc_meta.get("seed_group") or ""),
            })
        return results

    def _load_doc_records_by_id(self, doc_ids: list[str]) -> dict[str, dict[str, str]]:
        ids = list(dict.fromkeys(doc_id for doc_id in doc_ids if doc_id))
        if not ids:
            return {}

        try:
            response = self.doc_sink.client.mget(
                index=self.doc_sink.cfg.index_name,
                body={"ids": ids},
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not load document metadata: %s", exc)
            return {}

        docs: dict[str, dict[str, str]] = {}
        for doc in response.get("docs", []):
            if not doc.get("found"):
                continue
            source = doc.get("_source") or {}
            docs[str(doc.get("_id"))] = {
                "title": _clean_display_title(str(source.get("title") or "")),
                "url": str(source.get("url") or "").strip(),
                "source_domain": str(source.get("source_domain") or "").strip(),
                "seed_group": str(source.get("seed_group") or "").strip(),
            }
        return docs
