from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple, Optional

from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument
from sri_dx.core.schemas.indexing.chunk_document import ChunkDocument


# SemanticChunker se pasa como argumento desde el llamador (index_combined).
# No se instancia aquí para evitar cargar el modelo en imports y para
# garantizar que se use el singleton compartido.


# Headings de secciones que no aportan contenido clínico (boilerplate de sitios web).
# Comparación en lowercase.
_SKIP_HEADINGS: frozenset[str] = frozenset({
    "products & services",
    "associated procedures",
    "mayo clinic press",
    "from mayo clinic to your inbox",
    "sorry something went wrong with your subscription",
    "thank you for subscribing!",
    "thank you for subscribing",
    "news from mayo clinic",
    "related",
    "find out more",
    "on this page",
})

# Largo mínimo de texto de sección para generar un chunk
_MIN_SECTION_CHARS = 50


@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 1800
    overlap_chars: int = 200       # Solo usado por ventana deslizante
    min_chars: int = 100
    use_semantic_chunker: bool = True  # False → ventana deslizante por párrafos


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_chunk_id(doc_id: str, section_index: int, chunk_index: int) -> str:
    return f"{doc_id}:{section_index}:{chunk_index}"


def _sliding_window_chunks(text: str, max_chars: int, overlap_chars: int) -> List[Tuple[int, int, str]]:
    """
    Divide texto en chunks usando ventana deslizante por párrafos.

    Estrategia:
    1. Divide por párrafos (líneas en blanco).
    2. Acumula párrafos hasta alcanzar max_chars.
    3. Al pasar el límite, cierra el chunk y retrocede overlap_chars para el siguiente.
    """
    # Dividir en párrafos no vacíos
    paragraphs: List[Tuple[int, str]] = []
    pos = 0
    for para in text.split("\n\n"):
        stripped = para.strip()
        if stripped:
            # Encontrar posición real en el texto original
            p_start = text.find(stripped, pos)
            if p_start == -1:
                p_start = pos
            paragraphs.append((p_start, stripped))
            pos = p_start + len(stripped)

    if not paragraphs:
        return [(0, len(text), text)]

    chunks: List[Tuple[int, int, str]] = []
    buf_start = paragraphs[0][0]
    buf_parts: List[str] = []
    buf_len = 0

    def flush(start: int, parts: List[str]) -> Tuple[int, int, str]:
        chunk_text = "\n\n".join(parts)
        return (start, start + len(chunk_text), chunk_text)

    for p_start, p_text in paragraphs:
        if buf_len + len(p_text) > max_chars and buf_parts:
            chunks.append(flush(buf_start, buf_parts))
            # Retroceder: incluir últimos ~overlap_chars en el siguiente chunk
            overlap_parts: List[str] = []
            overlap_len = 0
            for part in reversed(buf_parts):
                if overlap_len + len(part) <= overlap_chars:
                    overlap_parts.insert(0, part)
                    overlap_len += len(part)
                else:
                    break
            buf_parts = overlap_parts
            buf_len = overlap_len
            buf_start = p_start - overlap_len  # aproximado

        buf_parts.append(p_text)
        buf_len += len(p_text)

    if buf_parts:
        chunks.append(flush(buf_start, buf_parts))

    return chunks if chunks else [(0, len(text), text)]


def chunk_acquired_document(
    doc: AcquiredDocument,
    *,
    cfg: ChunkingConfig = ChunkingConfig(),
    concept_extractor=None,
    semantic_chunker=None,
) -> Iterable[ChunkDocument]:
    """
    Transforma un documento adquirido en múltiples ChunkDocument.

    Estrategia por sección:
    - Si la sección cabe en max_chars → un único chunk (sección completa).
    - Si supera max_chars y use_semantic_chunker=True y semantic_chunker disponible
      → SemanticChunker (MiniLM) detecta breakpoints temáticos.
    - Si supera max_chars y use_semantic_chunker=False (o chunker no disponible)
      → ventana deslizante por párrafos con overlap.
    """
    language = doc.page_meta.language if doc.page_meta else None
    content_hash = doc.content_hash

    for s_idx, sec in enumerate(doc.content.sections):
        heading = (sec.heading or "").strip() or "main"
        sec_text = (sec.text or "").strip()

        if not sec_text:
            continue

        # Filtrar secciones boilerplate (no clínicas) y textos muy cortos
        if heading.lower() in _SKIP_HEADINGS:
            continue
        if len(sec_text) < _MIN_SECTION_CHARS:
            continue

        # Sección corta → chunk directo
        if len(sec_text) <= cfg.max_chars:
            pieces: List[Tuple[int, int, str]] = [(0, len(sec_text), sec_text)]
        elif cfg.use_semantic_chunker and semantic_chunker is not None:
            # Segunda estrategia: chunking semántico con MiniLM
            pieces = semantic_chunker.split_text(sec_text)
            if not pieces:
                pieces = [(0, len(sec_text), sec_text)]
        else:
            # Fallback: ventana deslizante por párrafos
            pieces = _sliding_window_chunks(sec_text, cfg.max_chars, cfg.overlap_chars)

        for c_idx, (start, end, chunk_text) in enumerate(pieces):
            chunk_id = build_chunk_id(doc.doc_id, s_idx, c_idx)
            chunk_hash = _sha256(chunk_text)

            concept_ids = []
            if concept_extractor is not None:
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
                ner_entities=[],
                embedding=None,
            )
