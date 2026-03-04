from __future__ import annotations

from dataclasses import dataclass

from sri_dx.core.ports.acquisition.document_source import DocumentSourcePort
from sri_dx.modules.indexing.prepare import prepare_index_document


@dataclass
class IndexCorpusPhaseAUseCase:
    source: DocumentSourcePort

    def run(self) -> dict:
        total = 0
        total_words = 0
        by_mime: dict[str, int] = {}

        for acquired in self.source.iter_documents():
            idx_doc = prepare_index_document(acquired)

            total += 1
            total_words += idx_doc.word_count
            by_mime[idx_doc.mime_type] = by_mime.get(idx_doc.mime_type, 0) + 1

        avg_words = (total_words / total) if total else 0.0
        return {
            "docs_total": total,
            "avg_words": avg_words,
            "by_mime": by_mime,
        }