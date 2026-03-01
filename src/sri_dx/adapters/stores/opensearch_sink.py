# src/sri_dx/adapters/stores/opensearch_sink.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from opensearchpy import OpenSearch, helpers

from sri_dx.core.schemas.index_document import IndexDocument
from sri_dx.modules.indexing.index_upsert import IndexUpsert
from sri_dx.modules.indexing.opensearch_schema import build_index_body


def _drop_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


@dataclass(frozen=True)
class OpenSearchConfig:
    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    verify_certs: bool = False
    index_name: str = "clinical_docs_v1"
    alias_name: str = "clinical_docs"
    shards: int = 1
    replicas: int = 0
    request_timeout: int = 60


class OpenSearchIndexSink:
    """
    Sink de indexación para OpenSearch.
    - Crea el índice si no existe.
    - Mantiene alias estable.
    - Indexa en bulk (lo correcto para volumen).
    """

    def __init__(self, cfg: OpenSearchConfig) -> None:
        self.cfg = cfg
        self.client = OpenSearch(
            hosts=[{"host": cfg.host, "port": cfg.port}],
            use_ssl=cfg.use_ssl,
            verify_certs=cfg.verify_certs,
            http_compress=True,
            timeout=cfg.request_timeout,
        )

    def ensure_index(self) -> None:
        if not self.client.indices.exists(index=self.cfg.index_name):
            body = build_index_body(shards=self.cfg.shards, replicas=self.cfg.replicas)
            self.client.indices.create(index=self.cfg.index_name, body=body)

        # Alias estable -> index versionado
        aliases = self.client.indices.get_alias(index="*")
        alias_points_somewhere = any(
            self.cfg.alias_name in info.get("aliases", {})
            for info in aliases.values()
        )
        if not alias_points_somewhere:
            self.client.indices.put_alias(index=self.cfg.index_name, name=self.cfg.alias_name)

    def bulk_upsert(self, docs: Iterable[IndexDocument | IndexUpsert], *, refresh: bool = False) -> int:
        """
        Inserta/actualiza docs usando _id = doc_id.
        Devuelve cantidad de operaciones enviadas.
        """
        def actions():
            for d in docs:
                if hasattr(d, "doc"):
                    base = getattr(d, "doc")
                    concept_ids = getattr(d, "concept_ids", []) or []
                else:
                    base = d
                    concept_ids = []

                src = _drop_none({
                    "url": base.url,
                    "source_domain": base.source_domain,
                    "fetched_at": base.fetched_at,
                    "mime_type": base.mime_type,
                    "seed_group": base.seed_group,
                    "seed_id": base.seed_id,
                    "depth": base.depth,

                    "title": base.title,
                    "sections_text": base.sections_text,
                    "body": base.body,

                    "language": base.language,
                    "published_at": base.published_at,
                    "updated_at": base.updated_at,
                    "author": base.author,

                    "content_hash": base.content_hash,
                    "char_len": base.char_len,
                    "word_count": base.word_count,
                    "section_count": base.section_count,

                    "concept_ids": concept_ids,  # Fase D
                })

                yield {
                    "_op_type": "index",
                    "_index": self.cfg.index_name,
                    "_id": base.doc_id,
                    "_source": src,
                }

        # helpers.bulk devuelve (success_count, errors)
        success, _ = helpers.bulk(self.client, actions())
        if refresh:
            self.client.indices.refresh(index=self.cfg.index_name)
        return success
