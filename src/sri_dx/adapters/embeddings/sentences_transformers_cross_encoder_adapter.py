"""Cross-encoder adapter using sentence-transformers."""

import logging
from typing import Optional

from sentence_transformers import CrossEncoder

from sri_dx.core.ports.search.cross_encoder_port import CrossEncoderPort
from sri_dx.modules.ranking.schemas.cross_encoder_config import CrossEncoderConfig
from sri_dx.modules.ranking.schemas.rerank_schemas import (
    RerankRequest,
    RerankResponse,
    RerankResult,
    EmptyResultsError,
    MissingContentError,
    RerankingError,
)

logger = logging.getLogger(__name__)


class SentenceTransformersCrossEncoderAdapter(CrossEncoderPort):
    """CrossEncoderPort implementation using sentence-transformers."""

    def __init__(self, config: CrossEncoderConfig):
        self._config = config
        self._model: Optional[CrossEncoder] = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            logger.info("Loading cross-encoder: %s", self._config.model_name)
            self._model = CrossEncoder(
                self._config.model_name,
                device=self._config.device,
                max_length=self._config.max_length
            )
            logger.info("Cross-encoder loaded on %s", self._config.device)
        except Exception as e:
            logger.error("Failed to load cross-encoder: %s", e)
            raise RerankingError(f"Could not load model: {e}") from e

    def rerank(self, request: RerankRequest) -> RerankResponse:
        # Validación
        if not request.results:
            raise EmptyResultsError("Results list cannot be empty")

        logger.info(
            "Reranking %d results for query: '%s...'",
            len(request.results), request.query[:50]
        )

        try:
            pairs, valid_results = self._prepare_pairs(request)
        except KeyError as e:
            raise MissingContentError(
                f"Field '{request.content_field}' not found in metadata"
            ) from e

        try:
            scores = self._model.predict(
                pairs,
                batch_size=self._config.batch_size,
                show_progress_bar=False
            )
        except Exception as e:
            logger.error("Cross-encoder inference error: %s", e)
            raise RerankingError(f"Model inference failed: {e}") from e

        rerank_results = []
        for i, (result, score) in enumerate(zip(valid_results, scores)):
            rerank_results.append(
                RerankResult(
                    original_result=result,
                    rerank_score=float(score),
                    original_position=i,
                )
            )

        rerank_results.sort(key=lambda x: x.rerank_score, reverse=True)

        top_results = rerank_results[:request.top_k]
        for new_pos, result in enumerate(top_results):
            object.__setattr__(result, "new_position", new_pos)

        if self._config.score_threshold is not None:
            top_results = [
                r for r in top_results
                if r.rerank_score >= self._config.score_threshold
            ]
            logger.debug(
                "Score threshold filter (%.2f): %d results remaining",
                self._config.score_threshold, len(top_results)
            )

        logger.info("Reranking complete: %d final results", len(top_results))

        return RerankResponse(
            query=request.query,
            ranked_results=top_results,
            model_name=self._config.model_name,
            model_version=self._config.model_version
        )

    def _prepare_pairs(self, request: RerankRequest) -> tuple[list[tuple[str, str]], list]:
        pairs = []
        valid_results = []

        for result in request.results:
            if not result.metadata or request.content_field not in result.metadata:
                logger.warning(
                    "Doc %s: field '%s' not found in metadata, skipping",
                    result.doc_id, request.content_field
                )
                continue

            content = result.metadata[request.content_field]
            if not isinstance(content, str) or not content.strip():
                logger.warning("Doc %s: empty content, skipping", result.doc_id)
                continue

            pairs.append((request.query, content))
            valid_results.append(result)

        if not pairs:
            raise MissingContentError(
                f"Could not extract content from any result. "
                f"Ensure field '{request.content_field}' exists in metadata with valid text."
            )

        logger.debug("Prepared %d pairs for reranking", len(pairs))
        return pairs, valid_results

    def is_available(self) -> bool:
        return self._model is not None
