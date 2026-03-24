# usecases/search/search_hybrid.py
"""UseCase para búsqueda híbrida (léxica + semántica)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import List, Optional, Dict, Any, Tuple

from sri_dx.core.ports.search.search_backend import SearchBackendPort
from sri_dx.core.ports.search.embedding_store_port import EmbeddingStorePort
from sri_dx.core.schemas.search.search_request import SearchRequest, SearchFilters
from sri_dx.core.schemas.search.search_result_schema import HybridSearchResult
from sri_dx.adapters.embeddings.clinical_bert_adapter import ClinicalBERTAdapter
from sri_dx.modules.ranking.fusion import reciprocal_rank_fusion, weighted_sum_fusion
from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor

logger = logging.getLogger(__name__)


# HybridSearchConfig ahora está en usecases.search.schemas.hybrid_search_config


@dataclass
class SearchHybridUseCase:
    """
    UseCase para búsqueda híbrida combinando:
    - Búsqueda léxica (BM25) sobre documentos completos
    - Búsqueda semántica (kNN) sobre embeddings de chunks
    
    Fusiona resultados usando RRF o suma ponderada.
    
    Flujo:
    1. Ejecuta búsqueda léxica en paralelo con semántica
    2. Mapea chunk_ids → doc_ids para búsqueda semántica
    3. Fusiona rankings usando método configurado (RRF/weighted_sum)
    4. Enriquece resultados con metadatos de ambas fuentes
    
    Uso:
        config = HybridSearchConfig(fusion_method="rrf")
        use_case = SearchHybridUseCase(
            lexical_backend=lexical_backend,
            embedding_store=embedding_store,
            config=config
        )
        results = use_case.search(query="diabetes tratamiento", k=10)
    """
    
    lexical_backend: SearchBackendPort
    embedding_store: EmbeddingStorePort
    config: HybridSearchConfig = field(default_factory=HybridSearchConfig)
    bert_adapter: Optional[ClinicalBERTAdapter] = None
    
    def __post_init__(self):
        """Initialize BERT adapter if not provided."""
        if self.bert_adapter is None:
            self.bert_adapter = ClinicalBERTAdapter.get_instance()
    
    def search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[SearchFilters] = None,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[HybridSearchResult]:
        """
        Búsqueda híbrida fusionando léxica + semántica.
        
        Args:
            query: Texto de consulta
            k: Número de resultados finales
            filters: Filtros para búsqueda léxica
            metadata_filters: Filtros para búsqueda semántica
            
        Returns:
            Resultados híbridos ordenados por score fusionado
        """
        if not query.strip():
            logger.warning("Query vacío en búsqueda híbrida")
            return []
        
        logger.info(f"Búsqueda híbrida: '{query[:100]}...' (k={k})")
        
        # 1. Búsqueda léxica
        lexical_results = self._lexical_search(query, filters)
        logger.debug(f"Búsqueda léxica: {len(lexical_results)} resultados")
        
        # 2. Búsqueda semántica  
        semantic_results = self._semantic_search(query, metadata_filters)
        logger.debug(f"Búsqueda semántica: {len(semantic_results)} resultados")
        
        # 3. Fusionar resultados
        fused_results = self._fuse_results(
            lexical_results,
            semantic_results,
            k
        )
        
        logger.info(f"Búsqueda híbrida completada: {len(fused_results)} resultados")
        return fused_results
    
    def _lexical_search(
        self,
        query: str,
        filters: Optional[SearchFilters]
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Ejecuta búsqueda léxica.
        
        Returns:
            Lista de (doc_id, score, metadata)
        """
        # Expansion by concepts
        extractor = ConceptExtractor()
        concepts = extractor.extract(query)
        
        final_filters = filters or SearchFilters()
        if concepts:
            current = set(final_filters.concept_ids or [])
            current.update(concepts)
            final_filters = replace(final_filters, concept_ids=list(current))

        request = SearchRequest(
            query=query,
            k=self.config.lexical_k,
            offset=0,
            operator="or" if concepts else "and",
            filters=final_filters,
            return_highlights=False,
            facet_fields=()
        )
        
        response = self.lexical_backend.search(request)
        
        results = []
        for hit in response.hits:
            metadata = {
                "chunk_id": hit.chunk_id,
                "doc_id": hit.doc_id,
                "url": hit.url,
                "title": hit.title,
                "source_domain": hit.source_domain,
                "mime_type": hit.mime_type,
                "concept_ids": hit.concept_ids or []
            }
            results.append((hit.chunk_id or hit.doc_id, hit.score, metadata))
        
        return results
    
    def _semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Ejecuta búsqueda semántica.
        
        Returns:
            Lista de (doc_id, score, metadata) con doc_ids mapeados desde chunks
        """
        # Generar embedding de query
        query_embedding = self.bert_adapter.encode([query])
        query_vector = query_embedding[0].numpy()
        
        # Buscar chunks similares
        chunk_results = self.embedding_store.search_similar(
            query_vector=query_vector,
            k=self.config.semantic_k,
            filters=filters,
            min_score=self.config.min_semantic_score
        )
        
        # Mapear chunk_id → doc_id y agregar metadatos
        results = []
        for chunk_result in chunk_results:
            metadata = {
                "chunk_id": chunk_result.chunk_id,
                "doc_id": chunk_result.doc_id,
                "chunk_text_preview": chunk_result.chunk_text_preview,
                "section_heading": chunk_result.section_heading,
                "source_domain": chunk_result.metadata.get("source_domain") if chunk_result.metadata else None,
                "seed_group": chunk_result.metadata.get("seed_group") if chunk_result.metadata else None,
            }
            results.append((chunk_result.chunk_id, chunk_result.score, metadata))
        
        return results
    
    def _fuse_results(
        self,
        lexical_results: List[Tuple[str, float, Dict[str, Any]]],
        semantic_results: List[Tuple[str, float, Dict[str, Any]]],
        k: int
    ) -> List[HybridSearchResult]:
        """
        Fusiona resultados léxicos y semánticos.
        
        Args:
            lexical_results: Resultados de búsqueda léxica
            semantic_results: Resultados de búsqueda semántica
            k: Número de resultados finales
            
        Returns:
            Resultados híbridos ordenados por score fusionado
        """
        if self.config.fusion_method == "rrf":
            return self._fuse_with_rrf(lexical_results, semantic_results, k)
        elif self.config.fusion_method == "weighted_sum":
            return self._fuse_with_weighted_sum(lexical_results, semantic_results, k)
        else:
            logger.warning(
                f"Método de fusión desconocido: {self.config.fusion_method}, "
                f"usando RRF"
            )
            return self._fuse_with_rrf(lexical_results, semantic_results, k)
    
    def _fuse_with_rrf(
        self,
        lexical_results: List[Tuple[str, float, Dict[str, Any]]],
        semantic_results: List[Tuple[str, float, Dict[str, Any]]],
        k: int
    ) -> List[HybridSearchResult]:
        """Fusión con Reciprocal Rank Fusion."""
        # Extraer rankings (ahora chunk_ids)
        lexical_ranking = [chunk_id for chunk_id, _, _ in lexical_results]
        semantic_ranking = [chunk_id for chunk_id, _, _ in semantic_results]
        
        lexical_meta = {chunk_id: (score, meta) for chunk_id, score, meta in lexical_results}
        
        # Para semántica
        semantic_meta: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        for chunk_id, score, meta in semantic_results:
            if chunk_id not in semantic_meta or score > semantic_meta[chunk_id][0]:
                semantic_meta[chunk_id] = (score, meta)
        
        # Aplicar RRF
        fused_scores = reciprocal_rank_fusion(
            rankings=[lexical_ranking, semantic_ranking],
            k=self.config.rrf_k
        )
        
        # Construir resultados híbridos
        results = []
        for chunk_id, rrf_score in fused_scores[:k]:
            lexical_score = lexical_meta.get(chunk_id, (0.0, {}))[0]
            semantic_score = semantic_meta.get(chunk_id, (0.0, {}))[0]
            
            # Combinar metadatos
            metadata = {}
            if chunk_id in lexical_meta:
                metadata.update(lexical_meta[chunk_id][1])
            if chunk_id in semantic_meta:
                metadata.update(semantic_meta[chunk_id][1])
            
            results.append(HybridSearchResult(
                doc_id=metadata.get("doc_id", chunk_id),
                chunk_id=chunk_id,
                score=rrf_score,
                lexical_score=lexical_score if lexical_score > 0 else None,
                vector_score=semantic_score if semantic_score > 0 else None,
                fusion_method="rrf",
                metadata=metadata
            ))
        
        return results
    
    def _fuse_with_weighted_sum(
        self,
        lexical_results: List[Tuple[str, float, Dict[str, Any]]],
        semantic_results: List[Tuple[str, float, Dict[str, Any]]],
        k: int
    ) -> List[HybridSearchResult]:
        """Fusión con suma ponderada de scores."""
        # Preparar datos
        lexical_ranking = [chunk_id for chunk_id, _, _ in lexical_results]
        lexical_scores = [score for _, score, _ in lexical_results]
        
        semantic_ranking = [chunk_id for chunk_id, _, _ in semantic_results]
        semantic_scores = [score for _, score, _ in semantic_results]
        
        lexical_meta = {chunk_id: (score, meta) for chunk_id, score, meta in lexical_results}
        
        semantic_meta: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        for chunk_id, score, meta in semantic_results:
            if chunk_id not in semantic_meta or score > semantic_meta[chunk_id][0]:
                semantic_meta[chunk_id] = (score, meta)
        
        # Aplicar weighted sum
        fused_scores = weighted_sum_fusion(
            rankings_with_scores=[
                (lexical_ranking, lexical_scores),
                (semantic_ranking, semantic_scores)
            ],
            weights=[self.config.lexical_weight, self.config.semantic_weight],
            normalize=self.config.normalize_scores
        )
        
        # Construir resultados híbridos
        results = []
        for chunk_id, combined_score in fused_scores[:k]:
            lexical_score = lexical_meta.get(chunk_id, (0.0, {}))[0]
            semantic_score = semantic_meta.get(chunk_id, (0.0, {}))[0]
            
            # Combinar metadatos
            metadata = {}
            if chunk_id in lexical_meta:
                metadata.update(lexical_meta[chunk_id][1])
            if chunk_id in semantic_meta:
                metadata.update(semantic_meta[chunk_id][1])
            
            results.append(HybridSearchResult(
                doc_id=metadata.get("doc_id", chunk_id),
                chunk_id=chunk_id,
                score=combined_score,
                lexical_score=lexical_score if lexical_score > 0 else None,
                vector_score=semantic_score if semantic_score > 0 else None,
                fusion_method="weighted_sum",
                metadata=metadata
            ))
        
        return results
