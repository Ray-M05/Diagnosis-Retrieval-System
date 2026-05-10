"""
Two-Stage Retrieval Pipeline.

Pipeline que integra búsqueda híbrida con reranking mediante cross-encoder.

Etapas:
1. Búsqueda híbrida (léxica + semántica) → top-100 candidatos
2. Cross-encoder reranking → top-10 resultados finales

Uso:
    python -m sri_dx.usecases.search.two_stage_retrieval_pipeline
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
from sri_dx.modules.ranking.disease_aggregator import DiseaseAggregator, DiseaseAggregatorConfig
from sri_dx.core.schemas.search.disease_result import DiseaseResult

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

    # Disease aggregation
    min_ner_score: float = 0.5  # Confianza mínima de NER
    max_diseases: int = 10  # Máximo de enfermedades a retornar
    positioned_results: int = 10  # Máximo de condiciones posicionadas a retornar


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
    disease_aggregator: Optional[DiseaseAggregator] = None
    positioning_service: Optional[Any] = None
    
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
    
    def search_diseases(
        self,
        query: str,
        hybrid_candidates: Optional[int] = None,
        final_results: Optional[int] = None,
    ) -> List[DiseaseResult]:
        """
        Búsqueda en tres etapas: híbrida → reranking → NER on-demand → agregación por enfermedad.

        NER se calcula solo sobre los top-K chunks rerankeados (no durante indexado).

        Args:
            query: Query del usuario (síntomas, lab tests, etc.)
            hybrid_candidates: Override de número de candidatos
            final_results: Override de resultados del cross-encoder

        Returns:
            Lista de enfermedades rankeadas con evidencia de soporte.
        """
        chunk_results = self.search(query, hybrid_candidates, final_results)

        if not chunk_results:
            logger.warning("No hay chunks para agregar en enfermedades")
            return []

        # NER on-demand: calcular entidades solo para los chunks rerankeados
        self._apply_ner_to_results(chunk_results)

        if self.disease_aggregator is None:
            self.disease_aggregator = DiseaseAggregator(
                DiseaseAggregatorConfig(
                    min_ner_score=self.config.min_ner_score,
                    max_diseases=self.config.max_diseases,
                )
            )

        diseases = self.disease_aggregator.aggregate(chunk_results)
        logger.info("Agregación completada: %d enfermedades identificadas", len(diseases))
        return diseases

    def search_positioned(
        self,
        query: str,
        hybrid_candidates: Optional[int] = None,
        final_results: Optional[int] = None,
        positioned_results: Optional[int] = None,
    ) -> list:
        """
        Búsqueda posicionada: híbrida → reranking → NER on-demand → posicionamiento clínico.

        No modifica el comportamiento de search() ni search_diseases().
        """
        chunk_results = self.search(query, hybrid_candidates, final_results)

        if not chunk_results:
            logger.warning("No hay chunks para posicionamiento clínico")
            return []

        self._apply_ner_to_results(chunk_results)

        top_k = positioned_results or self.config.positioned_results
        positioning_service = self.positioning_service
        if positioning_service is None:
            from sri_dx.modules.positioning import ClinicalPositioningService, PositioningConfig

            positioning_service = ClinicalPositioningService(
                PositioningConfig(
                    top_k=top_k,
                    min_ner_score=self.config.min_ner_score,
                )
            )

        positioned = positioning_service.position(
            query=query,
            retrieval_results=chunk_results,
            top_k=top_k,
        )
        logger.info("Posicionamiento completado: %d condiciones", len(positioned))
        return positioned

    def _apply_ner_to_results(self, results: List[RetrievalResult]) -> None:
        """Aplica NER en batch sobre los chunks rerankeados e inyecta ner_entities en metadata."""
        try:
            from sri_dx.adapters.embeddings.biomedical_ner_adapter import BiomedicalNERAdapter
        except ImportError:
            logger.warning("BiomedicalNERAdapter no disponible. Enfermedades sin NER.")
            return

        texts = []
        for r in results:
            text = (r.content or r.metadata.get("content", "") or "").strip()
            texts.append(text)

        if not any(texts):
            return

        ner_adapter = BiomedicalNERAdapter.get_instance()
        logger.info("Ejecutando NER on-demand sobre %d chunks rerankeados...", len(texts))
        batch_entities = ner_adapter.predict_batch(texts)

        for result, entities in zip(results, batch_entities):
            ner_list = [
                {
                    "text": e["word"],
                    "label": e["domain_label"],
                    "start_char": e["start"],
                    "end_char": e["end"],
                    "score": e["score"],
                }
                for e in entities
            ]
            if result.metadata is None:
                result.metadata = {}
            result.metadata["ner_entities"] = ner_list

    def print_disease_results(self, diseases: List[DiseaseResult]) -> None:
        """Imprime ranking de enfermedades de forma legible."""
        print("\n" + "=" * 80)
        print(f"ENFERMEDADES IDENTIFICADAS: {len(diseases)}")
        print("=" * 80)

        for disease in diseases:
            print("\n" + str(disease))

        print("\n" + "=" * 80)

    def print_positioned_results(self, positioned: list) -> None:
        """Imprime ranking de condiciones posicionadas de forma legible."""
        print("\n" + "=" * 80)
        print(f"CONDICIONES POSICIONADAS: {len(positioned)}")
        print("=" * 80)

        for result in positioned:
            print(
                f"\n#{result.rank} - {result.disease_name_display} "
                f"({result.relevance_label}, score={result.final_score:.4f})"
            )
            if result.matched_symptoms:
                print(f"  Coincidencias: {', '.join(result.matched_symptoms)}")
            if result.source_domains:
                print(f"  Fuentes: {', '.join(result.source_domains[:3])}")
            for explanation in result.explanation:
                print(f"  - {explanation}")
            for evidence in result.evidences[:3]:
                print(
                    f"    Evidencia chunk={evidence.chunk_id}, "
                    f"ce={evidence.cross_encoder_score}, url={evidence.url}"
                )

        print("\n" + "=" * 80)

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
