"""Chunking Module - Estrategias de Segmentación

Módulo para dividir documentos en fragmentos (chunks) óptimos para búsqueda.

Estrategias implementadas:
- SemanticChunker: Segmentación semántica con Bio_ClinicalBERT ✅

Estrategias por implementar:
- sliding_window: Ventana deslizante con overlap (en indexing/chunking.py)
- medical_section: Segmentación por secciones clínicas

Estado: ✅ IMPLEMENTADO (SemanticChunker)
"""

from .semantic_chunker import SemanticChunker
from .schemas.chunking_config import SemanticChunkingConfig

__all__ = ["SemanticChunker", "SemanticChunkingConfig"]
