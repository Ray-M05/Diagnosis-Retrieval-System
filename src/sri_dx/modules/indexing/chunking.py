from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional

from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument
from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument

# Intenta importar el SemanticChunker. Si falla (dependencias no satisfechas), 
# se ignorará graciosamente o se levantará alerta en tiempo de ejecución.
try:
    from sri_dx.modules.chunking.semantic_chunker import SemanticChunker
except ImportError:
    SemanticChunker = None

@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 1200
    overlap_chars: int = 200
    min_chars: int = 100

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def build_chunk_id(doc_id: str, section_index: int, chunk_index: int) -> str:
    return f"{doc_id}:{section_index}:{chunk_index}"

def chunk_acquired_document(
    doc: AcquiredDocument,
    *,
    cfg: ChunkingConfig = ChunkingConfig(),
    concept_extractor=None,
    semantic_chunker: Optional["SemanticChunker"] = None
) -> Iterable[ChunkDocument]:
    """
    Transforma un documento adquirido en múltiples ChunkDocument.
    1. Trata cada sección completa como un único chunk primario.
    2. Si la sección excede 'max_chars', la divide usando SemanticChunking en lugar de ventana.
    """
    language = doc.page_meta.language if doc.page_meta else None
    content_hash = doc.content_hash
    
    # Inicialización perezosa para evitar dependencias forzadas si no es necesario
    if semantic_chunker is None and SemanticChunker is not None:
        semantic_chunker = SemanticChunker()

    for s_idx, sec in enumerate(doc.content.sections):
        heading = (sec.heading or "").strip() or "main"
        sec_text = (sec.text or "").strip()
        
        if not sec_text:
            continue
            
        pieces = []
        # Si la sección excede el tamaño máximo y el chunker semántico está disponible,
        # dividimos la sección base en componentes semánticos.
        if len(sec_text) > cfg.max_chars and semantic_chunker is not None:
            pieces = semantic_chunker.split_text(sec_text)
            
            # Si por algún motivo el semantic chunker falló, caemos al valor crudo.
            if not pieces:
                pieces = [(0, len(sec_text), sec_text)]
        else:
            pieces = [(0, len(sec_text), sec_text)]

        for c_idx, (start, end, chunk_text) in enumerate(pieces):
            chunk_id = build_chunk_id(doc.doc_id, s_idx, c_idx)
            chunk_hash = _sha256(chunk_text)

            concept_ids = []
            if concept_extractor is not None:
                # Si existe el extractor, lo usamos (Fase B/D)
                try:
                    concept_ids = concept_extractor.extract(chunk_text, language=language or "en")
                except Exception:
                    concept_ids = []

            yield ChunkDocument(
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                url=doc.url,
                source_domain=doc.source_domain,
                fetched_at=doc.fetched_at,
                mime_type=doc.content.mime_type,
                seed_group=doc.crawl.seed_group,
                seed_id=doc.crawl.seed_id,
                depth=doc.crawl.depth,
                section_heading=heading,
                section_index=s_idx,
                chunk_index=c_idx,
                start_char=start,
                end_char=end,
                chunk_text=chunk_text,
                language=language,
                content_hash=content_hash,
                chunk_hash=chunk_hash,
                concept_ids=concept_ids,
                embedding=None, # Módulo 4
            )
