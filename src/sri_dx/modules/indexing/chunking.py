from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from sri_dx.core.schemas.acquired_document import AcquiredDocument
from sri_dx.core.schemas.chunk_document import ChunkDocument

@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 1200
    overlap_chars: int = 200
    min_chars: int = 100

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _split_with_overlap(text: str, cfg: ChunkingConfig) -> List[Tuple[int, int, str]]:
    """
    Divide un texto en ventanas de caracteres con solapamiento.
    Intenta no cortar palabras a la mitad.
    """
    text = (text or "").strip()
    if not text:
        return []
        
    if len(text) <= cfg.max_chars:
        return [(0, len(text), text)] if len(text) >= cfg.min_chars else []

    out = []
    start = 0
    n = len(text)

    while start < n:
        end = min(n, start + cfg.max_chars)

        # Intenta retroceder hasta un espacio en blanco para no cortar palabras
        if end < n:
            back = end
            # No retrocedemos más de 80 caracteres para no crear chunks demasiado pequeños
            limit = max(start + cfg.min_chars, end - 80)
            while back > limit and not text[back - 1].isspace():
                back -= 1
            if back > start + cfg.min_chars:
                end = back

        chunk = text[start:end].strip()
        # Solo guardamos si cumple el mínimo (el último chunk puede ser muy pequeño)
        if len(chunk) >= cfg.min_chars or (end == n and len(chunk) > 0):
            out.append((start, end, chunk))

        if end >= n:
            break
            
        # El siguiente inicio es el fin actual menos el overlap
        start = max(0, end - cfg.overlap_chars)
        
        # Salvaguarda: si no avanzamos, forzamos avance para evitar bucle infinito
        if start >= end:
            start = end

    return out

def build_chunk_id(doc_id: str, section_index: int, chunk_index: int) -> str:
    return f"{doc_id}:{section_index}:{chunk_index}"

def chunk_acquired_document(
    doc: AcquiredDocument,
    *,
    cfg: ChunkingConfig = ChunkingConfig(),
    concept_extractor=None,
) -> Iterable[ChunkDocument]:
    """
    Transforma un documento adquirido en múltiples ChunkDocument.
    1. Itera sobre las secciones clínicas.
    2. Divide cada sección en trozos según la configuración de ventana.
    """
    language = doc.page_meta.language if doc.page_meta else None
    content_hash = doc.content_hash

    for s_idx, sec in enumerate(doc.content.sections):
        heading = (sec.heading or "").strip() or "main"
        pieces = _split_with_overlap(sec.text, cfg)

        for c_idx, (start, end, chunk_text) in enumerate(pieces):
            chunk_id = build_chunk_id(doc.doc_id, s_idx, c_idx)
            chunk_hash = _sha256(chunk_text)

            concept_ids = []
            if concept_extractor is not None:
                # Si existe el extractor, lo usamos (Fase B/D)
                try:
                    concept_ids = concept_extractor.extract(chunk_text, language=language or "es")
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
