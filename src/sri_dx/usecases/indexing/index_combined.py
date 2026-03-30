"""UseCase combinado: indexa documentos y chunks en una sola pasada del JSONL.

Elimina la doble lectura de los archivos JSONL fusionando las Fases 2 y 3.
Para cada documento: (a) prepara IndexDocument → batch docs sink,
(b) genera chunks → batch chunks sink. Comparte ConceptExtractor.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sri_dx.core.ports.acquisition.document_source import DocumentSourcePort
from sri_dx.core.ports.acquisition.manifest_store import ManifestStorePort, ManifestEntry
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
from sri_dx.modules.indexing.prepare import prepare_index_document
from sri_dx.modules.indexing.chunking import chunk_acquired_document, ChunkingConfig
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
from sri_dx.modules.indexing.index_upsert import IndexUpsert
from sri_dx.modules.indexing.pipeline_version import PIPELINE_VERSION

logger = logging.getLogger(__name__)


@dataclass
class IndexCombinedUseCase:
    """Indexa docs + chunks en una sola iteración del JSONL."""

    source: DocumentSourcePort
    doc_sink: OpenSearchIndexSink
    chunk_sink: OpenSearchChunksSink
    manifest: ManifestStorePort
    doc_batch_size: int = 500
    chunk_batch_size: int = 500
    report_dir: Path = Path("data/index/reports")
    bad_docs_path: Path = Path("data/index/bad_docs.jsonl")

    def run(self, *, refresh: bool = False, with_concepts: bool = True) -> dict[str, Any]:
        self.doc_sink.ensure_index()
        self.chunk_sink.ensure_index()
        self.doc_sink.set_refresh_interval("-1")
        self.chunk_sink.set_refresh_interval("-1")
        self.report_dir.mkdir(parents=True, exist_ok=True)

        extractor = ConceptExtractor() if with_concepts else None

        chunker = None
        try:
            from sri_dx.modules.chunking.semantic_chunker import SemanticChunker
            chunker = SemanticChunker()
        except ImportError:
            pass

        seen = 0
        skipped = 0
        docs_indexed = 0
        chunks_seen = 0
        chunks_indexed = 0
        errors: list[str] = []

        doc_batch: list[IndexUpsert] = []
        chunk_batch: list = []

        for acquired in self.source.iter_documents():
            seen += 1
            try:
                # -- Fase 2: documento --
                idx_doc = prepare_index_document(acquired, concept_extractor=extractor)

                prev = self.manifest.get(idx_doc.doc_id)
                if prev and prev.content_hash == idx_doc.content_hash and prev.pipeline_version == PIPELINE_VERSION:
                    skipped += 1
                    continue

                text_all = " ".join([idx_doc.title, idx_doc.sections_text, idx_doc.body])
                concept_ids = extractor.extract(text_all, language=idx_doc.language or "es") if extractor else []
                upsert = IndexUpsert(doc=idx_doc, concept_ids=concept_ids)
                doc_batch.append(upsert)

                if len(doc_batch) >= self.doc_batch_size:
                    docs_indexed += self._flush_docs(doc_batch)
                    doc_batch.clear()

                # -- Fase 3: chunks --
                for ch in chunk_acquired_document(
                    acquired,
                    concept_extractor=extractor,
                    semantic_chunker=chunker,
                ):
                    chunk_batch.append(ch)
                    chunks_seen += 1
                    if len(chunk_batch) >= self.chunk_batch_size:
                        chunks_indexed += self.chunk_sink.bulk_upsert(chunk_batch, refresh=False)
                        chunk_batch.clear()

            except Exception as e:
                error_msg = f"Error processing {acquired.doc_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                self._log_bad_doc(acquired, str(e))

        # Flush remaining
        if doc_batch:
            docs_indexed += self._flush_docs(doc_batch)
        if chunk_batch:
            chunks_indexed += self.chunk_sink.bulk_upsert(chunk_batch, refresh=False)

        self.doc_sink.set_refresh_interval("1s")
        self.chunk_sink.set_refresh_interval("1s")

        if refresh:
            self.doc_sink.client.indices.refresh(index=self.doc_sink.cfg.index_name)
            self.chunk_sink.client.indices.refresh(index=self.chunk_sink.cfg.index_name)

        report = {
            "timestamp": datetime.now().isoformat(),
            "docs_seen": seen,
            "docs_skipped_same_hash": skipped,
            "docs_indexed_ok": docs_indexed,
            "chunks_seen": chunks_seen,
            "chunks_indexed_ok": chunks_indexed,
            "pipeline_version": PIPELINE_VERSION,
            "errors_count": len(errors),
            "errors_sample": errors[:10],
        }
        self._save_report(report)
        return report

    def _flush_docs(self, batch: list[IndexUpsert]) -> int:
        ok_ids = self.doc_sink.bulk_upsert(batch, refresh=False)
        content_hashes = {x.doc.doc_id: x.doc.content_hash for x in batch}
        self.manifest.upsert_many(
            ManifestEntry(doc_id=_id, content_hash=content_hashes[_id], pipeline_version=PIPELINE_VERSION)
            for _id in ok_ids
        )
        return len(ok_ids)

    def _log_bad_doc(self, doc: Any, reason: str) -> None:
        self.bad_docs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.bad_docs_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"doc_id": doc.doc_id, "url": doc.url, "reason": reason}) + "\n")

    def _save_report(self, report: dict[str, Any]) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.report_dir / f"index_combined_{ts}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
