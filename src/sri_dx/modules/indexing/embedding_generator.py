# modules/indexing/embedding_generator.py
"""Generador de embeddings para chunks usando Bio_ClinicalBERT."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument
from sri_dx.core.schemas.indexing.embedding_document import EmbeddingDocument

if TYPE_CHECKING:
    from sri_dx.adapters.embeddings.clinical_bert_adapter import ClinicalBERTAdapter

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingGeneratorConfig:
    """Configuración del generador de embeddings."""
    
    model_name: str = "Bio_ClinicalBERT"
    model_version: str = "1.0"
    embedding_dim: int = 768
    batch_size: int = 32
    text_preview_length: int = 200
    normalize_vectors: bool = True


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
        Inicializa el generador.
        
        Args:
            config: Configuración del generador
            bert_adapter: Adaptador BERT (si None, crea uno)
        """
        self.config = config or EmbeddingGeneratorConfig()
        self._bert_adapter = bert_adapter
    
    @property
    def bert_adapter(self) -> "ClinicalBERTAdapter":
        """Acceso lazy al adaptador BERT."""
        if self._bert_adapter is None:
            from sri_dx.adapters.embeddings.clinical_bert_adapter import (
                ClinicalBERTAdapter,
                ClinicalBERTConfig,
            )
            bert_config = ClinicalBERTConfig(
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_vectors,
            )
            self._bert_adapter = ClinicalBERTAdapter.get_instance(bert_config)
        return self._bert_adapter
    
    def generate_embeddings(
        self, 
        chunks: List[ChunkDocument]
    ) -> List[EmbeddingDocument]:
        """
        Genera embeddings para una lista de chunks.
        
        Args:
            chunks: Lista de chunks a procesar
            
        Returns:
            Lista de EmbeddingDocument con vectores
        """
        if not chunks:
            return []
        
        # Extraer textos
        texts = [self._get_chunk_text(chunk) for chunk in chunks]
        
        # Generar embeddings en batch
        logger.debug(f"Generando embeddings para {len(texts)} chunks...")
        vectors = self.bert_adapter.encode(texts)
        
        # Crear documentos de embedding
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
        
        logger.debug(f"Generados {len(embeddings)} embeddings")
        return embeddings
    
    def _get_chunk_text(self, chunk: ChunkDocument) -> str:
        """Extrae el texto del chunk para embedding."""
        text = chunk.chunk_text or ""
        
        # Opcionalmente agregar contexto (heading)
        if chunk.section_heading:
            text = f"{chunk.section_heading}: {text}"
        
        return text.strip()
    
    def _get_text_preview(self, chunk: ChunkDocument) -> str:
        """Genera preview del texto para metadata."""
        text = chunk.chunk_text or ""
        max_len = self.config.text_preview_length
        
        if len(text) <= max_len:
            return text
        
        return text[:max_len].rsplit(" ", 1)[0] + "..."
    
    def _generate_embedding_id(self, chunk: ChunkDocument) -> str:
        """Genera ID único para el embedding."""
        # Combinar chunk_id + model para permitir múltiples modelos
        unique_str = f"{chunk.chunk_id}:{self.config.model_name}:{self.config.model_version}"
        hash_suffix = hashlib.sha256(unique_str.encode()).hexdigest()[:8]
        return f"emb_{chunk.chunk_id}_{hash_suffix}"
    
    def get_embedding_dim(self) -> int:
        """Retorna la dimensión de los embeddings."""
        return self.config.embedding_dim
