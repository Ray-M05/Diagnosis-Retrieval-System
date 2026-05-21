from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List

from sri_dx.core.schemas.indexing.ner import NerEntity

@dataclass(frozen=True)
class ChunkDocument:
    """
    Representa un fragmento (chunk) de un documento para búsqueda vectorial o léxica.
    Diseñado para trazabilidad Completa.
    """
    chunk_id: str             # {doc_id}:{section_index}:{chunk_index}
    doc_id: str               # Parent document

    # Traceability and origin
    url: str
    source_domain: str
    fetched_at: str           # ISO-8601 UTC string of the acquisition timestamp
    mime_type: str

    # Crawling metadata (preserved from AcquiredDocument)
    seed_group: str
    seed_id: str
    depth: int

    # Section context
    section_heading: str
    section_index: int
    chunk_index: int          # Order within the section

    # Character offsets within the original SECTION text
    start_char: int
    end_char: int

    # Content
    chunk_text: str
    language: Optional[str] = None

    # Hashes for change detection
    content_hash: Optional[str] = None  # Hash of the full document
    chunk_hash: Optional[str] = None    # Hash of this chunk's text only

    # Enrichment (Module 4: Concepts / Module 4: Embeddings)
    concept_ids: List[str] = field(default_factory=list)
    ner_entities: List[NerEntity] = field(default_factory=list)

    # Vector search (kNN)
    embedding: Optional[List[float]] = None

