# modules/chunking/semantic_chunker.py
"""
Chunking Semántico — segunda estrategia cuando una sección supera max_chars.

Algoritmo:
1. Divide la sección en oraciones
2. Genera embeddings con un modelo ligero (all-MiniLM-L6-v2, 384 dims)
3. Calcula similitud coseno entre oraciones consecutivas
4. Crea breakpoints donde la similitud cae bajo el umbral
5. Agrupa oraciones entre breakpoints en chunks

El modelo MiniLM es ~6x más rápido que Bio_ClinicalBERT y suficiente para
detectar cambios temáticos. Los embeddings finales de calidad los genera F4
(Bio_ClinicalBERT sobre los chunks completos).
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional, Tuple

from sri_dx.core.ports.indexing.chunker_port import ChunkerPort
from sri_dx.core.schemas.indexing.chunk_config import ChunkingConfig
from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument
from .schemas.chunking_config import SemanticChunkingConfig
from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument

logger = logging.getLogger(__name__)

# Patrón para dividir en oraciones (texto médico en inglés/español)
_SENTENCE_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z])|'   # Punto/!/? + espacio + mayúscula
    r'(?<=\n)\s*(?=\S)|'          # Salto de línea
    r'(?<=\d\.)\s+(?=[A-Z])'      # "1. Texto"
)


class SemanticChunker(ChunkerPort):
    """
    Divide secciones largas en chunks semánticamente coherentes.

    Singleton: comparte el modelo MiniLM entre todos los documentos del pipeline.
    Se instancia una sola vez y se reutiliza en todas las llamadas a split_text().
    """

    _instance: Optional["SemanticChunker"] = None
    _model = None  # sentence_transformers.SentenceTransformer

    def __init__(self, config: Optional[SemanticChunkingConfig] = None):
        self.config = config or SemanticChunkingConfig()

    @classmethod
    def get_instance(cls, config: Optional[SemanticChunkingConfig] = None) -> "SemanticChunker":
        """Singleton: carga el modelo MiniLM una sola vez."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @property
    def model(self):
        """Carga lazy del modelo MiniLM."""
        if SemanticChunker._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Cargando modelo SemanticChunker: %s", self.config.model_name)
            SemanticChunker._model = SentenceTransformer(self.config.model_name)
            # Usar GPU si está disponible
            try:
                import torch
                if torch.cuda.is_available():
                    SemanticChunker._model = SemanticChunker._model.to("cuda")
                    logger.info("SemanticChunker: modelo en GPU")
            except Exception:
                pass
            logger.info("SemanticChunker listo.")
        return SemanticChunker._model

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def split_text(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Divide un texto largo en fragmentos semánticamente coherentes.

        Args:
            text: Texto de una sección que superó max_chars.

        Returns:
            Lista de (start_char, end_char, chunk_text) relativos al texto original.
        """
        if not text.strip():
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        # Pocos oraciones → un solo chunk
        if len(sentences) <= self.config.min_sentences_per_chunk:
            return [(0, len(text), text)]

        if self.config.combine_short_sentences:
            sentences = self._merge_short_sentences(sentences)

        # Embeddings en un solo batch (MiniLM es rápido)
        embeddings = self.model.encode(
            sentences,
            batch_size=self.config.batch_size,
            show_progress_bar=False,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )

        breakpoints = self._find_breakpoints(embeddings, sentences)
        return self._build_spans(text, sentences, breakpoints)

    def chunk_document(
        self,
        document: AcquiredDocument,
        config: Optional[ChunkingConfig] = None,
    ) -> List[ChunkDocument]:
        """Implementación de ChunkerPort — no usada en el pipeline principal."""
        raise NotImplementedError(
            "SemanticChunker se usa via split_text() en chunking.py, no directamente."
        )

    def chunk_batch(self, documents, config=None):
        raise NotImplementedError

    def chunk_strategy(self) -> str:
        return "semantic_minilm"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> List[str]:
        """Divide texto en oraciones, normalizando whitespace."""
        text = re.sub(r'\s+', ' ', text).strip()
        sentences = _SENTENCE_RE.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Fallback: si solo hay una "oración" muy larga, dividir por puntos
        if len(sentences) == 1 and len(text) > 500:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _merge_short_sentences(self, sentences: List[str]) -> List[str]:
        """Fusiona oraciones cortas con la siguiente para evitar embeddings triviales."""
        threshold = self.config.short_sentence_threshold
        result: List[str] = []
        buf = ""

        for s in sentences:
            if len(s) < threshold:
                buf = (buf + " " + s).strip() if buf else s
            else:
                if buf:
                    result.append((buf + " " + s).strip())
                    buf = ""
                else:
                    result.append(s)

        if buf:
            if result:
                result[-1] = (result[-1] + " " + buf).strip()
            else:
                result.append(buf)

        return result

    def _find_breakpoints(self, embeddings, sentences: List[str]) -> List[int]:
        """
        Retorna índices de inicio de cada chunk.
        Un breakpoint ocurre cuando la similitud coseno entre oraciones
        consecutivas cae bajo el umbral O se alcanza max_sentences_per_chunk.
        """
        import torch

        n = len(sentences)
        if n <= 1:
            return [0]

        # Similitud coseno entre oraciones consecutivas (embeddings ya normalizados)
        sims = torch.sum(embeddings[:-1] * embeddings[1:], dim=1).tolist()

        breakpoints = [0]
        chunk_size = 1

        for i, sim in enumerate(sims):
            chunk_size += 1
            force_break = chunk_size >= self.config.max_sentences_per_chunk
            semantic_break = sim < self.config.similarity_threshold

            if (force_break or semantic_break) and chunk_size > self.config.min_sentences_per_chunk:
                breakpoints.append(i + 1)
                chunk_size = 0

        return breakpoints

    def _build_spans(
        self, original_text: str, sentences: List[str], breakpoints: List[int]
    ) -> List[Tuple[int, int, str]]:
        """
        Convierte grupos de oraciones en spans (start, end, text) sobre el texto original.
        Fusiona chunks que queden bajo min_chunk_chars.
        """
        breakpoints = breakpoints + [len(sentences)]
        groups: List[str] = []

        for i in range(len(breakpoints) - 1):
            chunk_sentences = sentences[breakpoints[i]: breakpoints[i + 1]]
            chunk_text = " ".join(chunk_sentences)

            # Fusionar con anterior si es demasiado corto
            if len(chunk_text) < self.config.min_chunk_chars and groups:
                groups[-1] = groups[-1] + " " + chunk_text
            else:
                groups.append(chunk_text)

        # Construir spans buscando cada chunk en el texto original
        spans: List[Tuple[int, int, str]] = []
        cursor = 0
        for chunk_text in groups:
            # Buscar el comienzo del chunk en el texto original
            probe = chunk_text[:40] if len(chunk_text) >= 40 else chunk_text
            pos = original_text.find(probe, cursor)
            if pos == -1:
                pos = cursor  # fallback
            end = pos + len(chunk_text)
            spans.append((pos, end, chunk_text))
            cursor = pos + len(chunk_text)

        return spans
