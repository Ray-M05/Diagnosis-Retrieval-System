# core/ports/search/embedding_store_port.py
"""Puerto para almacenamiento y recuperación de embeddings."""

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
    Puerto para almacenamiento y recuperación de embeddings vectoriales.
    
    Responsabilidades:
    - Almacenar embeddings con metadata
    - Búsqueda kNN por similitud
    - Verificar si un chunk ya tiene embedding
    """
    
    @abstractmethod
    def store_embeddings(
        self, 
        embeddings: List[EmbeddingDocument],
        refresh: bool = False
    ) -> int:
        """
        Almacena embeddings en el índice.
        
        Args:
            embeddings: Lista de documentos de embedding
            refresh: Si True, hace refresh del índice después de insertar
            
        Returns:
            Número de embeddings almacenados con éxito
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
        Busca embeddings similares al vector query.
        
        Args:
            query_vector: Vector de búsqueda (debe ser mismo dim que índice)
            k: Número de resultados
            filters: Filtros adicionales (seed_group, source_domain, etc.)
            min_score: Score mínimo para incluir en resultados
            
        Returns:
            Lista de resultados ordenados por similitud descendente
        """
    
    @abstractmethod
    def get_by_chunk_ids(
        self, 
        chunk_ids: List[str]
    ) -> Dict[str, EmbeddingDocument]:
        """
        Obtiene embeddings por IDs de chunk.
        
        Args:
            chunk_ids: IDs de chunks a buscar
            
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
        Verifica qué chunks ya tienen embeddings.
        
        Args:
            chunk_ids: IDs de chunks a verificar
            chunk_hashes: Opcional - si se provee, también verifica que el hash coincida
            
        Returns:
            Dict mapping chunk_id -> exists (True/False)
        """
    
    @abstractmethod
    def delete_by_chunk_ids(self, chunk_ids: List[str]) -> int:
        """
        Elimina embeddings por IDs de chunk.
        
        Returns:
            Número de embeddings eliminados
        """
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del índice.
        
        Returns:
            Dict con total_embeddings, index_size, etc.
        """
