# adapters/stores/opensearch_chunk_reader.py
"""Adapter for reading chunks from OpenSearch."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any, Iterator

from .schemas.opensearch_chunk_reader_config import OpenSearchChunkReaderConfig

from opensearchpy import OpenSearch

from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument

logger = logging.getLogger(__name__)


# OpenSearchChunkReaderConfig is provided by adapters.stores.schemas.opensearch_chunk_reader_config


class OpenSearchChunkReader:
    """
    Reads chunks from OpenSearch for embedding processing.

    Usage:
        reader = OpenSearchChunkReader(config)
        for batch in reader.iter_chunks_batched(batch_size=100):
            process(batch)
    """
    
    def __init__(self, cfg: OpenSearchChunkReaderConfig) -> None:
        self.cfg = cfg
        self.client = OpenSearch(
            hosts=[{"host": cfg.host, "port": cfg.port}],
            use_ssl=cfg.use_ssl,
            verify_certs=cfg.verify_certs,
            http_compress=True,
            timeout=cfg.request_timeout,
        )
    
    def get_total_chunks(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Returns the total number of chunks in the index."""
        query = self._build_query(filters)
        response = self.client.count(index=self.cfg.index_name, body=query)
        return response.get("count", 0)
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[ChunkDocument]:
        """Retrieves a chunk by its ID."""
        try:
            response = self.client.get(index=self.cfg.index_name, id=chunk_id)
            if response.get("found"):
                return self._parse_chunk(response["_source"])
            return None
        except Exception as e:
            logger.warning(f"Error getting chunk {chunk_id}: {e}")
            return None
    
    def get_chunks_by_ids(self, chunk_ids: List[str]) -> Dict[str, ChunkDocument]:
        """Retrieves multiple chunks by their IDs."""
        if not chunk_ids:
            return {}
        
        response = self.client.mget(
            index=self.cfg.index_name,
            body={"ids": chunk_ids}
        )
        
        result = {}
        for doc in response.get("docs", []):
            if doc.get("found"):
                chunk = self._parse_chunk(doc["_source"])
                result[chunk.chunk_id] = chunk
        
        return result
    
    def iter_chunks(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        exclude_with_embedding: bool = False
    ) -> Iterator[ChunkDocument]:
        """
        Iterates over all chunks in the index.

        Args:
            filters: Additional filters (seed_group, source_domain, etc.)
            exclude_with_embedding: If True, excludes chunks that already have an embedding

        Yields:
            ChunkDocument one at a time
        """
        query = self._build_query(filters, exclude_with_embedding)

        # Start scroll
        response = self.client.search(
            index=self.cfg.index_name,
            body=query,
            scroll=self.cfg.scroll_timeout,
            size=self.cfg.scroll_size,
        )
        
        scroll_id = response.get("_scroll_id")
        hits = response.get("hits", {}).get("hits", [])
        
        try:
            while hits:
                for hit in hits:
                    yield self._parse_chunk(hit["_source"])
                
                # Fetch next batch
                response = self.client.scroll(
                    scroll_id=scroll_id,
                    scroll=self.cfg.scroll_timeout,
                )
                scroll_id = response.get("_scroll_id")
                hits = response.get("hits", {}).get("hits", [])
        finally:
            # Clear scroll context
            if scroll_id:
                try:
                    self.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass

    def iter_chunks_batched(
        self,
        batch_size: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        exclude_with_embedding: bool = False
    ) -> Iterator[List[ChunkDocument]]:
        """
        Iterates over chunks in batches.

        Args:
            batch_size: Batch size
            filters: Additional filters
            exclude_with_embedding: Exclude chunks that already have an embedding

        Yields:
            List of chunks (one batch)
        """
        batch = []
        for chunk in self.iter_chunks(filters, exclude_with_embedding):
            batch.append(chunk)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        # Yield remaining
        if batch:
            yield batch
    
    def get_chunk_ids_and_hashes(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Returns a chunk_id -> chunk_hash mapping for re-embedding verification.

        Returns:
            Dict mapping chunk_id -> chunk_hash
        """
        result = {}
        query = self._build_query(filters)
        query["_source"] = ["chunk_id", "chunk_hash"]
        
        response = self.client.search(
            index=self.cfg.index_name,
            body=query,
            scroll=self.cfg.scroll_timeout,
            size=self.cfg.scroll_size,
        )
        
        scroll_id = response.get("_scroll_id")
        hits = response.get("hits", {}).get("hits", [])
        
        try:
            while hits:
                for hit in hits:
                    src = hit["_source"]
                    result[src.get("chunk_id")] = src.get("chunk_hash")
                
                response = self.client.scroll(
                    scroll_id=scroll_id,
                    scroll=self.cfg.scroll_timeout,
                )
                scroll_id = response.get("_scroll_id")
                hits = response.get("hits", {}).get("hits", [])
        finally:
            if scroll_id:
                try:
                    self.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass
        
        return result
    
    def _build_query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        exclude_with_embedding: bool = False
    ) -> Dict[str, Any]:
        """Builds the query with optional filters."""
        must = []
        must_not = []

        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    must.append({"terms": {field: value}})
                else:
                    must.append({"term": {field: value}})

        if exclude_with_embedding:
            # Exclude chunks that already have an embedding
            must_not.append({"exists": {"field": "embedding"}})
        
        if not must and not must_not:
            return {"query": {"match_all": {}}}
        
        return {
            "query": {
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "must_not": must_not
                }
            }
        }
    
    def _parse_chunk(self, source: Dict[str, Any]) -> ChunkDocument:
        """Converts an OpenSearch document to a ChunkDocument."""
        return ChunkDocument(
            chunk_id=source.get("chunk_id", ""),
            doc_id=source.get("doc_id", ""),
            url=source.get("url", ""),
            source_domain=source.get("source_domain", ""),
            fetched_at=source.get("fetched_at", ""),
            mime_type=source.get("mime_type", ""),
            seed_group=source.get("seed_group", ""),
            seed_id=source.get("seed_id", ""),
            depth=source.get("depth", 0),
            section_heading=source.get("section_heading", ""),
            section_index=source.get("section_index", 0),
            chunk_index=source.get("chunk_index", 0),
            start_char=source.get("start_char", 0),
            end_char=source.get("end_char", 0),
            chunk_text=source.get("chunk_text", ""),
            language=source.get("language"),
            content_hash=source.get("content_hash"),
            chunk_hash=source.get("chunk_hash"),
            concept_ids=source.get("concept_ids"),
            embedding=source.get("embedding"),
        )
