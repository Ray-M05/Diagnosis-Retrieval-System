# core/ports/search/embedding_store_port.py
"""Port for embedding storage and retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray

from sri_dx.core.schemas.indexing.embedding_document import EmbeddingDocument
from sri_dx.core.schemas.search.vector_search_schema import (
    EmbeddingSearchResult,
    EmbeddingStoreConfig,
)


class EmbeddingStorePort(ABC):
    """
    Port for storing and retrieving vector embeddings.

    Responsibilities:
    - Store embeddings with metadata
    - kNN search by similarity
    - Check whether a chunk already has an embedding
    """
    
    @abstractmethod
    def store_embeddings(
        self, 
        embeddings: List[EmbeddingDocument],
        refresh: bool = False
    ) -> int:
        """
        Stores embeddings in the index.

        Args:
            embeddings: List of embedding documents
            refresh: If True, refreshes the index after insertion

        Returns:
            Number of embeddings successfully stored
        """
    
    @abstractmethod
    def search_similar(
        self,
        query_vector: "NDArray[Any]",
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[EmbeddingSearchResult]:
        """
        Searches for embeddings similar to the query vector.

        Args:
            query_vector: Query vector (must match index dimension)
            k: Number of results
            filters: Additional filters (seed_group, source_domain, etc.)
            min_score: Minimum score to include in results

        Returns:
            List of results ordered by descending similarity
        """
    
    @abstractmethod
    def get_by_chunk_ids(
        self, 
        chunk_ids: List[str]
    ) -> Dict[str, EmbeddingDocument]:
        """
        Retrieves embeddings by chunk IDs.

        Args:
            chunk_ids: IDs of chunks to retrieve

        Returns:
            Dict mapping chunk_id -> EmbeddingDocument
        """
    
    @abstractmethod
    def exists_for_chunks(
        self, 
        chunk_ids: List[str],
        chunk_hashes: Optional[Dict[str, str]] = None
    ) -> Dict[str, bool]:
        """
        Checks which chunks already have embeddings.

        Args:
            chunk_ids: IDs of chunks to check
            chunk_hashes: Optional - if provided, also verifies that the hash matches

        Returns:
            Dict mapping chunk_id -> exists (True/False)
        """
    
    @abstractmethod
    def delete_by_chunk_ids(self, chunk_ids: List[str]) -> int:
        """
        Deletes embeddings by chunk IDs.

        Returns:
            Number of embeddings deleted
        """
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Returns index statistics.

        Returns:
            Dict with total_embeddings, index_size, etc.
        """
