# usecases/search/search_semantic.py
"""Use case for semantic search using vector embeddings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from sri_dx.core.ports.search.embedding_store_port import EmbeddingStorePort
from sri_dx.core.schemas.search.vector_search_schema import EmbeddingSearchResult
from sri_dx.adapters.embeddings.clinical_bert_adapter import ClinicalBERTAdapter

logger = logging.getLogger(__name__)


@dataclass
class SearchSemanticUseCase:
    """
    Use case for semantic search by embedding similarity.

    Flow:
    1. Receives a natural-language query
    2. Encodes the query with Bio_ClinicalBERT
    3. Searches for K nearest neighbours in the embeddings index
    4. Returns the most similar chunks ordered by score

    Usage:
        use_case = SearchSemanticUseCase(embedding_store=store)
        results = use_case.search(query="type 2 diabetes", k=10)
    """
    
    embedding_store: EmbeddingStorePort
    bert_adapter: Optional[ClinicalBERTAdapter] = None
    
    def __post_init__(self):
        """Initialize BERT adapter if not provided."""
        if self.bert_adapter is None:
            self.bert_adapter = ClinicalBERTAdapter.get_instance()
    
    def search(
        self,
        query: str,
        k: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[EmbeddingSearchResult]:
        """
        Semantic search by embedding similarity.

        Args:
            query: Natural-language query text
            k: Number of results to return
            min_score: Minimum score (cosine similarity) to include a result
            filters: Metadata filters (seed_group, source_domain, etc.)

        Returns:
            List of results ordered by descending similarity
        """
        if not query.strip():
            logger.warning("Empty query received in semantic search")
            return []

        # 1. Encode the query
        logger.debug(f"Encoding query: '{query[:100]}...'")
        query_embedding = self.bert_adapter.encode([query])
        query_vector = query_embedding[0].numpy()

        # 2. Search for K nearest neighbours
        logger.debug(f"Searching {k} nearest neighbours with filters={filters}")
        results = self.embedding_store.search_similar(
            query_vector=query_vector,
            k=k,
            filters=filters,
            min_score=min_score
        )

        logger.info(f"Semantic search completed: {len(results)} results")
        return results
    
    def batch_search(
        self,
        queries: List[str],
        k: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[List[EmbeddingSearchResult]]:
        """
        Semantic search for multiple queries in batch.

        Args:
            queries: List of query texts
            k: Number of results per query
            min_score: Minimum score
            filters: Common filters applied to all queries

        Returns:
            List of result lists (one per query)
        """
        if not queries:
            return []

        # Generate embeddings in batch
        logger.debug(f"Encoding {len(queries)} queries")
        query_embeddings = self.bert_adapter.encode(queries)

        all_results = []
        for i, query_vector in enumerate(query_embeddings):
            results = self.embedding_store.search_similar(
                query_vector=query_vector.numpy(),
                k=k,
                filters=filters,
                min_score=min_score
            )
            all_results.append(results)

        logger.info(f"Batch search completed: {len(queries)} queries processed")
        return all_results
