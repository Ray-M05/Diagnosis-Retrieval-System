from __future__ import annotations
import argparse
import logging
from pathlib import Path

from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksConfig, OpenSearchChunksSink
from sri_dx.modules.indexing.chunking import ChunkingConfig
from sri_dx.usecases.index_chunks_opensearch import IndexChunksOpenSearchUseCase

# Configuración de logging básica
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main() -> None:
    ap = argparse.ArgumentParser(description="CLI para indexar fragmentos (chunks) en OpenSearch.")
    ap.add_argument("--html", default="data/processed/docs_html.jsonl", help="Ruta al JSONL de documentos HTML.")
    ap.add_argument("--pdf", default="data/processed/docs_pdf.jsonl", help="Ruta al JSONL de documentos PDF.")
    ap.add_argument("--host", default="localhost", help="Host de OpenSearch.")
    ap.add_argument("--port", type=int, default=9200, help="Puerto de OpenSearch.")
    ap.add_argument("--index", default="clinical_chunks_v1", help="Nombre del índice de OpenSearch.")
    ap.add_argument("--alias", default="clinical_chunks", help="Alias para el índice.")
    ap.add_argument("--dim", type=int, default=768, help="Dimensión del vector (kNN).")
    ap.add_argument("--batch-size", type=int, default=500, help="Tamaño del bloque de indexación.")
    ap.add_argument("--max-chars", type=int, default=1200, help="Máximo de caracteres por chunk.")
    ap.add_argument("--overlap", type=int, default=200, help="Caracteres de solapamiento.")
    ap.add_argument("--min-chars", type=int, default=100, help="Mínimo de caracteres por chunk.")
    ap.add_argument("--no-concepts", action="store_true", help="Deshabilitar extracción de conceptos.")
    ap.add_argument("--refresh", action="store_true", help="Forzar refresh del índice tras indexar.")
    args = ap.parse_args()

    # Configurar fuente de documentos
    jsonl_paths = []
    if Path(args.html).exists():
        jsonl_paths.append(Path(args.html))
    if Path(args.pdf).exists():
        jsonl_paths.append(Path(args.pdf))
    
    if not jsonl_paths:
        logger.error(f"No se encontraron archivos en {args.html} ni {args.pdf}")
        return

    source = JsonlDocumentSource(paths=jsonl_paths)

    # Configurar sink de OpenSearch
    sink_cfg = OpenSearchChunksConfig(
        host=args.host,
        port=args.port,
        index_name=args.index,
        alias_name=args.alias,
        vector_dim=args.dim,
    )
    sink = OpenSearchChunksSink(sink_cfg)

    # Configurar caso de uso
    chunk_cfg = ChunkingConfig(
        max_chars=args.max_chars,
        overlap_chars=args.overlap,
        min_chars=args.min_chars,
    )
    
    uc = IndexChunksOpenSearchUseCase(
        source=source,
        sink=sink,
        chunk_cfg=chunk_cfg,
        batch_size=args.batch_size,
    )

    logger.info("Iniciando indexación de chunks...")
    stats = uc.run(refresh=args.refresh, with_concepts=not args.no_concepts)
    
    print("\n" + "="*20)
    print("ESTADÍSTICAS DE INDEXACIÓN (CHUNKS)")
    print("="*20)
    print(f"Documentos procesados: {stats['docs_seen']}")
    print(f"Fragmentos generados:   {stats['chunks_seen']}")
    print(f"Operaciones de indexación exitosas: {stats['chunks_indexed_ops']}")
    print("="*20 + "\n")

if __name__ == "__main__":
    main()
破
