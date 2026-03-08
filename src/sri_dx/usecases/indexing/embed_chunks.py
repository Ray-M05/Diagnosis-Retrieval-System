# usecases/indexing/embed_chunks.py
"""UseCase para generar y almacenar embeddings de chunks."""

from __future__ import annotations

import logging
import time
from sri_dx.usecases.indexing.schemas.embed_chunks_config import EmbedChunksConfig
from typing import List, Optional, Dict, Any

from sri_dx.core.schemas.indexing.embedding_document import EmbeddingBatchResult
from sri_dx.modules.indexing.embedding_generator import (
    EmbeddingGenerator,
    EmbeddingGeneratorConfig,
)
from sri_dx.adapters.stores.opensearch_chunk_reader import (
    OpenSearchChunkReader,
    OpenSearchChunkReaderConfig,
)
from sri_dx.adapters.stores.opensearch_embedding_sink import (
    OpenSearchEmbeddingSink,
    OpenSearchEmbeddingConfig,
)

logger = logging.getLogger(__name__)


# EmbedChunksConfig moved to usecases.indexing.schemas.embed_chunks_config


class EmbedChunksUseCase:
    """
    Orquesta el proceso de:
    1. Leer chunks de OpenSearch
    2. Generar embeddings con Bio_ClinicalBERT
    3. Almacenar embeddings en índice separado
    
    Uso:
        uc = EmbedChunksUseCase(config)
        result = uc.run()
        print(f"Embeddings generados: {result.embeddings_generated}")
    """
    
    def __init__(
        self,
        config: Optional[EmbedChunksConfig] = None,
        chunk_reader: Optional[OpenSearchChunkReader] = None,
        embedding_sink: Optional[OpenSearchEmbeddingSink] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
    ):
        """
        Inicializa el UseCase.
        
        Args:
            config: Configuración general
            chunk_reader: Lector de chunks (si None, se crea)
            embedding_sink: Sink de embeddings (si None, se crea)
            embedding_generator: Generador de embeddings (si None, se crea)
        """
        self.config = config or EmbedChunksConfig()
        self._chunk_reader = chunk_reader
        self._embedding_sink = embedding_sink
        self._embedding_generator = embedding_generator
    
    @property
    def chunk_reader(self) -> OpenSearchChunkReader:
        """Acceso lazy al lector de chunks."""
        if self._chunk_reader is None:
            self._chunk_reader = OpenSearchChunkReader(
                OpenSearchChunkReaderConfig(
                    host=self.config.chunks_host,
                    port=self.config.chunks_port,
                    index_name=self.config.chunks_index,
                )
            )
        return self._chunk_reader
    
    @property
    def embedding_sink(self) -> OpenSearchEmbeddingSink:
        """Acceso lazy al sink de embeddings."""
        if self._embedding_sink is None:
            self._embedding_sink = OpenSearchEmbeddingSink(
                OpenSearchEmbeddingConfig(
                    host=self.config.embeddings_host,
                    port=self.config.embeddings_port,
                    index_name=self.config.embeddings_index,
                    alias_name=self.config.embeddings_alias,
                )
            )
        return self._embedding_sink
    
    @property
    def embedding_generator(self) -> EmbeddingGenerator:
        """Acceso lazy al generador de embeddings."""
        if self._embedding_generator is None:
            self._embedding_generator = EmbeddingGenerator(
                EmbeddingGeneratorConfig(
                    batch_size=self.config.batch_size,
                )
            )
        return self._embedding_generator
    
    def run(
        self,
        dry_run: bool = False,
        progress_callback: Optional[callable] = None
    ) -> EmbeddingBatchResult:
        """
        Ejecuta el proceso de embedding.
        
        Args:
            dry_run: Si True, no almacena embeddings
            progress_callback: Función callback(processed, total)
            
        Returns:
            Resultado del proceso
        """
        start_time = time.time()
        result = EmbeddingBatchResult()
        
        # Asegurar que el índice de embeddings existe
        if not dry_run:
            self.embedding_sink.ensure_index()
        
        # Construir filtros
        filters = self._build_filters()
        
        # Obtener total de chunks
        total_chunks = self.chunk_reader.get_total_chunks(filters)
        logger.info(f"Total de chunks a procesar: {total_chunks}")
        result.total_chunks = total_chunks
        
        if total_chunks == 0:
            return result
        
        # Si skip_existing, obtener hashes existentes
        existing_hashes: Dict[str, str] = {}
        if self.config.skip_existing:
            logger.info("Obteniendo hashes de chunks existentes...")
            chunk_id_hashes = self.chunk_reader.get_chunk_ids_and_hashes(filters)
            existing_embeddings = self.embedding_sink.exists_for_chunks(
                list(chunk_id_hashes.keys()),
                chunk_id_hashes
            )
            # Contar cuántos ya existen
            result.skipped_already_embedded = sum(1 for v in existing_embeddings.values() if v)
        
        # Procesar en batches
        processed = 0
        for batch in self.chunk_reader.iter_chunks_batched(
            batch_size=self.config.batch_size,
            filters=filters
        ):
            # Filtrar chunks que ya tienen embedding (si skip_existing)
            if self.config.skip_existing:
                batch = [
                    chunk for chunk in batch
                    if not existing_embeddings.get(chunk.chunk_id, False)
                ]
            
            if not batch:
                continue
            
            try:
                # Generar embeddings
                embeddings = self.embedding_generator.generate_embeddings(batch)
                result.embeddings_generated += len(embeddings)
                
                # Almacenar
                if not dry_run and embeddings:
                    stored = self.embedding_sink.store_embeddings(embeddings)
                    result.embeddings_stored += stored
                
            except Exception as e:
                error_msg = f"Error procesando batch: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
            
            processed += len(batch)
            
            # Progress callback
            if progress_callback:
                progress_callback(processed, total_chunks)
            
            logger.debug(f"Procesados {processed}/{total_chunks} chunks")
        
        result.processing_time_seconds = time.time() - start_time
        
        logger.info(
            f"Proceso completado: {result.embeddings_generated} embeddings generados, "
            f"{result.embeddings_stored} almacenados, "
            f"{result.skipped_already_embedded} saltados, "
            f"{len(result.errors)} errores, "
            f"{result.processing_time_seconds:.2f}s"
        )
        
        return result
    
    def _build_filters(self) -> Optional[Dict[str, Any]]:
        """Construye filtros para la query."""
        filters = {}
        
        if self.config.seed_group:
            filters["seed_group"] = self.config.seed_group
        
        if self.config.source_domain:
            filters["source_domain"] = self.config.source_domain
        
        return filters if filters else None
