from __future__ import annotations
from dataclasses import dataclass
import logging
from sri_dx.core.ports.acquisition.document_source import DocumentSourcePort
from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
from sri_dx.modules.indexing.chunking import chunk_acquired_document, ChunkingConfig

logger = logging.getLogger(__name__)

@dataclass
class IndexChunksOpenSearchUseCase:
    """
    Caso de uso para indexar fragmentos (chunks) en OpenSearch.
    - Obtiene documentos de la fuente.
    - Aplica la lógica de chunking.
    - Almacena en el sink de OpenSearch.
    """
    source: DocumentSourcePort
    sink: OpenSearchChunksSink
    chunk_cfg: ChunkingConfig = ChunkingConfig()
    batch_size: int = 500

    def run(self, *, refresh: bool = False, with_concepts: bool = True) -> dict:
        self.sink.ensure_index()
        self.sink.set_refresh_interval("-1")
        
        # Optional: ConceptExtractor (Module 4 / Phase D)
        extractor = None
        if with_concepts:
            try:
                from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
                extractor = ConceptExtractor()
            except ImportError:
                logger.warning("ConceptExtractor no encontrado. Procediendo sin extracción de conceptos.")

        chunker = None
        try:
            from sri_dx.modules.chunking.semantic_chunker import SemanticChunker
            chunker = SemanticChunker()
        except ImportError:
            pass

        seen_docs = 0
        seen_chunks = 0
        indexed_ops = 0

        batch = []
        for doc in self.source.iter_documents():
            seen_docs += 1
            
            # Split document into chunks
            chunks_gen = chunk_acquired_document(
                doc,
                cfg=self.chunk_cfg,
                concept_extractor=extractor,
                semantic_chunker=chunker,
            )
            
            for ch in chunks_gen:
                batch.append(ch)
                seen_chunks += 1
                
                if len(batch) >= self.batch_size:
                    indexed_ops += self.sink.bulk_upsert(batch, refresh=False)
                    batch.clear()

        # Flush remaining batch
        if batch:
            indexed_ops += self.sink.bulk_upsert(batch, refresh=False)

        self.sink.set_refresh_interval("1s")
        if refresh:
            self.sink.client.indices.refresh(index=self.sink.cfg.index_name)

        return {
            "docs_seen": seen_docs,
            "chunks_seen": seen_chunks,
            "chunks_indexed_ops": indexed_ops
        }
