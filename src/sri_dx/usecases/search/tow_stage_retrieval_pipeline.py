"""
Two-Stage Retrieval Pipeline.

Pipeline que integra búsqueda híbrida con reranking mediante cross-encoder.

Etapas:
1. Búsqueda híbrida (léxica + semántica) → top-100 candidatos
2. Cross-encoder reranking → top-10 resultados finales

Uso:
    python -m sri_dx.usecases.search.tow_stage_retrieval_pipeline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
from sri_dx.adapters.embeddings import SentenceTransformersCrossEncoderAdapter
from sri_dx.modules.ranking.schemas import (
    CrossEncoderConfig,
    RerankRequest,
    RerankResult,
)

logger = logging.getLogger(__name__)


@dataclass
class TwoStageRetrievalConfig:
    """Configuración del pipeline de dos etapas."""
    
    # Stage 1: Hybrid Search
    hybrid_candidates: int = 100  # Número de candidatos de búsqueda híbrida
    
    # Stage 2: Reranking
    final_results: int = 10  # Número de resultados finales tras reranking
    
    # Cross-encoder config
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    device: str = "cpu"
    batch_size: int = 32
    score_threshold: Optional[float] = None  # Filtro opcional por score
    
    # Content extraction
    content_field: str = "content"  # Campo en metadata con el texto del documento


@dataclass
class RetrievalResult:
    """Resultado final del pipeline con información enriquecida."""
    
    doc_id: str
    rerank_score: float
    original_hybrid_score: float
    lexical_score: Optional[float]
    vector_score: Optional[float]
    
    # Posiciones
    original_position: int
    final_position: int
    
    # Metadata del documento
    metadata: Dict[str, Any]
    
    # Contenido
    content: Optional[str] = None
    
    def __str__(self) -> str:
        """Representación legible del resultado."""
        lines = [
            f"#{self.final_position + 1} - Doc ID: {self.doc_id}",
            f"  Rerank Score: {self.rerank_score:.4f}",
            f"  Hybrid Score: {self.original_hybrid_score:.4f}",
            f"  Lexical: {self.lexical_score:.4f if self.lexical_score else 'N/A'}",
            f"  Vector: {self.vector_score:.4f if self.vector_score else 'N/A'}",
            f"  Position: {self.original_position + 1} → {self.final_position + 1}",
        ]
        
        if self.metadata:
            lines.append(f"  Metadata: {self.metadata}")
        
        if self.content:
            content_preview = self.content[:200] + "..." if len(self.content) > 200 else self.content
            lines.append(f"  Content: {content_preview}")
        
        return "\n".join(lines)


@dataclass
class TwoStageRetrievalPipeline:
    """
    Pipeline de búsqueda en dos etapas.
    
    Combina búsqueda híbrida rápida con reranking preciso usando cross-encoder.
    
    Flujo:
    1. Stage 1: Búsqueda híbrida (BM25 + kNN) → top-100 candidatos
    2. Stage 2: Cross-encoder reranking → top-10 finales
    
    Ejemplo:
        >>> pipeline = TwoStageRetrievalPipeline(
        ...     hybrid_search=hybrid_search_usecase,
        ...     config=TwoStageRetrievalConfig()
        ... )
        >>> results = pipeline.search("diabetes tratamiento")
        >>> for result in results:
        ...     print(result)
    """
    
    hybrid_search: SearchHybridUseCase
    config: TwoStageRetrievalConfig = field(default_factory=TwoStageRetrievalConfig)
    cross_encoder: Optional[SentenceTransformersCrossEncoderAdapter] = None
    
    def __post_init__(self):
        """Inicializa el cross-encoder si no fue proporcionado."""
        if self.cross_encoder is None:
            logger.info("Inicializando cross-encoder...")
            ce_config = CrossEncoderConfig(
                model_name=self.config.cross_encoder_model,
                device=self.config.device,
                batch_size=self.config.batch_size,
                top_k=self.config.final_results,
                score_threshold=self.config.score_threshold,
            )
            self.cross_encoder = SentenceTransformersCrossEncoderAdapter(ce_config)
            logger.info("Cross-encoder inicializado correctamente")
    
    def search(
        self,
        query: str,
        hybrid_candidates: Optional[int] = None,
        final_results: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        Ejecuta búsqueda en dos etapas.
        
        Args:
            query: Query del usuario
            hybrid_candidates: Override de número de candidatos (None = usar config)
            final_results: Override de resultados finales (None = usar config)
        
        Returns:
            Lista de resultados finales rerankeados
        
        Raises:
            ValueError: Si query está vacía
        """
        if not query or not query.strip():
            raise ValueError("Query no puede estar vacía")
        
        # Parámetros
        k_candidates = hybrid_candidates or self.config.hybrid_candidates
        k_final = final_results or self.config.final_results
        
        logger.info("=== Búsqueda en 2 etapas: '%s...' ===", query[:50])
        logger.info("Stage 1: %d candidatos | Stage 2: %d finales", k_candidates, k_final)
        
        # Stage 1: Búsqueda híbrida
        logger.info("Stage 1: Ejecutando búsqueda híbrida...")
        hybrid_results = self.hybrid_search.search(query=query, k=k_candidates)
        
        if not hybrid_results:
            logger.warning("Búsqueda híbrida no retornó resultados")
            return []
        
        logger.info("Stage 1 completado: %d candidatos obtenidos", len(hybrid_results))
        
        # Stage 2: Reranking con cross-encoder
        logger.info("Stage 2: Ejecutando reranking con cross-encoder...")
        rerank_request = RerankRequest(
            query=query,
            results=hybrid_results,
            top_k=k_final,
            content_field=self.config.content_field,
        )
        
        rerank_response = self.cross_encoder.rerank(rerank_request)
        logger.info("Stage 2 completado: %d resultados finales", len(rerank_response.ranked_results))
        
        # Convertir a RetrievalResult enriquecido
        final_results = self._enrich_results(rerank_response.ranked_results)
        
        logger.info("Pipeline completado: %d resultados", len(final_results))
        return final_results
    
    def _enrich_results(self, rerank_results: List[RerankResult]) -> List[RetrievalResult]:
        """
        Convierte RerankResult a RetrievalResult con información enriquecida.
        
        Args:
            rerank_results: Resultados del reranking
        
        Returns:
            Lista de resultados enriquecidos
        """
        enriched = []
        
        for rr in rerank_results:
            # Extraer contenido si está disponible
            content = None
            if rr.original_result.metadata and self.config.content_field in rr.original_result.metadata:
                content = rr.original_result.metadata.get(self.config.content_field)
            
            result = RetrievalResult(
                doc_id=rr.doc_id,
                rerank_score=rr.rerank_score,
                original_hybrid_score=rr.original_result.score,
                lexical_score=rr.original_result.lexical_score,
                vector_score=rr.original_result.vector_score,
                original_position=rr.original_position,
                final_position=rr.new_position if rr.new_position is not None else rr.original_position,
                metadata=rr.original_result.metadata or {},
                content=content,
            )
            enriched.append(result)
        
        return enriched
    
    def print_results(self, results: List[RetrievalResult]) -> None:
        """
        Imprime resultados de forma legible.
        
        Args:
            results: Resultados a imprimir
        """
        print("\n" + "=" * 80)
        print(f"RESULTADOS FINALES: {len(results)} documentos")
        print("=" * 80)
        
        for result in results:
            print("\n" + str(result))
        
        print("\n" + "=" * 80)


def main():
    """
    Función principal para testing del pipeline.
    
    Permite hardcodear la query para pruebas rápidas.
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Query hardcodeada (modificar según necesidad)
    HARDCODED_QUERY = ""
    
    print("\n" + "=" * 80)
    print("TWO-STAGE RETRIEVAL PIPELINE - TEST")
    print("=" * 80)
    print(f"\nQuery: {HARDCODED_QUERY}\n")
    
    # TODO: Inicializar componentes reales
    # Por ahora, este es un skeleton que muestra la estructura
    
    print("⚠️  NOTA: Para ejecutar este pipeline necesitas:")
    print("  1. Configurar SearchHybridUseCase con:")
    print("     - lexical_backend (OpenSearchAdapter o ElasticsearchAdapter)")
    print("     - embedding_store (QdrantAdapter o ChromaAdapter)")
    print("  2. Asegurarte de que los índices existen y tienen datos")
    print("  3. Tener los modelos descargados (ClinicalBERT, cross-encoder)")
    print("\nEjemplo de configuración:")
    print("""
    from sri_dx.adapters.stores import OpenSearchAdapter, QdrantAdapter
    from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
    from sri_dx.usecases.search.schemas import HybridSearchConfig
    
    # Configurar backends
    lexical_backend = OpenSearchAdapter(...)
    embedding_store = QdrantAdapter(...)
    
    # Crear usecase de búsqueda híbrida
    hybrid_config = HybridSearchConfig(
        fusion_method="rrf",
        lexical_k=100,
        semantic_k=100,
    )
    hybrid_search = SearchHybridUseCase(
        lexical_backend=lexical_backend,
        embedding_store=embedding_store,
        config=hybrid_config,
    )
    
    # Configurar pipeline
    pipeline_config = TwoStageRetrievalConfig(
        hybrid_candidates=100,
        final_results=10,
        cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        device="cpu",
    )
    
    # Crear y ejecutar pipeline
    pipeline = TwoStageRetrievalPipeline(
        hybrid_search=hybrid_search,
        config=pipeline_config,
    )
    
    results = pipeline.search(HARDCODED_QUERY)
    pipeline.print_results(results)
    """)


if __name__ == "__main__":
    main()