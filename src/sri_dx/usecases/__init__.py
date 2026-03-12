# Use Cases - Casos de Uso del Sistema
# Organizados por dominio para fácil navegación
# 
# indexing/ - Casos de uso de indexación
# search/   - Casos de uso de búsqueda

from .acquisition import RunAcquisitionUseCase
from .indexing import (
    IndexOpenSearchUseCase,
    IndexChunksOpenSearchUseCase,
    IndexCorpusPhaseAUseCase,
)
from .search import SearchLexicalUseCase

__all__ = [
    # Acquisition
    "RunAcquisitionUseCase",
    # Indexing
    "IndexOpenSearchUseCase",
    "IndexChunksOpenSearchUseCase",
    "IndexCorpusPhaseAUseCase",
    # Search
    "SearchLexicalUseCase",
]
