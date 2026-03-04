# core/ports/vector_index_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

from sri_dx.core.schemas.search.search_result_schema import VectorSearchResult

class VectorIndexPort(ABC):
    """
    Puerto para índices vectoriales (ANN/KNN).
    """
    
    @abstractmethod
    def build_index(
        self, 
        vectors: "NDArray[Any]", 
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict] = None
    ) -> None:
        """
        Construye el índice vectorial.
        
        Args:
            vectors: Array de vectores (n_samples, dimension)
            ids: IDs únicos para cada vector
            metadata: Metadatos asociados a cada vector
            config: Parámetros del índice (ef_construction, M, etc.)
        """
        
    
    @abstractmethod
    def search(
        self, 
        query_vector: "NDArray[Any]", 
        k: int = 50,
        filter_criteria: Optional[Dict] = None
    ) -> List[VectorSearchResult]:
        """
        Búsqueda de K vecinos más cercanos.
        
        Args:
            query_vector: Vector de consulta
            k: Número de resultados
            filter_criteria: Filtros por metadatos
            
        Returns:
            Lista de resultados con scores y metadatos
        """
        
    
    @abstractmethod
    def batch_search(
        self, 
        query_vectors: "NDArray[Any]", 
        k: int = 50
    ) -> List[List[VectorSearchResult]]:
        """Búsqueda por lotes (optimizada)."""
        
    
    @abstractmethod
    def add_vectors(
        self, 
        vectors: "NDArray[Any]", 
        ids: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """Añade vectores al índice existente."""
        
    
    @abstractmethod
    def remove_vectors(self, ids: List[str]) -> None:
        """Elimina vectores del índice."""
        
    
    @abstractmethod
    def save_index(self, path: str) -> None:
        """Persiste el índice en disco."""
        
    
    @abstractmethod
    def load_index(self, path: str) -> None:
        """Carga el índice desde disco."""
        
    
    @abstractmethod
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Estadísticas del índice.
        Ej: tamaño, número de vectores, memoria usada, etc.
        """
        