# src/sri_dx/usecases/index_opensearch.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sri_dx.core.ports.document_source import DocumentSourcePort
from sri_dx.core.ports.manifest_store import ManifestStorePort, ManifestEntry
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.modules.indexing.prepare import prepare_index_document
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
from sri_dx.modules.indexing.index_upsert import IndexUpsert
from sri_dx.modules.indexing.pipeline_version import PIPELINE_VERSION


@dataclass
class IndexOpenSearchUseCase:
    source: DocumentSourcePort
    sink: OpenSearchIndexSink
    manifest: ManifestStorePort
    batch_size: int = 500

    def run(self, *, refresh: bool = False) -> dict:
        self.sink.ensure_index()
        
        extractor = ConceptExtractor()

        seen = 0
        skipped = 0
        sent = 0
        indexed_ok = 0

        batch = []
        batch_ids = []

        for acquired in self.source.iter_documents():
            seen += 1
            idx_doc = prepare_index_document(acquired)

            prev = self.manifest.get(idx_doc.doc_id)
            if prev and prev.content_hash == idx_doc.content_hash and prev.pipeline_version == PIPELINE_VERSION:
                skipped += 1
                continue

            text_all = " ".join([idx_doc.title, idx_doc.sections_text, idx_doc.body])
            concept_ids = extractor.extract(text_all, language=idx_doc.language or "es")
            
            upsert = IndexUpsert(doc=idx_doc, concept_ids=concept_ids)
            batch.append(upsert)
            batch_ids.append(idx_doc.doc_id)
            sent += 1

            if len(batch) >= self.batch_size:
                ok_ids = self.sink.bulk_upsert(batch, refresh=False)
                indexed_ok += len(ok_ids)
                
                # Update manifest
                content_hashes = {x.doc.doc_id: x.doc.content_hash for x in batch}
                self.manifest.upsert_many(
                    ManifestEntry(doc_id=_id, content_hash=content_hashes[_id], pipeline_version=PIPELINE_VERSION)
                    for _id in ok_ids
                )
                
                batch.clear()
                batch_ids.clear()

        if batch:
            ok_ids = self.sink.bulk_upsert(batch, refresh=False)
            indexed_ok += len(ok_ids)
            
            # Update manifest
            content_hashes = {x.doc.doc_id: x.doc.content_hash for x in batch}
            self.manifest.upsert_many(
                ManifestEntry(doc_id=_id, content_hash=content_hashes[_id], pipeline_version=PIPELINE_VERSION)
                for _id in ok_ids
            )

        if refresh:
            # refresca al final para que la búsqueda lo vea ya
            self.sink.client.indices.refresh(index=self.sink.cfg.index_name)

        return {
            "docs_seen": seen,
            "docs_skipped_same_hash": skipped,
            "docs_sent_to_index": sent,
            "docs_indexed_ok": indexed_ok,
            "pipeline_version": PIPELINE_VERSION,
        }
