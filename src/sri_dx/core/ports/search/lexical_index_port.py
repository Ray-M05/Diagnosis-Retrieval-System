# core/ports/lexical_index_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from sri_dx.core.schemas.search.search_result_schema import LexicalSearchResult
from sri_dx.core.schemas.search.search_query_schema import LexicalQuery

class LexicalIndexPort(ABC):
    """
    Puerto para búsqueda léxica (BM25, TF-IDF, etc.).
    """
    
    @abstractmethod
    def index_documents(
        self, 
        documents: List[Dict[str, Any]], 
        text_field: str = "content",
        config: Optional[Dict] = None
    ) -> None:
        """
        Indexa documentos para búsqueda léxica.
        
        Args:
            documents: Lista de documentos (dicts con id, content, metadata)
            text_field: Campo que contiene el texto
            config: Parámetros (k1, b para BM25, etc.)
        """
        
    
    @abstractmethod
    def search(
        self, 
        query: LexicalQuery, 
        k: int = 50,
        filter_criteria: Optional[Dict] = None
    ) -> List[LexicalSearchResult]:
        """
        Búsqueda léxica.
        
        Args:
            query: Query con términos, operadores, etc.
            k: Número de resultados
            filter_criteria: Filtros adicionales
            
        Returns:
            Resultados con scores BM25/TF-IDF
        """
        