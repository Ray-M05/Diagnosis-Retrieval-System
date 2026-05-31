"""
Orchestrates the complete web-search-and-enrich pipeline:

1. Run the local hybrid retriever (``TwoStageRetrievalPipeline``).
2. Evaluate whether the local results are sufficient.
3. If sufficient → return local results with no web search.
4. If insufficient →
   a. Extract symptom concepts from the query.
   b. Query all three medical APIs in parallel.
   c. Convert external documents to ``AcquiredDocument`` dicts.
   d. Deduplicate against the WEB corpus (``doc_sink``/``chunk_sink`` point at
      the dedicated web indices, so web ingestion never touches the local
      corpus and dedup is web-vs-web by construction).
   e. Write delta JSONL.
   f. Index delta with ``IndexCombinedUseCase`` (docs + chunks in one pass)
      into the WEB indices.
   g. Re-run the hybrid retriever on the LOCAL index and interleave fresh web
      chunks found in the web index.
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

from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
from sri_dx.adapters.medical_apis.medical_api_search_service import (
    MedicalApiSearchService,
)
from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
from sri_dx.modules.indexing.chunking import ChunkingConfig
from sri_dx.modules.web_search.converters import external_to_acquired_dict
from sri_dx.modules.web_search.deduplicator import ApiDocumentDeduplicator, identity_keys
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
from sri_dx.usecases.indexing.embed_chunks import EmbedChunksUseCase
from sri_dx.usecases.indexing.schemas.embed_chunks_config import EmbedChunksConfig
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


# Entity domains worth sending to the medical APIs. PROBLEM/SYMPTOM/DISEASE name
# the clinical picture; ANATOMY/TEST add discriminating context (e.g. "bone
# marrow", "blood counts") that often separates rare from common diagnoses.
_NER_QUERY_DOMAINS = {"PROBLEM", "SYMPTOM", "DISEASE", "ANATOMY", "TEST", "TREATMENT"}
_NER_MIN_SCORE = 0.45


def _extract_symptoms(query: str) -> list[str]:
    """Extract clinical terms from *query* to feed the medical-API search.

    Prefers the biomedical NER model, which recognises real clinical vocabulary
    (chondritis, cytopenias, vacuoles, macrocytic anemia…) that the tiny closed
    :class:`ConceptExtractor` lexicon (7 concepts) silently drops. Dropping those
    discriminating terms is exactly what made web search return generic noise
    instead of the rare condition. The lexicon and a delimiter split remain as
    fallbacks so the function still works if the model is unavailable.

    Returns terms in their order of appearance in the query, deduplicated.
    """
    ner_terms = _extract_symptoms_ner(query)
    if ner_terms:
        logger.info("Symptoms (NER): %s", ner_terms)
        return ner_terms

    try:
        from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
        concepts = ConceptExtractor().extract(query, language="en")
        if concepts:
            logger.info("Symptoms (lexicon fallback): %s", concepts)
            return list(concepts)
    except Exception as exc:  # noqa: BLE001
        logger.debug("ConceptExtractor unavailable (%s), using split fallback", exc)

    # Last resort: split on commas / 'and'
    parts = re.split(r",\s*|\s+and\s+", query, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _extract_symptoms_ner(query: str) -> list[str]:
    """Run biomedical NER and return relevant clinical terms (deduped, in order)."""
    try:
        from sri_dx.adapters.embeddings.biomedical_ner_adapter import (
            BiomedicalNERAdapter,
        )
    except ImportError:
        logger.debug("BiomedicalNERAdapter unavailable; skipping NER extraction")
        return []

    try:
        logger.info("Symptom extraction: using biomedical NER")
        entities = BiomedicalNERAdapter.get_instance().predict_batch([query])[0]
    except Exception as exc:  # noqa: BLE001
        logger.warning("NER extraction failed (%s); falling back to lexicon", exc)
        return []

    seen: set[str] = set()
    terms: list[str] = []
    for ent in entities:
        if ent.get("domain_label") not in _NER_QUERY_DOMAINS:
            continue
        if float(ent.get("score") or 0.0) < _NER_MIN_SCORE:
            continue
        term = re.sub(r"\s+", " ", str(ent.get("word") or "")).strip()
        # Drop subword fragments and trivially short tokens.
        if len(term) < 3 or term.startswith("##"):
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
    logger.info(
        "NER extraction: %d raw entities -> %d query terms kept", len(entities), len(terms)
    )
    return terms


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
        OpenSearch sink for the WEB docs index (``clinical_docs_web``).
    chunk_sink:
        OpenSearch sink for the WEB chunks index (``clinical_chunks_web``).
    manifest:
        SQLite manifest store for incremental indexing.
    report_dir:
        Directory where JSON run reports are saved.
    chunk_cfg:
        Chunking configuration for ``IndexCombinedUseCase``.
    embed_config:
        :class:`EmbedChunksConfig` pointing at the WEB chunks index (source) and
        the SHARED embeddings index (sink). After web chunks are indexed they are
        embedded into the shared vector index so web evidence competes by kNN in
        the normal hybrid retrieval, exactly like local chunks. When ``None``,
        the embedding step is skipped (web stays BM25-only — legacy behaviour).
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
    embed_config: EmbedChunksConfig | None = None
    local_pipeline: TwoStageRetrievalPipeline | None = None

    # ------------------------------------------------------------------

    @property
    def _sufficiency_pipeline(self) -> TwoStageRetrievalPipeline:
        """Pipeline used to measure local sufficiency (Stage 1).

        Defaults to ``pipeline`` for backward compatibility, but callers should
        pass a LOCAL-only ``local_pipeline`` so sufficiency reflects the local
        corpus alone. Otherwise a combined local+web ``pipeline`` would let web
        content from *previous* queries make the local picture look sufficient
        and suppress a fresh web search.
        """
        return self.local_pipeline or self.pipeline

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

        # Stage 1 — Local retrieval (sufficiency is measured on the LOCAL corpus)
        logger.info("Stage 1: running local two-stage retrieval")
        local_pipeline = self._sufficiency_pipeline
        configured_k = getattr(getattr(local_pipeline, "config", None), "final_results", 10)
        if not isinstance(configured_k, int):
            configured_k = 10
        sufficiency_k = max(configured_k, 20)
        try:
            local_raw = local_pipeline.search(query, final_results=sufficiency_k)
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
                if acq_dict is None:
                    logger.debug("Skipping content-less document: '%s'", ext.title[:60])
                    continue
                pairs.append((ext, acq_dict))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Converter error for '%s': %s", ext.title[:60], exc
                )

        existing_hashes, existing_keys = self._load_existing_document_identity(pairs)
        deduplicator = ApiDocumentDeduplicator(
            existing_content_hashes=existing_hashes,
            existing_identity_keys=existing_keys,
        )
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
            # All API docs were duplicates, but web chunks from previous runs may
            # still lack embeddings (e.g. a web corpus ingested before this change).
            # Embedding is idempotent (skip_existing by hash), so run it here too so
            # those chunks gain vectors and can finally be retrieved by kNN.
            self._embed_web_chunks()
            # The combined (local+web) pipeline already retrieves the web chunks
            # indexed by previous runs of this query via the normal hybrid path,
            # so there is no separate lexical web pass to merge anymore.
            final_raw = self.pipeline.search(query)
            final_results = _results_to_response(
                final_raw,
                self._load_docs_by_doc_id(final_raw),
            )
            report = WebSearchRunReport(
                query=query,
                query_hash=q_hash,
                web_search_triggered=True,
                sufficiency=decision,
                api_retrieval=api_stats,
                deduplication=dedup_stats,
                results=_renumber_results(final_results),
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

        def _as_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        idx_stats = IndexingStats(
            delta_path=str(delta_path),
            docs_indexed=_as_int(index_report.get("docs_indexed_ok", 0)),
            chunks_indexed=_as_int(index_report.get("chunks_indexed_ok", 0)),
        )
        logger.info(
            "Indexing: docs=%d  chunks=%d",
            idx_stats.docs_indexed, idx_stats.chunks_indexed,
        )

        # Stage 6b — Embed the freshly-indexed web chunks into the SHARED vector
        # index. Without this, web chunks live in the web chunks index but have no
        # vectors, so they can never be retrieved by kNN — they would only ever
        # compete on BM25. Embedding them here lets web evidence go through the
        # exact same hybrid (BM25 + kNN) + rerank path as local chunks.
        if idx_stats.chunks_indexed > 0:
            self._embed_web_chunks()

        # Stage 7 — Re-run retrieval on the enriched index. The pipeline is the
        # COMBINED local+web pipeline (see main._build_pipeline(web=True)), so this
        # single hybrid+rerank pass returns local and web chunks ranked together by
        # the same cross-encoder. No separate lexical web pass, no artificial merge.
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

        # Build and save report
        report = WebSearchRunReport(
            query=query,
            query_hash=q_hash,
            web_search_triggered=True,
            sufficiency=decision,
            api_retrieval=api_stats,
            deduplication=dedup_stats,
            indexing=idx_stats,
            results=_renumber_results(final_results),
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

    def _load_existing_document_identity(
        self,
        pairs: list[tuple[ExternalApiDocument, dict]],
    ) -> tuple[set[str], set[str]]:
        """Return already-indexed hashes and identity keys for API candidates."""
        doc_ids = list(dict.fromkeys(
            str(acq.get("doc_id") or "")
            for _, acq in pairs
            if acq.get("doc_id")
        ))
        content_hashes = list(dict.fromkeys(
            str(acq.get("content_hash") or "")
            for _, acq in pairs
            if acq.get("content_hash")
        ))
        candidate_keys = (
            set().union(*(identity_keys(ext) for ext, _ in pairs))
            if pairs else set()
        )

        existing_hashes: set[str] = set()
        existing_keys: set[str] = set()

        def register(source: dict) -> None:
            content_hash = str(source.get("content_hash") or "").strip()
            if content_hash:
                existing_hashes.add(content_hash)
            url = str(source.get("url") or "").strip()
            if url:
                existing_keys.add(f"url:{url}")

        if doc_ids:
            try:
                response = self.doc_sink.client.mget(
                    index=self.doc_sink.cfg.index_name,
                    body={"ids": doc_ids},
                )
                docs = response.get("docs", []) if isinstance(response, dict) else []
                for doc in docs:
                    if doc.get("found"):
                        register(doc.get("_source") or {})
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not load existing docs for dedup by id: %s", exc)

        if content_hashes:
            try:
                response = self.doc_sink.client.search(
                    index=self.doc_sink.cfg.index_name,
                    body={
                        "size": min(len(content_hashes), 1000),
                        "_source": ["content_hash", "url"],
                        "query": {"terms": {"content_hash": content_hashes}},
                    },
                )
                hits = (
                    response.get("hits", {}).get("hits", [])
                    if isinstance(response, dict) else []
                )
                for hit in hits:
                    register(hit.get("_source") or {})
            except NotFoundError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not load existing docs for dedup by hash: %s", exc)

        existing_keys &= candidate_keys
        logger.info(
            "Dedup corpus check: existing_hashes=%d existing_identity_keys=%d",
            len(existing_hashes),
            len(existing_keys),
        )
        return existing_hashes, existing_keys

    def _embed_web_chunks(self) -> None:
        """Embed freshly-indexed web chunks into the SHARED vector index.

        Reuses :class:`EmbedChunksUseCase`, which reads chunks from the WEB chunks
        index and writes vectors to the shared embeddings index. ``skip_existing``
        (hash-based) means only chunks without an up-to-date embedding are encoded,
        so re-running the same query is cheap. The encode runs synchronously inside
        the request; the first search for a new case is therefore slower, later ones
        reuse the vectors.
        """
        if self.embed_config is None:
            logger.info(
                "Stage 6b: embed_config not provided — skipping web embedding "
                "(web chunks will only compete on BM25)"
            )
            return
        try:
            logger.info("Stage 6b: embedding web chunks into the shared vector index")
            result = EmbedChunksUseCase(self.embed_config).run()
            logger.info(
                "Stage 6b complete: generated=%d stored=%d skipped=%d errors=%d",
                result.embeddings_generated,
                result.embeddings_stored,
                result.skipped_already_embedded,
                len(result.errors),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Web chunk embedding failed: %s", exc)

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
