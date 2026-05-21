from __future__ import annotations
from typing import Iterable, List

from .schemas.opensearch_chunks_config import OpenSearchChunksConfig

from opensearchpy import OpenSearch, helpers

from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument
from sri_dx.modules.indexing.opensearch_chunks_schema import build_chunks_index_body

def _drop_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}

# OpenSearchChunksConfig is provided by adapters.stores.schemas.opensearch_chunks_config

class OpenSearchChunksSink:
    """
    Sink for indexing chunks in OpenSearch.
    - Handles index creation with kNN support.
    - Performs bulk insertions.
    """

    def __init__(self, cfg: OpenSearchChunksConfig) -> None:
        self.cfg = cfg
        self.client = OpenSearch(
            hosts=[{"host": cfg.host, "port": cfg.port}],
            use_ssl=cfg.use_ssl,
            verify_certs=cfg.verify_certs,
            http_compress=True,
            timeout=cfg.request_timeout,
        )

    def ensure_index(self) -> None:
        """Ensures the chunks index exists and the alias points to it."""
        if not self.client.indices.exists(index=self.cfg.index_name):
            body = build_chunks_index_body(
                vector_dim=self.cfg.vector_dim,
                shards=self.cfg.shards,
                replicas=self.cfg.replicas,
            )
            self.client.indices.create(index=self.cfg.index_name, body=body)

        # Verify alias
        try:
            aliases = self.client.indices.get_alias(index=self.cfg.index_name)
            if self.cfg.alias_name not in aliases.get(self.cfg.index_name, {}).get("aliases", {}):
                self.client.indices.put_alias(index=self.cfg.index_name, name=self.cfg.alias_name)
        except Exception:
            # If the index is new or has no alias, create one
            self.client.indices.put_alias(index=self.cfg.index_name, name=self.cfg.alias_name)

    def set_refresh_interval(self, interval: str) -> None:
        """Changes the index refresh_interval. Use '-1' during bulk indexing."""
        self.client.indices.put_settings(
            index=self.cfg.index_name,
            body={"index": {"refresh_interval": interval}},
        )

    def bulk_upsert(self, chunks: Iterable[ChunkDocument], *, refresh: bool = False) -> int:
        """
        Indexes a list of chunks in bulk.
        Returns the number of successfully indexed documents.
        """
        def actions():
            for c in chunks:
                src = _drop_none({
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "url": c.url,
                    "source_domain": c.source_domain,
                    "fetched_at": c.fetched_at,
                    "mime_type": c.mime_type,
                    "seed_group": c.seed_group,
                    "seed_id": c.seed_id,
                    "depth": c.depth,
                    "section_heading": c.section_heading,
                    "section_index": c.section_index,
                    "chunk_index": c.chunk_index,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "chunk_text": c.chunk_text,
                    "language": c.language,
                    "content_hash": c.content_hash,
                    "chunk_hash": c.chunk_hash,
                    "concept_ids": c.concept_ids or [],
                    "ner_entities": [
                        {
                            "text": e.text,
                            "label": e.label,
                            "start_char": e.start_char,
                            "end_char": e.end_char,
                            "score": e.score,
                        }
                        for e in (c.ner_entities or [])
                    ] or None,
                    "embedding": c.embedding,
                })
                yield {
                    "_op_type": "index",
                    "_index": self.cfg.index_name,
                    "_id": c.chunk_id,
                    "_source": src,
                }

        success_count = 0
        for ok, action in helpers.streaming_bulk(self.client, actions(), chunk_size=500, max_retries=3, raise_on_error=False):
            if ok:
                success_count += 1

        if refresh:
            self.client.indices.refresh(index=self.cfg.index_name)
        
        return success_count
