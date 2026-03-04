# core/ports/hybrid_search_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from sri_dx.core.schemas.search.search_query_schema import HybridQuery
from sri_dx.core.schemas.search.search_result_schema import HybridSearchResult

class HybridSearchPort(ABC):
    """
    Puerto para búsqueda híbrida (fusión de vectorial + léxica).
    """
    
    @abstractmethod
    def search(
        self, 
        query: HybridQuery, 
        k: int = 10,
        alpha: float = 0.5,  # Balance vectorial vs léxico
        filter_criteria: Optional[Dict] = None
    ) -> List[HybridSearchResult]:
        """
        Búsqueda híbrida con fusión de resultados.
        
        Args:
            query: Query con componentes semánticos y léxicos
            k: Número de resultados finales
            alpha: Peso (0=solo léxico, 1=solo vectorial, 0.5=balanceado)
            filter_criteria: Filtros por metadatos
            
        Returns:
            Resultados fusionados con scores combinados
        """
        
    
    @abstractmethod
    def get_fusion_strategy(self) -> str:
        """Retorna la estrategia de fusión usada (RRF, CombSUM, etc.)."""
        