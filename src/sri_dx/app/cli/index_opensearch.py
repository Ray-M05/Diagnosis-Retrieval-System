# src/sri_dx/app/index_opensearch.py
from __future__ import annotations

import argparse
from pathlib import Path

from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink, OpenSearchConfig
from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore
from sri_dx.usecases.indexing.index_opensearch import IndexOpenSearchUseCase


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="data/processed/docs_html.jsonl")
    ap.add_argument("--pdf", default="data/processed/docs_pdf.jsonl")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9200)
    ap.add_argument("--index", default="clinical_docs_v1")
    ap.add_argument("--alias", default="clinical_docs")
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--manifest", default="data/index/manifest.sqlite")
    args = ap.parse_args()

    source = JsonlDocumentSource(paths=[Path(args.html), Path(args.pdf)])
    sink = OpenSearchIndexSink(OpenSearchConfig(
        host=args.host,
        port=args.port,
        index_name=args.index,
        alias_name=args.alias,
    ))
    manifest = SqliteManifestStore(Path(args.manifest))

    uc = IndexOpenSearchUseCase(source=source, sink=sink, manifest=manifest, batch_size=args.batch_size)
    stats = uc.run(refresh=args.refresh)
    print("=== INDEX OPENSEARCH (FASE C/E) ===")
    print(stats)


if __name__ == "__main__":
    main()
