# src/sri_dx/app/cli/orchestrator.py
"""Indexing pipeline orchestrator for SRI-DX.

Runs all phases in-process to share loaded models and avoid redundant reloads.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Orchestrator")

logging.getLogger("opensearch").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def run_acquisition() -> bool:
    """Phase 1: Acquisition (runs the scraper as a subprocess)."""
    try:
        subprocess.run(["uv", "run", "python", "src/sri_dx/scripts/run_acquisition.py"], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Acquisition phase failed: %s", e)
        return False


def run_index_docs_and_chunks(host: str, port: int, use_semantic_chunker: bool = True) -> bool:
    """Phases 2+3: indexes docs and chunks in a single JSONL pass."""
    from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
    from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink, OpenSearchConfig
    from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink, OpenSearchChunksConfig
    from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
    from sri_dx.usecases.indexing.index_combined import IndexCombinedUseCase
    from sri_dx.modules.indexing.chunking import ChunkingConfig

    paths = [p for p in [Path("data/processed/docs_html.jsonl"), Path("data/processed/docs_pdf.jsonl")] if p.exists()]
    if not paths:
        logger.error("No JSONL files found in data/processed/")
        return False

    source = JsonlDocumentSource(paths=paths)
    doc_sink = OpenSearchIndexSink(OpenSearchConfig(host=host, port=port))
    chunk_sink = OpenSearchChunksSink(OpenSearchChunksConfig(host=host, port=port))
    manifest = SqliteManifestStore(Path("data/index/manifest.sqlite"))
    chunk_cfg = ChunkingConfig(use_semantic_chunker=use_semantic_chunker)
    uc = IndexCombinedUseCase(
        source=source, doc_sink=doc_sink, chunk_sink=chunk_sink,
        manifest=manifest, chunk_cfg=chunk_cfg,
    )
    stats = uc.run(refresh=False)
    return stats.get("errors_count", 0) == 0


def run_embeddings(host: str, port: int, batch_size: int, device: str) -> bool:
    """Phase 4: Generates embeddings in-process, reusing any already-loaded BERT model."""
    from sri_dx.usecases.indexing.embed_chunks import EmbedChunksUseCase, EmbedChunksConfig

    config = EmbedChunksConfig(
        chunks_host=host, chunks_port=port,
        embeddings_host=host, embeddings_port=port,
        batch_size=batch_size,
        device=device,
    )
    uc = EmbedChunksUseCase(config)
    result = uc.run()
    logger.info(
        "Phase 4 complete: %d embeddings generated, %d stored, %.1fs",
        result.embeddings_generated, result.embeddings_stored, result.processing_time_seconds,
    )
    return result.errors == []


def main() -> None:
    parser = argparse.ArgumentParser(description="SRI-DX indexing pipeline (in-process).")
    parser.add_argument("--skip-acquisition", action="store_true", help="Skip Phase 1 (scraping)")
    parser.add_argument("--skip-indexing", action="store_true", help="Skip Phases 2+3 (docs+chunks)")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip Phase 4 (embeddings)")
    parser.add_argument(
        "--only-indexing", action="store_true",
        help="Run only Phases 2+3. Equivalent to --skip-acquisition --skip-embeddings"
    )
    parser.add_argument("--host", default="localhost", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument(
        "--no-semantic-chunker", action="store_true",
        help="Disable SemanticChunker in Phase 3: use sliding-window chunking (faster, less precise)"
    )
    parser.add_argument(
        "--embedding-device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Device for Phase 4 embeddings. Use 'cpu' if GPU VRAM is insufficient.",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=64,
        help="Batch size for Phase 4 embeddings. Reduce to 16/32 if CUDA OOM occurs.",
    )
    args = parser.parse_args()
    
    if args.only_indexing:
        args.skip_acquisition = True
        args.skip_embeddings = True

    use_semantic = not args.no_semantic_chunker
    pipeline_start = time.time()

    steps = [
        ("Phase 1: Acquisition", lambda: run_acquisition(), args.skip_acquisition),
        ("Phases 2+3: Indexing Docs+Chunks", lambda: run_index_docs_and_chunks(args.host, args.port, use_semantic), args.skip_indexing),
        ("Phase 4: Embeddings", lambda: run_embeddings(args.host, args.port, args.embedding_batch_size, args.embedding_device), args.skip_embeddings),
    ]

    for desc, run_fn, skip in steps:
        if skip:
            print(f"\n[SKIP] {desc}")
            continue
        print(f"\n{'='*60}")
        print(f"  STARTING: {desc}")
        print(f"{'='*60}")
        t0 = time.time()
        if not run_fn():
            print(f"\n[ERROR] Failed: {desc}")
            sys.exit(1)
        elapsed = time.time() - t0
        print(f"\n  DONE: {desc}  ({elapsed:.1f}s / {elapsed/60:.1f} min)")

    total = time.time() - pipeline_start
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE: {total:.1f}s ({total/60:.1f} min)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
