# modules/indexing/embedding_generator.py
"""Generador de embeddings para chunks usando Bio_ClinicalBERT."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument
from sri_dx.core.schemas.indexing.embedding_document import EmbeddingDocument
from .schemas.embedding_config import EmbeddingGeneratorConfig

if TYPE_CHECKING:
    from sri_dx.adapters.embeddings.clinical_bert_adapter import ClinicalBERTAdapter

logger = logging.getLogger(__name__)


# EmbeddingGeneratorConfig is provided by modules.indexing.schemas.embedding_config


class EmbeddingGenerator:
    """
    Genera embeddings para chunks usando Bio_ClinicalBERT.
    
    Responsabilidades:
    - Extraer texto de chunks
    - Generar embeddings en batch
    - Crear EmbeddingDocument con metadata
    """
    
    def __init__(
        self,
        config: Optional[EmbeddingGeneratorConfig] = None,
        bert_adapter: Optional["ClinicalBERTAdapter"] = None
    ):
        """
        Initialises the generator.

        Args:
            config: Generator configuration
            bert_adapter: BERT adapter (if None, one is created)
        """
        self.config = config or EmbeddingGeneratorConfig()
        self._bert_adapter = bert_adapter
    
    @property
    def bert_adapter(self) -> "ClinicalBERTAdapter":
        """Lazy access to the BERT adapter."""
        if self._bert_adapter is None:
            from sri_dx.adapters.embeddings.clinical_bert_adapter import (
                ClinicalBERTAdapter,
                ClinicalBERTConfig,
            )
            bert_config = ClinicalBERTConfig(
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_vectors,
                device=self.config.device,
            )
            self._bert_adapter = ClinicalBERTAdapter.get_instance(bert_config)
        return self._bert_adapter
    
    def generate_embeddings(
        self, 
        chunks: List[ChunkDocument]
    ) -> List[EmbeddingDocument]:
        """
        Generates embeddings for a list of chunks.

        Args:
            chunks: List of chunks to process

        Returns:
            List of EmbeddingDocument with vectors
        """
        if not chunks:
            return []

        texts = [self._get_chunk_text(chunk) for chunk in chunks]

        logger.debug(f"Generating embeddings for {len(texts)} chunks...")
        vectors = self.bert_adapter.encode(texts)

        embeddings = []
        now = datetime.now(timezone.utc).isoformat()
        
        for i, chunk in enumerate(chunks):
            vector = vectors[i].tolist()
            
            embedding_doc = EmbeddingDocument(
                embedding_id=self._generate_embedding_id(chunk),
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                vector=vector,
                model_name=self.config.model_name,
                model_version=self.config.model_version,
                embedding_dim=self.config.embedding_dim,
                similarity_metric="cosine",
                chunk_text_preview=self._get_text_preview(chunk),
                chunk_index=chunk.chunk_index,
                section_heading=chunk.section_heading,
                seed_group=chunk.seed_group,
                source_domain=chunk.source_domain,
                concept_ids=chunk.concept_ids,
                created_at=now,
                chunk_hash=chunk.chunk_hash,
            )
            embeddings.append(embedding_doc)
        
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def _get_chunk_text(self, chunk: ChunkDocument) -> str:
        """Extracts chunk text for embedding."""
        text = chunk.chunk_text or ""

        # Optionally prepend section heading as context
        if chunk.section_heading:
            text = f"{chunk.section_heading}: {text}"
        
        return text.strip()
    
    def _get_text_preview(self, chunk: ChunkDocument) -> str:
        """Generates a text preview for metadata."""
        text = chunk.chunk_text or ""
        max_len = self.config.text_preview_length
        
        if len(text) <= max_len:
            return text
        
        return text[:max_len].rsplit(" ", 1)[0] + "..."
    
    def _generate_embedding_id(self, chunk: ChunkDocument) -> str:
        """Generates a unique ID for the embedding."""
        # Combine chunk_id + model to support multiple models
        unique_str = f"{chunk.chunk_id}:{self.config.model_name}:{self.config.model_version}"
        hash_suffix = hashlib.sha256(unique_str.encode()).hexdigest()[:8]
        return f"emb_{chunk.chunk_id}_{hash_suffix}"
    
    def get_embedding_dim(self) -> int:
        """Returns the embedding dimension."""
        return self.config.embedding_dim
