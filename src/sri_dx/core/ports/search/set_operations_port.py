# core/ports/set_operations_port.py
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Callable, Optional
from sri_dx.core.schemas.search.search_result_schema import SearchResult

class SetOperationsPort(ABC):
    """
    Puerto para operaciones de conjuntos sobre resultados.
    """
    
    @abstractmethod
    def intersect(
        self, 
        result_sets: List[List[SearchResult]],
        merge_strategy: str = "max_score"
    ) -> List[SearchResult]:
        """
        Intersección de múltiples conjuntos de resultados.
        
        Args:
            result_sets: Listas de resultados a intersectar
            merge_strategy: Cómo combinar scores (max, min, avg)
            
        Returns:
            Documentos que aparecen en TODOS los conjuntos
        """

    
    @abstractmethod
    def negate(
        self, 
        positive_results: List[SearchResult],
        negative_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Negación: resultados en positive pero NO en negative.
        """

    
    @abstractmethod
    def filter_by_metadata(
        self, 
        results: List[SearchResult],
        filter_fn: Callable[[Dict], bool]
    ) -> List[SearchResult]:
        """
        Filtra resultados según función de metadatos.
        
        """


    
    @abstractmethod
    def filter_by_score_threshold(
        self, 
        results: List[SearchResult],
        min_score: float
    ) -> List[SearchResult]:
        """Filtra por score mínimo."""