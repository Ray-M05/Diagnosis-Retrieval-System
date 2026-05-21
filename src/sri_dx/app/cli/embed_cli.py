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
    """Configures logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def progress_bar(current: int, total: int) -> None:
    """Displays a simple progress bar."""
    pct = (current / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "=" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r[{bar}] {pct:.1f}% ({current}/{total})")
    sys.stdout.flush()
    if current >= total:
        print()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generates embeddings for chunks stored in OpenSearch."
    )

    # Connection
    parser.add_argument(
        "--host",
        default="localhost",
        help="OpenSearch host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9200,
        help="OpenSearch port (default: 9200)"
    )

    # Indices
    parser.add_argument(
        "--chunks-index",
        default="clinical_chunks_v1",
        help="Chunks index name (default: clinical_chunks_v1)"
    )
    parser.add_argument(
        "--embeddings-index",
        default="clinical_embeddings_v1",
        help="Embeddings index name (default: clinical_embeddings_v1)"
    )

    # Processing
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Batch size for embedding (default: 128)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-generates embeddings even if they already exist"
    )

    # Filters
    parser.add_argument(
        "--seed-group",
        help="Filter by seed_group"
    )
    parser.add_argument(
        "--source-domain",
        help="Filter by source_domain"
    )

    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Inference device (default: auto)"
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate only, do not store embeddings"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar"
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    # Configure use case
    config = EmbedChunksConfig(
        chunks_host=args.host,
        chunks_port=args.port,
        chunks_index=args.chunks_index,
        embeddings_host=args.host,
        embeddings_port=args.port,
        embeddings_index=args.embeddings_index,
        batch_size=args.batch_size,
        device=args.device,
        skip_existing=not args.no_skip_existing,
        seed_group=args.seed_group,
        source_domain=args.source_domain,
    )
    
    logger.info("Starting embedding generation...")
    logger.info(f"  Chunks: {args.host}:{args.port}/{args.chunks_index}")
    logger.info(f"  Embeddings: {args.host}:{args.port}/{args.embeddings_index}")

    if args.dry_run:
        logger.info("  DRY-RUN MODE: No embeddings will be stored")

    # Run
    usecase = EmbedChunksUseCase(config)
    
    progress_cb = progress_bar if not args.no_progress else None
    result = usecase.run(dry_run=args.dry_run, progress_callback=progress_cb)
    
    # Results
    print("\n--- Results ---")
    print(f"Total chunks:       {result.total_chunks}")
    print(f"Embeddings gen.:    {result.embeddings_generated}")
    print(f"Embeddings stored:  {result.embeddings_stored}")
    print(f"Skipped (exist.):   {result.skipped_already_embedded}")
    print(f"Errors:             {len(result.errors)}")
    print(f"Time:               {result.processing_time_seconds:.2f}s")

    if result.errors:
        print("\nErrors:")
        for err in result.errors[:5]:
            print(f"  - {err}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
