# src/sri_dx/usecases/index_opensearch.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sri_dx.core.ports.document_source import DocumentSourcePort
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.modules.indexing.prepare import prepare_index_document


@dataclass
class IndexOpenSearchUseCase:
    source: DocumentSourcePort
    sink: OpenSearchIndexSink
    batch_size: int = 500

    def run(self, *, refresh: bool = False) -> dict:
        self.sink.ensure_index()

        total_docs = 0
        total_indexed = 0

        batch = []
        for acquired in self.source.iter_documents():
            idx_doc = prepare_index_document(acquired)
            batch.append(idx_doc)
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
