"""Adapter para cross-encoder usando sentence-transformers."""

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
    """
    Implementación de CrossEncoderPort usando sentence-transformers.
    
    Reordena resultados de búsqueda híbrida evaluando directamente
    la relevancia entre query y contenido del documento.
    
    Modelos recomendados:
        - cross-encoder/ms-marco-MiniLM-L-6-v2 (rápido, inglés)
        - cross-encoder/ms-marco-MiniLM-L-12-v2 (más preciso, inglés)
        - cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (multilingüe)
    
    Ejemplo:
        >>> config = CrossEncoderConfig(
        ...     model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        ...     device="cpu",
        ...     batch_size=32
        ... )
        >>> adapter = SentenceTransformersCrossEncoderAdapter(config)
        >>> response = adapter.rerank(request)
    """

    def __init__(self, config: CrossEncoderConfig):
        """
        Inicializa el adapter con configuración.
        
        Args:
            config: Configuración del cross-encoder
        """
        self._config = config
        self._model: Optional[CrossEncoder] = None
        self._load_model()

    def _load_model(self) -> None:
        """Carga el modelo de cross-encoder."""
        try:
            logger.info(f"Cargando cross-encoder: {self._config.model_name}")
            self._model = CrossEncoder(
                self._config.model_name,
                device=self._config.device,
                max_length=self._config.max_length
            )
            logger.info(f"Cross-encoder cargado exitosamente en {self._config.device}")
        except Exception as e:
            logger.error(f"Error cargando cross-encoder: {e}")
            raise RerankingError(f"No se pudo cargar el modelo: {e}") from e

    def rerank(self, request: RerankRequest) -> RerankResponse:
        """
        Reordena resultados de búsqueda híbrida.
        
        Proceso:
        1. Valida que haya resultados
        2. Extrae contenido de cada resultado
        3. Crea pares (query, contenido)
        4. Ejecuta inferencia del cross-encoder
        5. Ordena por score y aplica top_k
        
        Args:
            request: Request con query y resultados a rerankear
        
        Returns:
            Response con resultados reordenados
        
        Raises:
            EmptyResultsError: Si no hay resultados para rerankear
            MissingContentError: Si falta contenido en algún resultado
            RerankingError: Si falla la inferencia
        """
        # Validación
        if not request.results:
            raise EmptyResultsError("La lista de resultados no puede estar vacía")

        logger.info(
            f"Reranking {len(request.results)} resultados para query: "
            f"'{request.query[:50]}...'"
        )

        # Extraer contenido y crear pares
        try:
            pairs, valid_results = self._prepare_pairs(request)
        except KeyError as e:
            raise MissingContentError(
                f"Campo '{request.content_field}' no encontrado en metadata"
            ) from e

        # Inferencia
        try:
            scores = self._model.predict(
                pairs,
                batch_size=self._config.batch_size,
                show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"Error en inferencia del cross-encoder: {e}")
            raise RerankingError(f"Falló la inferencia del modelo: {e}") from e

        # Construir resultados rerankeados
        rerank_results = []
        for i, (result, score) in enumerate(zip(valid_results, scores)):
            rerank_results.append(
                RerankResult(
                    original_result=result,
                    rerank_score=float(score),
                    original_position=i,
                )
            )

        # Ordenar por score descendente
        rerank_results.sort(key=lambda x: x.rerank_score, reverse=True)

        # Aplicar top_k y asignar nuevas posiciones
        top_results = rerank_results[:request.top_k]
        for new_pos, result in enumerate(top_results):
            # Como RerankResult es frozen, creamos uno nuevo con la posición
            object.__setattr__(result, "new_position", new_pos)

        # Aplicar filtro de score si está configurado
        if self._config.score_threshold is not None:
            top_results = [
                r for r in top_results
                if r.rerank_score >= self._config.score_threshold
            ]
            logger.debug(
                f"Filtro por score_threshold={self._config.score_threshold}: "
                f"{len(top_results)} resultados"
            )

        logger.info(f"Reranking completado: {len(top_results)} resultados finales")

        return RerankResponse(
            query=request.query,
            ranked_results=top_results,
            model_name=self._config.model_name,
            model_version=self._config.model_version
        )

    def _prepare_pairs(self, request: RerankRequest) -> tuple[list[tuple[str, str]], list]:
        """
        Prepara pares (query, content) para inferencia.
        
        Args:
            request: Request con resultados
        
        Returns:
            Tupla de (pares, resultados_válidos)
        
        Raises:
            MissingContentError: Si falta contenido en metadata
        """
        pairs = []
        valid_results = []

        for result in request.results:
            # Extraer contenido de metadata
            if not result.metadata or request.content_field not in result.metadata:
                logger.warning(
                    f"Doc {result.doc_id}: campo '{request.content_field}' "
                    f"no encontrado en metadata, se omite"
                )
                continue

            content = result.metadata[request.content_field]
            if not isinstance(content, str) or not content.strip():
                logger.warning(f"Doc {result.doc_id}: contenido vacío, se omite")
                continue

            pairs.append((request.query, content))
            valid_results.append(result)

        if not pairs:
            raise MissingContentError(
                f"No se pudo extraer contenido de ningún resultado. "
                f"Verifica que el campo '{request.content_field}' exista "
                f"en metadata y contenga texto válido."
            )

        logger.debug(f"Preparados {len(pairs)} pares para reranking")
        return pairs, valid_results

    def is_available(self) -> bool:
        """
        Verifica si el modelo está cargado.
        
        Returns:
            True si el modelo está listo, False en caso contrario
        """
        return self._model is not None
