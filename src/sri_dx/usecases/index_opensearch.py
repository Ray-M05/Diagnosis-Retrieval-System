import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Any

from sri_dx.core.ports.document_source import DocumentSourcePort
from sri_dx.core.ports.manifest_store import ManifestStorePort, ManifestEntry
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.modules.indexing.prepare import prepare_index_document
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
from sri_dx.modules.indexing.index_upsert import IndexUpsert
from sri_dx.modules.indexing.pipeline_version import PIPELINE_VERSION

logger = logging.getLogger(__name__)


@dataclass
class IndexOpenSearchUseCase:
    source: DocumentSourcePort
    sink: OpenSearchIndexSink
    manifest: ManifestStorePort
    batch_size: int = 500
    report_dir: Path = Path("data/index/reports")
    bad_docs_path: Path = Path("data/index/bad_docs.jsonl")

    def run(self, *, refresh: bool = False) -> dict[str, Any]:
        self.sink.ensure_index()
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        extractor = ConceptExtractor()

        seen = 0
        skipped = 0
        sent = 0
        indexed_ok = 0
        errors = []

        batch = []
        
        # Stats by mime/domain
        stats_mime: dict[str, int] = {}
        stats_domain: dict[str, int] = {}

        for acquired in self.source.iter_documents():
            seen += 1
            try:
                idx_doc = prepare_index_document(acquired)
                
                # Update stats
                stats_mime[idx_doc.mime_type] = stats_mime.get(idx_doc.mime_type, 0) + 1
                stats_domain[idx_doc.source_domain] = stats_domain.get(idx_doc.source_domain, 0) + 1

                prev = self.manifest.get(idx_doc.doc_id)
                if prev and prev.content_hash == idx_doc.content_hash and prev.pipeline_version == PIPELINE_VERSION:
                    skipped += 1
                    continue

                text_all = " ".join([idx_doc.title, idx_doc.sections_text, idx_doc.body])
                concept_ids = extractor.extract(text_all, language=idx_doc.language or "es")
                
                upsert = IndexUpsert(doc=idx_doc, concept_ids=concept_ids)
                batch.append(upsert)
                sent += 1

                if len(batch) >= self.batch_size:
                    indexed_ok += self._flush_batch(batch, refresh=False)
                    batch.clear()

            except Exception as e:
                error_msg = f"Error processing {acquired.doc_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                self._log_bad_doc(acquired, str(e))

        if batch:
            indexed_ok += self._flush_batch(batch, refresh=False)

        if refresh:
            self.sink.client.indices.refresh(index=self.sink.cfg.index_name)

        report = {
            "timestamp": datetime.now().isoformat(),
            "docs_seen": seen,
            "docs_skipped_same_hash": skipped,
            "docs_sent_to_index": sent,
            "docs_indexed_ok": indexed_ok,
            "pipeline_version": PIPELINE_VERSION,
            "errors_count": len(errors),
            "errors_sample": errors[:10],
            "stats": {
                "by_mime": stats_mime,
                "by_domain": stats_domain,
            }
        }
        
        self._save_report(report)
        return report

    def _flush_batch(self, batch: list[IndexUpsert], refresh: bool) -> int:
        ok_ids = self.sink.bulk_upsert(batch, refresh=refresh)
        
        # Update manifest
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
        report_path = self.report_dir / f"index_run_{ts}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
