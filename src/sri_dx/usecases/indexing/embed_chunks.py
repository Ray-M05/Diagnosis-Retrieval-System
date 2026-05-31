# usecases/indexing/embed_chunks.py
"""UseCase para generar y almacenar embeddings de chunks."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
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
                    device=self.config.device,
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
        
        # Ensure the embeddings index exists
        if not dry_run:
            self.embedding_sink.ensure_index()
            self.embedding_sink.set_refresh_interval("-1")
        
        # Build filters
        filters = self._build_filters()
        
        import sys

        # Obtener total de chunks
        total_chunks = self.chunk_reader.get_total_chunks(filters)
        print(f"  Total chunks a embedir: {total_chunks}")
        result.total_chunks = total_chunks

        if total_chunks == 0:
            print("  No hay chunks para procesar.")
            return result

        # If skip_existing, retrieve existing hashes
        existing_hashes: Dict[str, str] = {}
        if self.config.skip_existing:
            print("  Verificando embeddings ya existentes...")
            chunk_id_hashes = self.chunk_reader.get_chunk_ids_and_hashes(filters)
            existing_embeddings = self.embedding_sink.exists_for_chunks(
                list(chunk_id_hashes.keys()),
                chunk_id_hashes
            )
            result.skipped_already_embedded = sum(1 for v in existing_embeddings.values() if v)
            pending_count = total_chunks - result.skipped_already_embedded
            print(f"  Ya embebidos: {result.skipped_already_embedded}  Pendientes: {pending_count}")

        # Process in batches with I/O-compute overlap
        processed = 0
        t0_embed = start_time

        def _print_embed_progress(done: int, total: int) -> None:
            elapsed = time.time() - t0_embed
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            pct = done / total * 100 if total > 0 else 0
            bar_len = 30
            filled = int(bar_len * done / total) if total > 0 else 0
            bar = "#" * filled + "-" * (bar_len - filled)
            line = (
                f"\r  [{bar}] {pct:5.1f}%  {done}/{total} chunks"
                f"  {rate:.0f} ch/s"
                f"  ETA {eta/60:.1f}min"
            )
            # A non-UTF-8 console (e.g. Windows cp1252) must never crash the embed
            # run over a cosmetic progress bar — this use case also runs inside the
            # web-search request path, where a crash here would leave web chunks
            # without vectors.
            try:
                sys.stdout.write(line)
                sys.stdout.flush()
            except (UnicodeEncodeError, OSError):
                pass

        with ThreadPoolExecutor(max_workers=2) as pool:
            pending_store: Optional[Future] = None

            for batch in self.chunk_reader.iter_chunks_batched(
                batch_size=self.config.batch_size,
                filters=filters
            ):
                # Filter out chunks that already have an embedding (if skip_existing)
                if self.config.skip_existing:
                    batch = [
                        chunk for chunk in batch
                        if not existing_embeddings.get(chunk.chunk_id, False)
                    ]

                if not batch:
                    continue

                try:
                    # Generate embeddings (compute)
                    embeddings = self.embedding_generator.generate_embeddings(batch)
                    result.embeddings_generated += len(embeddings)

                    # Wait for previous store if pending
                    if pending_store is not None:
                        result.embeddings_stored += pending_store.result()
                        pending_store = None

                    # Launch store in parallel (I/O) while the next batch is generated
                    if not dry_run and embeddings:
                        pending_store = pool.submit(self.embedding_sink.store_embeddings, embeddings)

                except Exception as e:
                    error_msg = f"Error procesando batch: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

                processed += len(batch)

                # Progress callback and console
                if progress_callback:
                    progress_callback(processed, total_chunks)
                _print_embed_progress(processed, total_chunks)

            # Wait for the last pending store
            if pending_store is not None:
                result.embeddings_stored += pending_store.result()

        if not dry_run:
            self.embedding_sink.set_refresh_interval("1s")
            # Force an explicit refresh so the just-written vectors are immediately
            # searchable. Without this, refresh_interval="1s" leaves a ~1s window in
            # which a kNN query (e.g. the web-enrich Stage 7 re-retrieval that runs
            # right after embedding) does NOT see the new web embeddings — so web
            # chunks silently fail to appear in the results on the first run.
            try:
                self.embedding_sink.client.indices.refresh(
                    index=self.embedding_sink.cfg.index_name
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not refresh embeddings index: %s", exc)

        result.processing_time_seconds = time.time() - start_time
        elapsed = result.processing_time_seconds
        print(f"\n\n  F4 completada en {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"  generados={result.embeddings_generated}  almacenados={result.embeddings_stored}"
              f"  saltados={result.skipped_already_embedded}  errores={len(result.errors)}")
        
        return result
    
    def _build_filters(self) -> Optional[Dict[str, Any]]:
        """Construye filtros para la query."""
        filters = {}
        
        if self.config.seed_group:
            filters["seed_group"] = self.config.seed_group
        
        if self.config.source_domain:
            filters["source_domain"] = self.config.source_domain
        
        return filters if filters else None
