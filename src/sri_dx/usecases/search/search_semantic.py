# usecases/search/search_semantic.py
"""UseCase para búsqueda semántica usando embeddings vectoriales."""

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
    UseCase para búsqueda semántica por similitud de embeddings.
    
    Flujo:
    1. Recibe query en texto natural
    2. Genera embedding de la query con Bio_ClinicalBERT
    3. Busca K vecinos más cercanos en el índice de embeddings
    4. Retorna chunks más similares ordenados por score
    
    Uso:
        use_case = SearchSemanticUseCase(embedding_store=store)
        results = use_case.search(query="diabetes tipo 2", k=10)
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
        Búsqueda semántica por similitud de embeddings.
        
        Args:
            query: Texto de la consulta en lenguaje natural
            k: Número de resultados a retornar
            min_score: Score mínimo (similitud coseno) para incluir resultado
            filters: Filtros por metadatos (seed_group, source_domain, etc.)
            
        Returns:
            Lista de resultados ordenados por similitud descendente
        """
        if not query.strip():
            logger.warning("Query vacío recibido en búsqueda semántica")
            return []
        
        # 1. Generar embedding de la query
        logger.debug(f"Generando embedding para query: '{query[:100]}...'")
        query_embedding = self.bert_adapter.encode([query])
        query_vector = query_embedding[0].numpy()
        
        # 2. Buscar K vecinos más cercanos
        logger.debug(f"Buscando {k} vecinos más cercanos con filtros={filters}")
        results = self.embedding_store.search_similar(
            query_vector=query_vector,
            k=k,
            filters=filters,
            min_score=min_score
        )
        
        logger.info(f"Búsqueda semántica completada: {len(results)} resultados")
        return results
    
    def batch_search(
        self,
        queries: List[str],
        k: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[List[EmbeddingSearchResult]]:
        """
        Búsqueda semántica para múltiples queries en batch.
        
        Args:
            queries: Lista de textos de consulta
            k: Número de resultados por query
            min_score: Score mínimo
            filters: Filtros comunes para todas las queries
            
        Returns:
            Lista de listas de resultados (una por query)
        """
        if not queries:
            return []
        
        # Generar embeddings en batch
        logger.debug(f"Generando embeddings para {len(queries)} queries")
        query_embeddings = self.bert_adapter.encode(queries)
        
        # Buscar para cada embedding
        all_results = []
        for i, query_vector in enumerate(query_embeddings):
            results = self.embedding_store.search_similar(
                query_vector=query_vector.numpy(),
                k=k,
                filters=filters,
                min_score=min_score
            )
            all_results.append(results)
        
        logger.info(f"Batch search completado: {len(queries)} queries procesadas")
        return all_results
