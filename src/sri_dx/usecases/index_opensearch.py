# src/sri_dx/usecases/index_opensearch.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sri_dx.core.ports.document_source import DocumentSourcePort
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.modules.indexing.prepare import prepare_index_document
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
from sri_dx.modules.indexing.index_upsert import IndexUpsert


@dataclass
class IndexOpenSearchUseCase:
    source: DocumentSourcePort
    sink: OpenSearchIndexSink
    batch_size: int = 500

    def run(self, *, refresh: bool = False) -> dict:
        self.sink.ensure_index()
        
        extractor = ConceptExtractor()

        total_docs = 0
        total_indexed = 0

        batch = []
        for acquired in self.source.iter_documents():
            idx_doc = prepare_index_document(acquired)
            text_all = " ".join([idx_doc.title, idx_doc.sections_text, idx_doc.body])
            concept_ids = extractor.extract(text_all, language=idx_doc.language or "es")
            
            upsert = IndexUpsert(doc=idx_doc, concept_ids=concept_ids)
            batch.append(upsert)
            total_docs += 1

            if len(batch) >= self.batch_size:
                total_indexed += self.sink.bulk_upsert(batch, refresh=False)
                batch.clear()

        if batch:
            total_indexed += self.sink.bulk_upsert(batch, refresh=False)

        if refresh:
            # refresca al final para que la búsqueda lo vea ya
            self.sink.client.indices.refresh(index=self.sink.cfg.index_name)

        return {"docs_seen": total_docs, "docs_indexed_ops": total_indexed}
