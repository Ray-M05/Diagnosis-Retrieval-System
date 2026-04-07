from __future__ import annotations

import hashlib
import logging
from typing import Optional
from dateutil import parser

from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument
from sri_dx.core.schemas.indexing.index_document import IndexDocument
from sri_dx.modules.indexing.text.text_pipeline import TextAnalyzer

logger = logging.getLogger(__name__)

_analyzer = TextAnalyzer()


def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normaliza una cadena de fecha a formato ISO 8601 (YYYY-MM-DDTHH:MM:SS) 
    para que OpenSearch pueda indexarla sin errores de mapeo.
    """
    if not date_str or not date_str.strip():
        return None
    try:
        # fuzzy=True permite ignorar texto extra alrededor de la fecha
        dt = parser.parse(date_str, fuzzy=True)
        return dt.isoformat()
    except (ValueError, OverflowError, TypeError) as e:
        logger.warning(f"No se pudo parsear la fecha '{date_str}': {e}")
        return None


def _flatten_sections(doc: AcquiredDocument) -> str:
    # Forma estable: incluye headings para que luego puedas buscar por nombres de secciones
    parts: list[str] = []
    for s in doc.content.sections:
        h = s.heading.strip()
        t = s.text.strip()
        if h:
            parts.append(h)
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip()


def _safe_title(doc: AcquiredDocument) -> str:
    # Para indexación: evita None
    if doc.content.title and doc.content.title.strip():
        return doc.content.title.strip()
    return ""


def _compute_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def prepare_index_document(
    doc: AcquiredDocument,
    *,
    concept_extractor=None,
) -> IndexDocument:
    title = _safe_title(doc)
    body = doc.content.body.strip()
    sections_text = _flatten_sections(doc)

    # Si el módulo 1 no trajo content_hash, lo calculamos aquí (recomendado por el contrato)
    content_hash = doc.content_hash or _compute_hash(body)

    language: Optional[str] = doc.page_meta.language if doc.page_meta else None
    published_at: Optional[str] = _normalize_date(doc.page_meta.published_at) if doc.page_meta else None
    updated_at: Optional[str] = _normalize_date(doc.page_meta.updated_at) if doc.page_meta else None
    author: Optional[str] = doc.page_meta.author if doc.page_meta else None

    # Stats simples: útiles para debugging + features futuras
    word_count = len(_analyzer.analyze(body, language=language).tokens)
    char_len = len(body)
    
    # Enriquecimientos a nivel de Documento completo
    doc_text = f"{title}\n\n{sections_text}".strip()
    concept_ids = []
    if concept_extractor is not None:
        try:
            concept_ids = concept_extractor.extract(doc_text, language=language or "en")
        except Exception:
            concept_ids = []
            
    return IndexDocument(
        doc_id=doc.doc_id,
        url=doc.url,
        source_domain=doc.source_domain,
        fetched_at=doc.fetched_at,

        mime_type=doc.content.mime_type,
        title=title,
        body=body,
        sections_text=sections_text,

        seed_group=doc.crawl.seed_group,
        seed_id=doc.crawl.seed_id,
        depth=doc.crawl.depth,

        language=language,
        published_at=published_at,
        updated_at=updated_at,
        author=author,

        content_hash=content_hash,

        char_len=char_len,
        word_count=word_count,
        section_count=len(doc.content.sections),
        
        concept_ids=concept_ids,
        ner_entities=[],
    )