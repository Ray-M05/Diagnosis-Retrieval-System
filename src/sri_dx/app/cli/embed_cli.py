# app/embed_cli.py
"""CLI para generar embeddings de chunks en OpenSearch."""

from __future__ import annotations

import argparse
import logging
import sys

from sri_dx.usecases.indexing.embed_chunks import (
    EmbedChunksUseCase,
    EmbedChunksConfig,
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configura logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def progress_bar(current: int, total: int) -> None:
    """Muestra barra de progreso simple."""
    pct = (current / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "=" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r[{bar}] {pct:.1f}% ({current}/{total})")
    sys.stdout.flush()
    if current >= total:
        print()


def main() -> int:
    """Punto de entrada del CLI."""
    parser = argparse.ArgumentParser(
        description="Genera embeddings para chunks almacenados en OpenSearch."
    )
    
    # Conexión
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Host de OpenSearch (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=9200,
        help="Puerto de OpenSearch (default: 9200)"
    )
    
    # Índices
    parser.add_argument(
        "--chunks-index",
        default="clinical_chunks_v1",
        help="Nombre del índice de chunks (default: clinical_chunks_v1)"
    )
    parser.add_argument(
        "--embeddings-index",
        default="clinical_embeddings_v1",
        help="Nombre del índice de embeddings (default: clinical_embeddings_v1)"
    )
    
    # Procesamiento
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Tamaño de batch para embedding (default: 32)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-genera embeddings incluso si ya existen"
    )
    
    # Filtros
    parser.add_argument(
        "--seed-group",
        help="Filtrar por seed_group"
    )
    parser.add_argument(
        "--source-domain",
        help="Filtrar por source_domain"
    )
    
    # Opciones
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo simula, no almacena embeddings"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activa logging detallado"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Desactiva barra de progreso"
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    # Configurar UseCase
    config = EmbedChunksConfig(
        chunks_host=args.host,
        chunks_port=args.port,
        chunks_index=args.chunks_index,
        embeddings_host=args.host,
        embeddings_port=args.port,
        embeddings_index=args.embeddings_index,
        batch_size=args.batch_size,
        skip_existing=not args.no_skip_existing,
        seed_group=args.seed_group,
        source_domain=args.source_domain,
    )
    
    logger.info("Iniciando generación de embeddings...")
    logger.info(f"  Chunks: {args.host}:{args.port}/{args.chunks_index}")
    logger.info(f"  Embeddings: {args.host}:{args.port}/{args.embeddings_index}")
    
    if args.dry_run:
        logger.info("  MODO DRY-RUN: No se almacenarán embeddings")
    
    # Ejecutar
    usecase = EmbedChunksUseCase(config)
    
    progress_cb = progress_bar if not args.no_progress else None
    result = usecase.run(dry_run=args.dry_run, progress_callback=progress_cb)
    
    # Resultados
    print("\n--- Resultados ---")
    print(f"Total chunks:       {result.total_chunks}")
    print(f"Embeddings gen.:    {result.embeddings_generated}")
    print(f"Embeddings alm.:    {result.embeddings_stored}")
    print(f"Saltados (exist.):  {result.skipped_already_embedded}")
    print(f"Errores:            {len(result.errors)}")
    print(f"Tiempo:             {result.processing_time_seconds:.2f}s")
    
    if result.errors:
        print("\nErrores:")
        for err in result.errors[:5]:
            print(f"  - {err}")
        if len(result.errors) > 5:
            print(f"  ... y {len(result.errors) - 5} más")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
