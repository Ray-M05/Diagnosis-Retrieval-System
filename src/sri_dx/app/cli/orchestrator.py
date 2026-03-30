# src/sri_dx/app/cli/orchestrator.py
"""Orquestador del pipeline de indexado SRI-DX.

Ejecuta las fases in-process (mismo proceso Python) para compartir
modelos cargados en memoria y evitar recargas redundantes.
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


def run_acquisition() -> bool:
    """Fase 1: Adquisición (subprocess, es un scraper independiente)."""
    try:
        subprocess.run(["uv", "run", "python", "src/sri_dx/scripts/run_acquisition.py"], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Fallo en adquisición: %s", e)
        return False


def run_index_docs_and_chunks(host: str, port: int) -> bool:
    """Fases 2+3 combinadas: Docs + Chunks en una sola pasada del JSONL."""
    from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
    from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink, OpenSearchConfig
    from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink, OpenSearchChunksConfig
    from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
    from sri_dx.usecases.indexing.index_combined import IndexCombinedUseCase

    paths = [p for p in [Path("data/processed/docs_html.jsonl"), Path("data/processed/docs_pdf.jsonl")] if p.exists()]
    if not paths:
        logger.error("No se encontraron archivos JSONL en data/processed/")
        return False

    source = JsonlDocumentSource(paths=paths)
    doc_sink = OpenSearchIndexSink(OpenSearchConfig(host=host, port=port))
    chunk_sink = OpenSearchChunksSink(OpenSearchChunksConfig(host=host, port=port))
    manifest = SqliteManifestStore(Path("data/index/manifest.sqlite"))
    uc = IndexCombinedUseCase(source=source, doc_sink=doc_sink, chunk_sink=chunk_sink, manifest=manifest)
    stats = uc.run(refresh=False)
    logger.info("Fases 2+3 completadas: %s", stats)
    return True


def run_embeddings(host: str, port: int) -> bool:
    """Fase 4: Generación de embeddings (in-process, reutiliza modelo BERT si ya cargado)."""
    from sri_dx.usecases.indexing.embed_chunks import EmbedChunksUseCase, EmbedChunksConfig

    config = EmbedChunksConfig(
        chunks_host=host, chunks_port=port,
        embeddings_host=host, embeddings_port=port,
    )
    uc = EmbedChunksUseCase(config)
    result = uc.run()
    logger.info(
        "Fase 4 completada: %d embeddings generados, %d almacenados, %.1fs",
        result.embeddings_generated, result.embeddings_stored, result.processing_time_seconds,
    )
    return result.errors == []


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline SRI-DX (in-process).")
    parser.add_argument("--skip-acquisition", action="store_true", help="Salta la Fase 1 (Scraping)")
    parser.add_argument("--skip-indexing", action="store_true", help="Salta Fases 2+3 (Docs+Chunks OpenSearch)")
    parser.add_argument("--skip-embeddings", action="store_true", help="Salta la Fase 4 (Embeddings)")
    parser.add_argument("--host", default="localhost", help="Host de OpenSearch")
    parser.add_argument("--port", type=int, default=9200, help="Puerto de OpenSearch")
    args = parser.parse_args()

    pipeline_start = time.time()

    steps = [
        ("Fase 1: Adquisición", lambda: run_acquisition(), args.skip_acquisition),
        ("Fases 2+3: Indexación Docs+Chunks", lambda: run_index_docs_and_chunks(args.host, args.port), args.skip_indexing),
        ("Fase 4: Embeddings", lambda: run_embeddings(args.host, args.port), args.skip_embeddings),
    ]

    for desc, run_fn, skip in steps:
        if skip:
            logger.info("[*] SALTADO: %s", desc)
            continue
        logger.info("=== INICIANDO: %s ===", desc)
        t0 = time.time()
        if not run_fn():
            logger.error("Fallo en: %s", desc)
            sys.exit(1)
        logger.info("=== COMPLETO: %s (%.1fs) ===", desc, time.time() - t0)

    total = time.time() - pipeline_start
    logger.info("Pipeline completado en %.1fs (%.1f min)", total, total / 60)


if __name__ == "__main__":
    main()
