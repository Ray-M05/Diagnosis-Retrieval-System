"""
Two-stage retrieval pipeline: hybrid search (BM25 + kNN) followed by
cross-encoder reranking. Optionally performs NER on reranked chunks and
aggregates results by disease entity.
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
from sri_dx.core.ports.feedback.feedback_store_port import FeedbackStorePort
from sri_dx.core.schemas.search.disease_result import DiseaseResult
from sri_dx.modules.expansion import SimplePseudoRelevanceFeedback, SynonymExpander

logger = logging.getLogger(__name__)


@dataclass
class TwoStageRetrievalConfig:
    """Configuration for the two-stage retrieval pipeline."""

    # Stage 1: Hybrid Search
    hybrid_candidates: int = 100

    # Stage 2: Reranking
    final_results: int = 10

    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    device: str = "cpu"
    batch_size: int = 32
    score_threshold: Optional[float] = None

    content_field: str = "content"

    # Disease aggregation
    min_ner_score: float = 0.5
    max_diseases: int = 10
    positioned_results: int = 10
    enable_synonym_expansion: bool = True
    enable_prf: bool = False


@dataclass
class RetrievalResult:
    """Final pipeline result with enriched scoring information."""
    
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
    """Two-stage retrieval pipeline: hybrid search → cross-encoder reranking."""
    
    hybrid_search: SearchHybridUseCase
    config: TwoStageRetrievalConfig = field(default_factory=TwoStageRetrievalConfig)
    cross_encoder: Optional[SentenceTransformersCrossEncoderAdapter] = None
    disease_aggregator: Optional[DiseaseAggregator] = None
    positioning_service: Optional[Any] = None
    synonym_expander: Optional[SynonymExpander] = None
    prf_expander: Optional[SimplePseudoRelevanceFeedback] = None
    feedback_store: Optional[FeedbackStorePort] = None
    
    def __post_init__(self):
        if self.cross_encoder is None:
            logger.info("Initializing cross-encoder...")
            ce_config = CrossEncoderConfig(
                model_name=self.config.cross_encoder_model,
                device=self.config.device,
                batch_size=self.config.batch_size,
                top_k=self.config.final_results,
                score_threshold=self.config.score_threshold,
            )
            self.cross_encoder = SentenceTransformersCrossEncoderAdapter(ce_config)
            logger.info("Cross-encoder initialized")
        if self.synonym_expander is None:
            self.synonym_expander = SynonymExpander()
        if self.prf_expander is None:
            self.prf_expander = SimplePseudoRelevanceFeedback()
    
    def search(
        self,
        query: str,
        hybrid_candidates: Optional[int] = None,
        final_results: Optional[int] = None,
        session_id: Optional[str] = None,
        excluded_chunk_ids: Optional[set[str]] = None,
    ) -> List[RetrievalResult]:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        k_candidates = hybrid_candidates or self.config.hybrid_candidates
        k_final = final_results or self.config.final_results
        
        logger.info("=== Two-stage search: '%s...' ===", query[:50])
        logger.info("Stage 1: %d candidates | Stage 2: %d final", k_candidates, k_final)

        retrieval_query = query
        if self.config.enable_synonym_expansion and self.synonym_expander is not None:
            retrieval_query = self.synonym_expander.expand(query)

        if self.feedback_store is not None and retrieval_query != query:
            self.feedback_store.save_query_expansion(
                session_id=session_id,
                original_query=query,
                expanded_query=retrieval_query,
                strategy="synonym",
            )
        
        logger.info("Stage 1: Running hybrid search...")
        hybrid_results = self.hybrid_search.search(query=retrieval_query, k=k_candidates)
        
        if not hybrid_results:
            logger.warning("Hybrid search returned no results")
            return []

        if self.config.enable_prf and self.prf_expander is not None:
            top_chunks = [
                str((r.metadata or {}).get(self.config.content_field) or "")
                for r in hybrid_results[: self.prf_expander.top_docs]
            ]
            prf_query = self.prf_expander.expand(retrieval_query, top_chunks)
            if prf_query != retrieval_query:
                if self.feedback_store is not None:
                    self.feedback_store.save_query_expansion(
                        session_id=session_id,
                        original_query=query,
                        expanded_query=prf_query,
                        strategy="pseudo_relevance",
                    )
                hybrid_results = self.hybrid_search.search(query=prf_query, k=k_candidates)

        if excluded_chunk_ids:
            hybrid_results = [
                result for result in hybrid_results
                if result.chunk_id not in excluded_chunk_ids
            ]
            if not hybrid_results:
                logger.warning("All candidates were filtered by negative feedback")
                return []

        logger.info("Stage 1 complete: %d candidates", len(hybrid_results))

        logger.info("Stage 2: Running cross-encoder reranking...")
        rerank_request = RerankRequest(
            query=query,
            results=hybrid_results,
            top_k=k_final,
            content_field=self.config.content_field,
        )
        
        rerank_response = self.cross_encoder.rerank(rerank_request)
        logger.info("Stage 2 complete: %d final results", len(rerank_response.ranked_results))

        final_results = self._enrich_results(rerank_response.ranked_results)

        logger.info("Pipeline complete: %d results", len(final_results))
        return final_results
    
    def _enrich_results(self, rerank_results: List[RerankResult]) -> List[RetrievalResult]:
        enriched = []

        for rr in rerank_results:
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
        session_id: Optional[str] = None,
        excluded_chunk_ids: Optional[set[str]] = None,
    ) -> List[DiseaseResult]:
        """Three-stage search: hybrid → reranking → on-demand NER → disease aggregation."""
        # NER needs enough chunks to find disease entities — always rerank at
        # least 20 chunks regardless of the requested number of final diseases.
        ner_k = max(final_results or self.config.final_results, 20)
        chunk_results = self.search(
            query,
            hybrid_candidates,
            ner_k,
            session_id=session_id,
            excluded_chunk_ids=excluded_chunk_ids,
        )

        if not chunk_results:
            logger.warning("No chunks available for disease aggregation")
            return []

        self._apply_ner_to_results(chunk_results)

        if self.disease_aggregator is None:
            self.disease_aggregator = DiseaseAggregator(
                DiseaseAggregatorConfig(
                    min_ner_score=self.config.min_ner_score,
                    max_diseases=self.config.max_diseases,
                )
            )

        diseases = self.disease_aggregator.aggregate(chunk_results)
        logger.info("Aggregation complete: %d diseases identified", len(diseases))
        # Truncate to the originally requested k (not ner_k)
        requested_k = final_results or self.config.final_results
        return diseases[:requested_k]

    def search_positioned(
        self,
        query: str,
        hybrid_candidates: Optional[int] = None,
        final_results: Optional[int] = None,
        positioned_results: Optional[int] = None,
    ) -> list:
        """Positioned search: hybrid → reranking → on-demand NER → clinical positioning."""
        chunk_results = self.search(query, hybrid_candidates, final_results)

        if not chunk_results:
            logger.warning("No chunks available for clinical positioning")
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
        logger.info("Positioning complete: %d conditions", len(positioned))
        return positioned

    def _apply_ner_to_results(self, results: List[RetrievalResult]) -> None:
        """Runs batch NER on reranked chunks and injects ner_entities into each result's metadata."""
        try:
            from sri_dx.adapters.embeddings.biomedical_ner_adapter import BiomedicalNERAdapter
        except ImportError:
            logger.warning("BiomedicalNERAdapter not available. NER disabled.")
            return

        texts = []
        for r in results:
            text = (r.content or r.metadata.get("content", "") or "").strip()
            texts.append(text)

        if not any(texts):
            return

        ner_adapter = BiomedicalNERAdapter.get_instance()
        logger.info("Running on-demand NER on %d reranked chunks...", len(texts))
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
        print("\n" + "=" * 80)
        print(f"IDENTIFIED DISEASES: {len(diseases)}")
        print("=" * 80)

        for disease in diseases:
            print("\n" + str(disease))

        print("\n" + "=" * 80)

    def print_positioned_results(self, positioned: list) -> None:
        print("\n" + "=" * 80)
        print(f"POSITIONED CONDITIONS: {len(positioned)}")
        print("=" * 80)

        for result in positioned:
            print(
                f"\n#{result.rank} - {result.disease_name_display} "
                f"({result.relevance_label}, score={result.final_score:.4f})"
            )
            if result.matched_symptoms:
                print(f"  Matches: {', '.join(result.matched_symptoms)}")
            if result.source_domains:
                print(f"  Sources: {', '.join(result.source_domains[:3])}")
            for explanation in result.explanation:
                print(f"  - {explanation}")
            for evidence in result.evidences[:3]:
                print(
                    f"    Evidencia chunk={evidence.chunk_id}, "
                    f"ce={evidence.cross_encoder_score}, url={evidence.url}"
                )

        print("\n" + "=" * 80)

    def print_results(self, results: List[RetrievalResult]) -> None:
        print("\n" + "=" * 80)
        print(f"FINAL RESULTS: {len(results)} documents")
        print("=" * 80)
        
        for result in results:
            print("\n" + str(result))
        
        print("\n" + "=" * 80)


