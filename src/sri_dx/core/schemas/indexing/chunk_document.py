from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class ChunkDocument:
    """
    Representa un fragmento (chunk) de un documento para búsqueda vectorial o léxica.
    Diseñado para trazabilidad Completa.
    """
    chunk_id: str             # {doc_id}:{section_index}:{chunk_index}
    doc_id: str               # Documento padre

    # Trazabilidad y Origen
    url: str
    source_domain: str
    fetched_at: str           # ISO-8601 UTC string de la adquisición
    mime_type: str

    # Metadatos de Crawling (Mantenidos desde AcquiredDocument)
    seed_group: str
    seed_id: str
    depth: int

    # Contexto de la sección
    section_heading: str
    section_index: int
    chunk_index: int          # Orden dentro de la sección

    # Offsets dentro del texto original de la SECCIÓN
    start_char: int
    end_char: int

    # Contenido
    chunk_text: str
    language: Optional[str] = None
    
    # Hashes para control de cambios
    content_hash: Optional[str] = None  # Hash del doc completo
    chunk_hash: Optional[str] = None    # Hash solo del texto de este chunk

    # Enriquecimiento (Módulo 4: Conceptos / Módulo 4: Embeddings)
    concept_ids: List[str] = None

    # Vector Search (kNN)
    embedding: Optional[List[float]] = None
