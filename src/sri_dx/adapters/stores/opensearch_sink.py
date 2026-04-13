# src/sri_dx/adapters/stores/opensearch_sink.py
from __future__ import annotations
import logging

from dataclasses import dataclass
from typing import Iterable, Optional

from opensearchpy import OpenSearch, helpers

from sri_dx.core.schemas.indexing.index_document import IndexDocument
from sri_dx.modules.indexing.index_upsert import IndexUpsert
from sri_dx.modules.indexing.opensearch_schema import build_index_body


logger = logging.getLogger(__name__)


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
        """Asegura que el índice configurado existe y el alias apunta allí si no existe."""
        if not self.client.indices.exists(index=self.cfg.index_name):
            self.create_index(self.cfg.index_name)

        # Alias estable -> index versionado
        if not self.get_alias_targets(self.cfg.alias_name):
            self.set_alias(self.cfg.alias_name, self.cfg.index_name)

    def create_index(self, index_name: str) -> None:
        """Crea un índice con el mapping predefinido."""
        body = build_index_body(shards=self.cfg.shards, replicas=self.cfg.replicas)
        self.client.indices.create(index=index_name, body=body)

    def set_alias(self, alias_name: str, index_name: str, remove_others: bool = True) -> None:
        """Apunta el alias al índice indicado."""
        actions = []
        if remove_others:
            current_targets = self.get_alias_targets(alias_name)
            for old_index in current_targets:
                if old_index != index_name:
                    actions.append({"remove": {"index": old_index, "alias": alias_name}})
        
        actions.append({"add": {"index": index_name, "alias": alias_name}})
        self.client.indices.update_aliases(body={"actions": actions})

    def get_alias_targets(self, alias_name: str) -> list[str]:
        """Devuelve la lista de índices a los que apunta un alias."""
        try:
            res = self.client.indices.get_alias(name=alias_name)
            return list(res.keys())
        except Exception:
            return []

    def set_refresh_interval(self, interval: str) -> None:
        """Cambia el refresh_interval del índice. Usar '-1' durante bulk masivo."""
        self.client.indices.put_settings(
            index=self.cfg.index_name,
            body={"index": {"refresh_interval": interval}},
        )

    def bulk_upsert(self, docs: Iterable[IndexDocument | IndexUpsert], *, refresh: bool = False) -> list[str]:
        """
        Inserta/actualiza docs usando _id = doc_id.
        Devuelve lista de _id de documentos indexados exitosamente.
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

        ok_ids: list[str] = []
        for ok, item in helpers.streaming_bulk(self.client, actions(), chunk_size=500, max_retries=3, raise_on_error=False):
            # item tiene forma {"index": {"_id": "...", "status": 201/200, ...}}
            action = next(iter(item.values()))
            _id = action.get("_id")
            if ok and _id:
                ok_ids.append(_id)

        if refresh:
            self.client.indices.refresh(index=self.cfg.index_name)
        return ok_ids
