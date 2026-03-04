# modules/chunking/semantic_chunker.py
"""
Chunking Semántico usando Bio_ClinicalBERT.

Esta implementación divide documentos en chunks basándose en la
similitud semántica entre oraciones consecutivas, en lugar de
usar un tamaño fijo de caracteres/tokens.

Algoritmo:
1. Divide el texto en oraciones
2. Genera embeddings para cada oración usando Bio_ClinicalBERT
3. Calcula similitud coseno entre oraciones consecutivas
4. Detecta "puntos de quiebre" donde la similitud cae significativamente
5. Agrupa oraciones entre puntos de quiebre en chunks

Ventajas:
- Chunks semánticamente coherentes
- Ideal para textos médicos con secciones temáticas
- Mejor para búsqueda semántica posterior
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, TYPE_CHECKING

from sri_dx.core.ports.indexing.chunker_port import ChunkerPort
from sri_dx.core.schemas.indexing.chunk_config import ChunkingConfig
from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument
from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunkingConfig:
    """Configuración específica para chunking semántico."""
    
    similarity_threshold: float = 0.5
    """Umbral de similitud. Debajo de este valor se crea un nuevo chunk."""
    
    min_sentences_per_chunk: int = 2
    """Mínimo de oraciones por chunk."""
    
    max_sentences_per_chunk: int = 15
    """Máximo de oraciones por chunk (fuerza split si se excede)."""
    
    min_chunk_chars: int = 100
    """Chunks más pequeños se fusionan con el anterior."""
    
    max_chunk_chars: int = 2000
    """Chunks más grandes se fuerzan a dividir."""
    
    combine_short_sentences: bool = True
    """Si True, combina oraciones muy cortas antes del análisis."""
    
    short_sentence_threshold: int = 20
    """Oraciones con menos caracteres se consideran 'cortas'."""
    
    batch_size: int = 32
    """Batch size para encoding de embeddings."""


# Patrones para dividir en oraciones (considerando texto médico)
SENTENCE_PATTERN = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z])|'  # Punto/!/? seguido de espacio y mayúscula
    r'(?<=\n)\s*(?=\S)|'        # Salto de línea
    r'(?<=:)\s*(?=\n)|'         # Dos puntos antes de newline
    r'(?<=\d\.)\s+(?=[A-Z])'    # Número. seguido de mayúscula (listas)
)


class SemanticChunker(ChunkerPort):
    """
    Implementación de ChunkerPort usando chunking semántico.
    
    Usa Bio_ClinicalBERT para generar embeddings y detectar
    cambios temáticos en el texto.
    """
    
    def __init__(
        self, 
        semantic_config: Optional[SemanticChunkingConfig] = None,
        bert_adapter: Optional["ClinicalBERTAdapter"] = None
    ):
        """
        Inicializa el chunker semántico.
        
        Args:
            semantic_config: Configuración de chunking semántico
            bert_adapter: Adaptador de Bio_ClinicalBERT (si None, crea uno)
        """
        self.semantic_config = semantic_config or SemanticChunkingConfig()
        self._bert_adapter = bert_adapter
    
    @property
    def bert_adapter(self) -> "ClinicalBERTAdapter":
        """Acceso lazy al adaptador BERT."""
        if self._bert_adapter is None:
            from sri_dx.adapters.embeddings.clinical_bert_adapter import (
                ClinicalBERTAdapter
            )
            self._bert_adapter = ClinicalBERTAdapter.get_instance()
        return self._bert_adapter
    
    def chunk_document(
        self, 
        document: AcquiredDocument, 
        config: Optional[ChunkingConfig] = None
    ) -> List[ChunkDocument]:
        """
        Divide un documento en chunks semánticamente coherentes.
        
        Args:
            document: Documento a dividir
            config: Configuración base (se combina con semantic_config)
            
        Returns:
            Lista de chunks con metadatos
        """
        # Extraer texto completo del documento
        full_text = self._extract_full_text(document)
        
        if not full_text.strip():
            return []
        
        # Dividir en oraciones
        sentences = self._split_into_sentences(full_text)
        
        if len(sentences) == 0:
            return []
        
        # Si muy pocas oraciones, retornar como un solo chunk
        if len(sentences) <= self.semantic_config.min_sentences_per_chunk:
            return [self._create_chunk(
                document=document,
                text=full_text,
                chunk_index=0,
                start_char=0,
                end_char=len(full_text)
            )]
        
        # Combinar oraciones muy cortas si está configurado
        if self.semantic_config.combine_short_sentences:
            sentences = self._combine_short_sentences(sentences)
        
        # Generar embeddings para todas las oraciones
        embeddings = self.bert_adapter.encode(
            sentences, 
            show_progress=len(sentences) > 100
        )
        
        # Encontrar puntos de quiebre basados en similitud
        breakpoints = self._find_semantic_breakpoints(embeddings, sentences)
        
        # Crear chunks basados en los breakpoints
        chunks = self._create_chunks_from_breakpoints(
            sentences=sentences,
            breakpoints=breakpoints,
            document=document,
            full_text=full_text
        )
        
        logger.debug(
            f"Documento {document.doc_id}: {len(sentences)} oraciones -> "
            f"{len(chunks)} chunks semánticos"
        )
        
        return chunks
    
    def chunk_batch(
        self, 
        documents: List[AcquiredDocument], 
        config: Optional[ChunkingConfig] = None
    ) -> List[List[ChunkDocument]]:
        """
        Procesa múltiples documentos (secuencial, embeddings en batch por doc).
        
        Args:
            documents: Lista de documentos
            config: Configuración base
            
        Returns:
            Lista de listas de chunks
        """
        return [self.chunk_document(doc, config) for doc in documents]
    
    def chunk_strategy(self) -> str:
        """Retorna el nombre de la estrategia."""
        return "semantic"
    
    def _extract_full_text(self, document: AcquiredDocument) -> str:
        """Extrae todo el texto del documento."""
        parts = []
        
        # Título
        if document.content.title:
            parts.append(document.content.title)
        
        # Body
        if document.content.body:
            parts.append(document.content.body)
        
        # Secciones
        for section in document.content.sections:
            if section.title:
                parts.append(section.title)
            if section.text:
                parts.append(section.text)
        
        return "\n\n".join(parts)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Divide texto en oraciones."""
        # Normalizar whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Dividir por patrones de oración
        sentences = SENTENCE_PATTERN.split(text)
        
        # Filtrar vacíos y muy cortos
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Si no se dividió bien, intentar por puntos simples
        if len(sentences) == 1 and len(text) > 500:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _combine_short_sentences(self, sentences: List[str]) -> List[str]:
        """Combina oraciones muy cortas con la siguiente."""
        threshold = self.semantic_config.short_sentence_threshold
        combined = []
        buffer = ""
        
        for sentence in sentences:
            if len(sentence) < threshold:
                buffer += " " + sentence if buffer else sentence
            else:
                if buffer:
                    combined.append(buffer + " " + sentence)
                    buffer = ""
                else:
                    combined.append(sentence)
        
        # No olvidar el buffer final
        if buffer:
            if combined:
                combined[-1] += " " + buffer
            else:
                combined.append(buffer)
        
        return combined
    
    def _find_semantic_breakpoints(
        self, 
        embeddings: "torch.Tensor",
        sentences: List[str]
    ) -> List[int]:
        """
        Encuentra índices donde la similitud semántica cae.
        
        Args:
            embeddings: Tensor (n_sentences, embedding_dim)
            sentences: Lista de oraciones
            
        Returns:
            Lista de índices donde empieza un nuevo chunk
        """
        import torch
        
        n = len(sentences)
        if n <= 1:
            return [0]
        
        # Calcular similitud entre oraciones consecutivas
        similarities = []
        for i in range(n - 1):
            sim = torch.nn.functional.cosine_similarity(
                embeddings[i:i+1], 
                embeddings[i+1:i+2]
            )
            similarities.append(sim.item())
        
        # Encontrar breakpoints
        breakpoints = [0]  # Siempre empezamos con índice 0
        current_chunk_size = 1
        
        for i, sim in enumerate(similarities):
            current_chunk_size += 1
            
            # Condiciones para crear breakpoint:
            # 1. Similitud bajo umbral
            # 2. O chunk actual excede máximo de oraciones
            should_break = (
                sim < self.semantic_config.similarity_threshold or
                current_chunk_size >= self.semantic_config.max_sentences_per_chunk
            )
            
            # No romper si chunk actual tiene muy pocas oraciones
            if (should_break and 
                current_chunk_size >= self.semantic_config.min_sentences_per_chunk):
                breakpoints.append(i + 1)  # El breakpoint es la siguiente oración
                current_chunk_size = 0
        
        return breakpoints
    
    def _create_chunks_from_breakpoints(
        self,
        sentences: List[str],
        breakpoints: List[int],
        document: AcquiredDocument,
        full_text: str
    ) -> List[ChunkDocument]:
        """Crea objetos ChunkDocument a partir de breakpoints."""
        chunks = []
        
        # Agregar punto final implícito
        breakpoints = breakpoints + [len(sentences)]
        
        for i in range(len(breakpoints) - 1):
            start_idx = breakpoints[i]
            end_idx = breakpoints[i + 1]
            
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = " ".join(chunk_sentences)
            
            # Verificar tamaño mínimo
            if len(chunk_text) < self.semantic_config.min_chunk_chars and chunks:
                # Fusionar con chunk anterior (recrear ChunkDocument)
                prev_chunk = chunks[-1]
                merged_text = prev_chunk.chunk_text + " " + chunk_text
                
                import hashlib
                chunk_hash = hashlib.sha256(merged_text.encode()).hexdigest()[:16]
                
                chunks[-1] = ChunkDocument(
                    chunk_id=prev_chunk.chunk_id,
                    doc_id=prev_chunk.doc_id,
                    url=prev_chunk.url,
                    source_domain=prev_chunk.source_domain,
                    fetched_at=prev_chunk.fetched_at,
                    mime_type=prev_chunk.mime_type,
                    seed_group=prev_chunk.seed_group,
                    seed_id=prev_chunk.seed_id,
                    depth=prev_chunk.depth,
                    section_heading=prev_chunk.section_heading,
                    section_index=prev_chunk.section_index,
                    chunk_index=prev_chunk.chunk_index,
                    start_char=prev_chunk.start_char,
                    end_char=prev_chunk.end_char + len(chunk_text) + 1,
                    chunk_text=merged_text,
                    language=prev_chunk.language,
                    content_hash=prev_chunk.content_hash,
                    chunk_hash=chunk_hash,
                )
            else:
                # Crear nuevo chunk
                chunk = self._create_chunk(
                    document=document,
                    text=chunk_text,
                    chunk_index=len(chunks),
                    start_char=0,  # Simplificado
                    end_char=len(chunk_text),
                )
                chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        document: AcquiredDocument,
        text: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
    ) -> ChunkDocument:
        """Crea un objeto ChunkDocument."""
        import hashlib
        
        chunk_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        
        return ChunkDocument(
            chunk_id=f"{document.doc_id}:0:{chunk_index}",
            doc_id=document.doc_id,
            url=document.url,
            source_domain=document.source_domain,
            fetched_at=document.fetched_at,
            mime_type=document.content.mime_type,
            seed_group=document.crawl.seed_group,
            seed_id=document.crawl.seed_id,
            depth=document.crawl.depth,
            section_heading="",  # Simplificado para semantic chunking
            section_index=0,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            chunk_text=text,
            language=document.page_meta.language if document.page_meta else None,
            content_hash=document.content_hash,
            chunk_hash=chunk_hash,
        )
