# src/sri_dx/app/cli/reset_indices.py
"""Clean and (re)create the SRI-DX OpenSearch indices.

Idempotent maintenance command used to wipe the corpora before a full
re-index. It operates on the SEPARATED indices resolved from
:func:`sri_dx.core.index_names.resolve_index_names`:

- docs:   local + web
- chunks: local + web
- embeddings: a single shared vector index

For each selected index it deletes-if-exists (guarded by the mandatory
``--yes`` flag) and recreates it via the existing ``ensure_index()`` on the
matching sink, so the schemas are never duplicated here.

It also resets the SQLite manifest by default: ``IndexCombinedUseCase`` skips
documents whose ``content_hash`` is already recorded, so a stale manifest
against freshly-emptied indices would skip every document. Use
``--keep-manifest`` to override.

Usage::

    uv run python -m sri_dx.app.cli.reset_indices --yes
    uv run python -m sri_dx.app.cli.reset_indices --yes --only web
    uv run python -m sri_dx.app.cli.reset_indices --yes --only embeddings --keep-manifest
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("reset_indices")
logging.getLogger("opensearch").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def _delete_if_exists(client, index_name: str) -> None:
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        logger.info("Deleted index %s", index_name)
    else:
        logger.info("Index %s did not exist", index_name)


def _reset_docs(host: str, port: int, index_name: str, alias_name: str) -> None:
    from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink, OpenSearchConfig

    sink = OpenSearchIndexSink(OpenSearchConfig(
        host=host, port=port, index_name=index_name, alias_name=alias_name,
    ))
    _delete_if_exists(sink.client, index_name)
    sink.ensure_index()
    logger.info("Recreated docs index %s (alias %s)", index_name, alias_name)


def _reset_chunks(host: str, port: int, index_name: str, alias_name: str) -> None:
    from sri_dx.adapters.stores.opensearch_chunk_sink import OpenSearchChunksSink
    from sri_dx.adapters.stores.schemas.opensearch_chunks_config import OpenSearchChunksConfig

    sink = OpenSearchChunksSink(OpenSearchChunksConfig(
        host=host, port=port, index_name=index_name, alias_name=alias_name,
    ))
    _delete_if_exists(sink.client, index_name)
    sink.ensure_index()
    logger.info("Recreated chunks index %s (alias %s)", index_name, alias_name)


def _reset_embeddings(host: str, port: int, index_name: str, alias_name: str) -> None:
    from sri_dx.adapters.stores import OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig

    sink = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
        host=host, port=port, index_name=index_name, alias_name=alias_name,
    ))
    _delete_if_exists(sink.client, index_name)
    sink.ensure_index()
    logger.info("Recreated embeddings index %s (alias %s)", index_name, alias_name)


def _reset_manifest(manifest_path: Path) -> None:
    if manifest_path.exists():
        manifest_path.unlink()
        logger.info("Deleted manifest %s", manifest_path)
    else:
        logger.info("Manifest %s did not exist", manifest_path)


def reset(
    *,
    host: str,
    port: int,
    scope: str,
    keep_manifest: bool,
    manifest_path: Path,
) -> None:
    from sri_dx.core.index_names import resolve_index_names

    names = resolve_index_names()
    do_local = scope in ("local", "all")
    do_web = scope in ("web", "all")
    do_embeddings = scope in ("embeddings", "all")

    if do_local:
        _reset_docs(host, port, names.docs_local_index, names.docs_local_alias)
        _reset_chunks(host, port, names.chunks_local_index, names.chunks_local_alias)
    if do_web:
        _reset_docs(host, port, names.docs_web_index, names.docs_web_alias)
        _reset_chunks(host, port, names.chunks_web_index, names.chunks_web_alias)
    if do_embeddings:
        _reset_embeddings(host, port, names.embeddings_index, names.embeddings_alias)

    # The manifest tracks (doc_id, content_hash). It is corpus-agnostic, so we
    # reset it whenever any docs/chunks index was wiped unless told otherwise.
    if not keep_manifest and (do_local or do_web):
        _reset_manifest(manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and recreate SRI-DX OpenSearch indices.")
    parser.add_argument("--yes", action="store_true", required=True,
                        help="Confirm destructive deletion of the selected indices.")
    parser.add_argument("--only", choices=["local", "web", "embeddings", "all"], default="all",
                        help="Which indices to reset (default: all).")
    parser.add_argument("--keep-manifest", action="store_true",
                        help="Do NOT delete the SQLite manifest (advanced; risks skipping docs).")
    parser.add_argument("--host", default="localhost", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument("--manifest", default="data/index/manifest.sqlite",
                        help="Path to the SQLite manifest to reset.")
    args = parser.parse_args()

    if not args.yes:  # argparse enforces required, but keep an explicit guard
        logger.error("Refusing to run without --yes")
        sys.exit(2)

    reset(
        host=args.host,
        port=args.port,
        scope=args.only,
        keep_manifest=args.keep_manifest,
        manifest_path=Path(args.manifest),
    )
    logger.info("Reset complete (scope=%s).", args.only)


if __name__ == "__main__":
    main()
