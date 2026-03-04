from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IndexDocument:
    """
    Documento listo para indexación (forma interna).
    Importante: no inventa semántica clínica; solo prepara campos y derivados.
    """
    doc_id: str
    url: str
    source_domain: str
    fetched_at: str

    mime_type: str
    title: str
    body: str
    sections_text: str

    # Facets/filtros derivables desde el contrato de adquisición
    seed_group: str
    seed_id: str
    depth: int

    # Metadatos opcionales
    language: Optional[str]
    published_at: Optional[str]
    updated_at: Optional[str]
    author: Optional[str]

    # Para incrementalidad
    content_hash: str

    # Estadísticas útiles (debug + features futuras)
    char_len: int
    word_count: int
    section_count: int
