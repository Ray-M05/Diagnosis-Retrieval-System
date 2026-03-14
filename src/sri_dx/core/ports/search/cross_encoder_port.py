"""Puerto para cross-encoder reranking."""

from abc import ABC, abstractmethod

from sri_dx.modules.ranking.schemas.rerank_schemas import (
    RerankRequest,
    RerankResponse,
)


class CrossEncoderPort(ABC):
    """
    Puerto para cross-encoder reranking.
    
    Define el contrato que cualquier implementación de reranking
    debe cumplir, permitiendo rerankear resultados de búsqueda híbrida
    usando modelos de tipo cross-encoder.
    
    El cross-encoder evalúa directamente la relevancia entre query y documento,
    a diferencia de los bi-encoders que generan embeddings independientes.
    
    Casos de uso:
        - Mejorar precisión de búsqueda híbrida
        - Reordenar top-k resultados candidatos
        - Filtrar resultados por umbral de relevancia
    """

    @abstractmethod
    def rerank(self, request: RerankRequest) -> RerankResponse:
        """
        Reordena resultados de búsqueda según relevancia con la query.
        
        El cross-encoder evalúa cada par (query, documento) y asigna
        un score de relevancia. Los resultados se ordenan por este score.
        
        Args:
            request: Contiene query, resultados híbridos y parámetros de reranking
        
        Returns:
            RerankResponse con resultados reordenados y scores asignados
        
        Raises:
            RerankingError: Si falla el proceso de reranking
            EmptyResultsError: Si la lista de resultados está vacía
            MissingContentError: Si no se puede extraer contenido de resultados
        
        Ejemplo:
            >>> request = RerankRequest(
            ...     query="diabetes tratamiento",
            ...     results=hybrid_results,
            ...     top_k=10
            ... )
            >>> response = cross_encoder.rerank(request)
            >>> for result in response.ranked_results:
            ...     print(f"{result.doc_id}: {result.rerank_score:.3f}")
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si el modelo está cargado y listo para inferencia.
        
        Returns:
            True si el modelo está disponible, False en caso contrario
        """
        ...
