# adapters/stores/opensearch_embedding_sink.py
"""Adaptador para almacenar embeddings en OpenSearch."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from .schemas.opensearch_embedding_config import OpenSearchEmbeddingConfig

from opensearchpy import OpenSearch, helpers

from sri_dx.core.ports.search.embedding_store_port import EmbeddingStorePort
from sri_dx.core.schemas.search.vector_search_schema import EmbeddingSearchResult
from sri_dx.core.schemas.indexing.embedding_document import EmbeddingDocument
from sri_dx.modules.indexing.opensearch_embeddings_schema import build_embeddings_index_body

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _drop_none(d: dict) -> dict:
    """Elimina claves con valor None."""
    return {k: v for k, v in d.items() if v is not None}


# OpenSearchEmbeddingConfig is provided by adapters.stores.schemas.opensearch_embedding_config


class OpenSearchEmbeddingSink(EmbeddingStorePort):
    """
    Implementación del EmbeddingStorePort para OpenSearch.
    
    Almacena embeddings en un índice separado con soporte kNN
    para búsqueda por similitud coseno.
    """
    
    def __init__(self, cfg: OpenSearchEmbeddingConfig) -> None:
        self.cfg = cfg
        self.client = OpenSearch(
            hosts=[{"host": cfg.host, "port": cfg.port}],
            use_ssl=cfg.use_ssl,
            verify_certs=cfg.verify_certs,
            http_compress=True,
            timeout=cfg.request_timeout,
        )
    
    def ensure_index(self) -> None:
        """Asegura que el índice de embeddings existe."""
        if not self.client.indices.exists(index=self.cfg.index_name):
            body = build_embeddings_index_body(
                vector_dim=self.cfg.vector_dim,
                shards=self.cfg.shards,
                replicas=self.cfg.replicas,
                ef_construction=self.cfg.ef_construction,
                m=self.cfg.m,
            )
            self.client.indices.create(index=self.cfg.index_name, body=body)
            logger.info(f"Índice {self.cfg.index_name} creado")
        
        # Asegurar alias
        try:
            aliases = self.client.indices.get_alias(index=self.cfg.index_name)
            if self.cfg.alias_name not in aliases.get(self.cfg.index_name, {}).get("aliases", {}):
                self.client.indices.put_alias(index=self.cfg.index_name, name=self.cfg.alias_name)
        except Exception:
            self.client.indices.put_alias(index=self.cfg.index_name, name=self.cfg.alias_name)
    
    def set_refresh_interval(self, interval: str) -> None:
        """Cambia el refresh_interval del índice. Usar '-1' durante bulk masivo."""
        self.client.indices.put_settings(
            index=self.cfg.index_name,
            body={"index": {"refresh_interval": interval}},
        )

    def store_embeddings(
        self,
        embeddings: List[EmbeddingDocument],
        refresh: bool = False
    ) -> int:
        """Almacena embeddings en bulk."""
        if not embeddings:
            return 0
        
        def actions():
            for emb in embeddings:
                source = _drop_none({
                    "embedding_id": emb.embedding_id,
                    "chunk_id": emb.chunk_id,
                    "doc_id": emb.doc_id,
                    "vector": emb.vector,
                    "model_name": emb.model_name,
                    "model_version": emb.model_version,
                    "embedding_dim": emb.embedding_dim,
                    "similarity_metric": emb.similarity_metric,
                    "chunk_text_preview": emb.chunk_text_preview,
                    "chunk_index": emb.chunk_index,
                    "section_heading": emb.section_heading,
                    "seed_group": emb.seed_group,
                    "source_domain": emb.source_domain,
                    "concept_ids": emb.concept_ids,
                    "chunk_hash": emb.chunk_hash,
                    "created_at": emb.created_at,
                })
                yield {
                    "_op_type": "index",
                    "_index": self.cfg.index_name,
                    "_id": emb.embedding_id,
                    "_source": source,
                }
        
        success_count = 0
        for ok, _ in helpers.streaming_bulk(
            self.client,
            actions(),
            chunk_size=500,
            max_retries=3,
            raise_on_error=False,
        ):
            if ok:
                success_count += 1
        
        if refresh:
            self.client.indices.refresh(index=self.cfg.index_name)
        
        return success_count
    
    def search_similar(
        self,
        query_vector: "NDArray[Any]",
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[EmbeddingSearchResult]:
        """Búsqueda kNN por similitud coseno."""
        import numpy as np
        
        # Normalizar vector para cosine similarity
        query_vec = np.array(query_vector).flatten()
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm
        
        # Construir query kNN
        knn_query = {
            "size": k,
            "query": {
                "knn": {
                    "vector": {
                        "vector": query_vec.tolist(),
                        "k": k
                    }
                }
            },
            "_source": [
                "embedding_id", "chunk_id", "doc_id", 
                "chunk_text_preview", "section_heading",
                "seed_group", "source_domain", "chunk_index",
                "concept_ids"
            ]
        }
        
        # Agregar filtros si los hay
        if filters:
            filter_clauses = []
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {field: value}})
                else:
                    filter_clauses.append({"term": {field: value}})
            
            knn_query["query"] = {
                "bool": {
                    "must": [knn_query["query"]],
                    "filter": filter_clauses
                }
            }
        
        response = self.client.search(index=self.cfg.index_name, body=knn_query)
        
        results = []
        for hit in response.get("hits", {}).get("hits", []):
            score = hit.get("_score", 0.0)
            if score >= min_score:
                source = hit["_source"]
                results.append(EmbeddingSearchResult(
                    embedding_id=source.get("embedding_id", ""),
                    chunk_id=source.get("chunk_id", ""),
                    doc_id=source.get("doc_id", ""),
                    score=score,
                    chunk_text_preview=source.get("chunk_text_preview"),
                    section_heading=source.get("section_heading"),
                    metadata={
                        "seed_group": source.get("seed_group"),
                        "source_domain": source.get("source_domain"),
                        "chunk_index": source.get("chunk_index"),
                        "concept_ids": source.get("concept_ids") or [],
                    }
                ))
        
        return results
    
    def get_by_chunk_ids(
        self,
        chunk_ids: List[str]
    ) -> Dict[str, EmbeddingDocument]:
        """Obtiene embeddings por IDs de chunk (paginado para >10K ids)."""
        if not chunk_ids:
            return {}

        PAGE = 5000  # Mantenerse bajo max_result_window (10000)
        result = {}

        for offset in range(0, len(chunk_ids), PAGE):
            batch_ids = chunk_ids[offset:offset + PAGE]
            query = {
                "size": len(batch_ids),
                "query": {
                    "terms": {"chunk_id": batch_ids}
                },
                "_source": ["embedding_id", "chunk_id", "doc_id", "model_name",
                             "model_version", "embedding_dim", "similarity_metric",
                             "chunk_text_preview", "chunk_index", "section_heading",
                             "seed_group", "source_domain", "concept_ids",
                             "created_at", "chunk_hash"],
            }

            response = self.client.search(index=self.cfg.index_name, body=query)

            for hit in response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                emb = EmbeddingDocument(
                    embedding_id=source.get("embedding_id", ""),
                    chunk_id=source.get("chunk_id", ""),
                    doc_id=source.get("doc_id", ""),
                    vector=source.get("vector", []),
                    model_name=source.get("model_name", ""),
                    model_version=source.get("model_version", ""),
                    embedding_dim=source.get("embedding_dim", 768),
                    similarity_metric=source.get("similarity_metric", "cosine"),
                    chunk_text_preview=source.get("chunk_text_preview"),
                    chunk_index=source.get("chunk_index", 0),
                    section_heading=source.get("section_heading"),
                    seed_group=source.get("seed_group"),
                    source_domain=source.get("source_domain"),
                    concept_ids=source.get("concept_ids"),
                    created_at=source.get("created_at", ""),
                    chunk_hash=source.get("chunk_hash"),
                )
                result[emb.chunk_id] = emb

        return result
    
    def exists_for_chunks(
        self, 
        chunk_ids: List[str],
        chunk_hashes: Optional[Dict[str, str]] = None
    ) -> Dict[str, bool]:
        """Verifica qué chunks ya tienen embeddings."""
        if not chunk_ids:
            return {}
        
        # Buscar embeddings existentes
        existing = self.get_by_chunk_ids(chunk_ids)
        
        result = {}
        for chunk_id in chunk_ids:
            if chunk_id not in existing:
                result[chunk_id] = False
            elif chunk_hashes and chunk_id in chunk_hashes:
                # Verificar si el hash coincide
                existing_hash = existing[chunk_id].chunk_hash
                result[chunk_id] = (existing_hash == chunk_hashes[chunk_id])
            else:
                result[chunk_id] = True
        
        return result
    
    def delete_by_chunk_ids(self, chunk_ids: List[str]) -> int:
        """Elimina embeddings por IDs de chunk."""
        if not chunk_ids:
            return 0
        
        response = self.client.delete_by_query(
            index=self.cfg.index_name,
            body={
                "query": {
                    "terms": {"chunk_id": chunk_ids}
                }
            },
            refresh=True
        )
        
        return response.get("deleted", 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del índice."""
        try:
            count = self.client.count(index=self.cfg.index_name)
            stats = self.client.indices.stats(index=self.cfg.index_name)
            
            index_stats = stats.get("indices", {}).get(self.cfg.index_name, {})
            primaries = index_stats.get("primaries", {})
            
            return {
                "total_embeddings": count.get("count", 0),
                "index_size_bytes": primaries.get("store", {}).get("size_in_bytes", 0),
                "index_name": self.cfg.index_name,
                "vector_dim": self.cfg.vector_dim,
            }
        except Exception as e:
            logger.warning(f"Error getting stats: {e}")
            return {"error": str(e)}
