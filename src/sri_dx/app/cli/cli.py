from __future__ import annotations
import argparse
import sys
from pathlib import Path

from sri_dx.core.config import load_config
from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
from sri_dx.adapters.stores.opensearch_sink import OpenSearchConfig, OpenSearchIndexSink
from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
from sri_dx.usecases.indexing.index_opensearch import IndexOpenSearchUseCase

def cmd_index_run(args):
    cfg = load_config(args.config)
    
    html_path = Path(args.html or cfg.indexing.html_source)
    pdf_path = Path(args.pdf or cfg.indexing.pdf_source)
    
    source = JsonlDocumentSource(paths=[html_path, pdf_path])
    sink = OpenSearchIndexSink(OpenSearchConfig(
        host=args.host or cfg.opensearch.host,
        port=args.port or cfg.opensearch.port,
        index_name=args.index or cfg.opensearch.index_name,
        alias_name=args.alias or cfg.opensearch.alias_name,
    ))
    manifest = SqliteManifestStore(Path(args.manifest or cfg.indexing.manifest_path))
    
    uc = IndexOpenSearchUseCase(
        source=source, 
        sink=sink, 
        manifest=manifest, 
        batch_size=args.batch_size or cfg.indexing.batch_size,
        report_dir=Path(cfg.indexing.report_dir),
        bad_docs_path=Path(cfg.indexing.bad_docs_path)
    )
    
    print(f"[*] Iniciando indexación incremental...")
    print(f"[*] Índice: {sink.cfg.index_name} (Alias: {sink.cfg.alias_name})")
    stats = uc.run(refresh=args.refresh)
    
    print("\n=== RESUMEN DE INDEXACIÓN ===")
    print(f"Docs vistos: {stats['docs_seen']}")
    print(f"Docs saltados (mismo hash): {stats['docs_skipped_same_hash']}")
    print(f"Docs enviados a indexar: {stats['docs_sent_to_index']}")
    print(f"Docs indexados OK: {stats['docs_indexed_ok']}")
    print(f"Errores: {stats['errors_count']}")
    if 'timestamp' in stats:
        print(f"Reporte guardado en: {cfg.indexing.report_dir}")

def cmd_index_create(args):
    cfg = load_config(args.config)
    sink = OpenSearchIndexSink(OpenSearchConfig(
        host=args.host or cfg.opensearch.host,
        port=args.port or cfg.opensearch.port,
    ))
    index_name = args.name
    print(f"[*] Creando índice: {index_name}...")
    sink.create_index(index_name)
    print("[+] Índice creado satisfactoriamente.")

def cmd_index_alias(args):
    cfg = load_config(args.config)
    sink = OpenSearchIndexSink(OpenSearchConfig(
        host=args.host or cfg.opensearch.host,
        port=args.port or cfg.opensearch.port,
    ))
    alias_name = args.alias or cfg.opensearch.alias_name
    index_name = args.to
    print(f"[*] Apuntando alias '{alias_name}' a '{index_name}'...")
    sink.set_alias(alias_name, index_name)
    print("[+] Alias actualizado.")

def main():
    parser = argparse.ArgumentParser(prog="sri-dx", description="SRI Diagnosis Retrieval System CLI")
    parser.add_argument("--config", "-c", type=Path, help="Ruta al archivo config.toml")
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Subcomando 'index'
    index_parser = subparsers.add_parser("index", help="Gestión del índice")
    index_sub = index_parser.add_subparsers(dest="subcommand", help="Acciones de indexación")
    
    # index run
    run_parser = index_sub.add_parser("run", help="Ejecutar proceso de indexación")
    run_parser.add_argument("--html", help="Sobreescribir ruta JSONL HTML")
    run_parser.add_argument("--pdf", help="Sobreescribir ruta JSONL PDF")
    run_parser.add_argument("--host", help="Host OpenSearch")
    run_parser.add_argument("--port", type=int, help="Port OpenSearch")
    run_parser.add_argument("--index", help="Nombre del índice")
    run_parser.add_argument("--alias", help="Nombre del alias")
    run_parser.add_argument("--batch-size", type=int, help="Tamaño de lote")
    run_parser.add_argument("--manifest", help="Ruta al manifest SQLite")
    run_parser.add_argument("--refresh", action="store_true", help="Refrescar índice al final")
    
    # index create
    create_parser = index_sub.add_parser("create", help="Crear un nuevo índice")
    create_parser.add_argument("--name", required=True, help="Nombre del nuevo índice (ej: clinical_docs_v2)")
    create_parser.add_argument("--host", help="Host OpenSearch")
    create_parser.add_argument("--port", type=int, help="Port OpenSearch")
    
    # index alias
    alias_parser = index_sub.add_parser("alias", help="Gestionar alias")
    alias_parser.add_argument("--to", required=True, help="Nombre del índice al que apuntar")
    alias_parser.add_argument("--alias", help="Nombre del alias (default de config)")
    alias_parser.add_argument("--host", help="Host OpenSearch")
    alias_parser.add_argument("--port", type=int, help="Port OpenSearch")

    args = parser.parse_args()
    
    if args.command == "index":
        if args.subcommand == "run":
            cmd_index_run(args)
        elif args.subcommand == "create":
            cmd_index_create(args)
        elif args.subcommand == "alias":
            cmd_index_alias(args)
        else:
            index_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
