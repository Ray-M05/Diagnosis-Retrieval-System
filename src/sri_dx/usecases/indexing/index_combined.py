"""UseCase combinado: indexa documentos y chunks en una sola pasada del JSONL.

Elimina la doble lectura de los archivos JSONL fusionando las Fases 2 y 3.
Para cada documento: (a) prepara IndexDocument → batch docs sink,
(b) genera chunks → batch chunks sink. Comparte ConceptExtractor.
"""
from __future__ import annotations

import json
import logging
import sys
import time
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

_LOG_EVERY = 50  # Print progress every N documents


def _print_progress(seen: int, total: int, chunks_seen: int, t0: float) -> None:
    elapsed = time.time() - t0
    rate = seen / elapsed if elapsed > 0 else 0
    eta = (total - seen) / rate if rate > 0 else 0
    pct = seen / total * 100 if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * seen / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(
        f"\r  [{bar}] {pct:5.1f}%  doc {seen}/{total}"
        f"  chunks={chunks_seen}"
        f"  {rate:.1f} doc/s"
        f"  ETA {eta/60:.1f}min"
    )
    sys.stdout.flush()


@dataclass
class IndexCombinedUseCase:
    """Indexa docs + chunks en una sola iteración del JSONL."""

    source: DocumentSourcePort
    doc_sink: OpenSearchIndexSink
    chunk_sink: OpenSearchChunksSink
    manifest: ManifestStorePort
    doc_batch_size: int = 500
    chunk_batch_size: int = 500
    chunk_cfg: ChunkingConfig = field(default_factory=ChunkingConfig)
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
        if self.chunk_cfg.use_semantic_chunker:
            try:
                from sri_dx.modules.chunking.semantic_chunker import SemanticChunker
                chunker = SemanticChunker.get_instance()
                _ = chunker.model  # preload para que no cuente en el primer doc
                print(f"  Estrategia overflow: SemanticChunker ({chunker.config.model_name})")
                print(f"  similarity_threshold={chunker.config.similarity_threshold}  max_chars={self.chunk_cfg.max_chars}")
            except ImportError:
                print("  SemanticChunker no disponible → ventana deslizante")
        else:
            print(f"  Estrategia overflow: ventana deslizante (overlap={self.chunk_cfg.overlap_chars} chars)")

        # Count total documents (counting JSONL lines without parsing)
        total_docs = 0
        try:
            for p in self.source.paths:  # type: ignore[attr-defined]
                with open(p, "r", encoding="utf-8") as f:
                    total_docs += sum(1 for line in f if line.strip())
        except Exception:
            pass

        seen = 0
        skipped = 0
        docs_indexed = 0
        chunks_seen = 0
        chunks_indexed = 0
        errors: list[str] = []

        doc_batch: list[IndexUpsert] = []
        chunk_batch: list = []

        t0 = time.time()
        print(f"\n  Procesando {total_docs or '?'} documentos...")

        for acquired in self.source.iter_documents():
            seen += 1
            try:
                # -- Fase 2: documento --
                idx_doc = prepare_index_document(acquired, concept_extractor=extractor)

                prev = self.manifest.get(idx_doc.doc_id)
                if prev and prev.content_hash == idx_doc.content_hash and prev.pipeline_version == PIPELINE_VERSION:
                    skipped += 1
                    if seen % _LOG_EVERY == 0:
                        _print_progress(seen, total_docs, chunks_seen, t0)
                    continue

                text_all = " ".join([idx_doc.title, idx_doc.sections_text, idx_doc.body])
                concept_ids = extractor.extract(text_all, language=idx_doc.language or "es") if extractor else []
                upsert = IndexUpsert(doc=idx_doc, concept_ids=concept_ids)
                doc_batch.append(upsert)

                if len(doc_batch) >= self.doc_batch_size:
                    docs_indexed += self._flush_docs(doc_batch)
                    doc_batch.clear()
                    print(f"\n  → Flush docs: {docs_indexed} docs indexados")

                # -- Fase 3: chunks --
                doc_chunks_before = chunks_seen
                for ch in chunk_acquired_document(
                    acquired,
                    cfg=self.chunk_cfg,
                    concept_extractor=extractor,
                    semantic_chunker=chunker,
                ):
                    chunk_batch.append(ch)
                    chunks_seen += 1
                    if len(chunk_batch) >= self.chunk_batch_size:
                        chunks_indexed += self.chunk_sink.bulk_upsert(chunk_batch, refresh=False)
                        chunk_batch.clear()
                        print(f"\n  → Flush chunks: {chunks_indexed} chunks indexados")

                doc_chunks = chunks_seen - doc_chunks_before

            except Exception as e:
                error_msg = f"Error processing {acquired.doc_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                self._log_bad_doc(acquired, str(e))

            if seen % _LOG_EVERY == 0 or seen == total_docs:
                _print_progress(seen, total_docs, chunks_seen, t0)

        # Flush remaining
        if doc_batch:
            docs_indexed += self._flush_docs(doc_batch)
        if chunk_batch:
            chunks_indexed += self.chunk_sink.bulk_upsert(chunk_batch, refresh=False)

        elapsed = time.time() - t0
        print(f"\n\n  Fases 2+3 completadas en {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"  docs vistos={seen}  skipped={skipped}  indexados={docs_indexed}  errores={len(errors)}")
        print(f"  chunks generados={chunks_seen}  chunks indexados={chunks_indexed}")

        self.doc_sink.set_refresh_interval("1s")
        self.chunk_sink.set_refresh_interval("1s")

        # Always refresh at the end so the embedding phase sees chunks immediately
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
