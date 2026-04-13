"""Document Sources Adapters

Adaptadores para lectura de documentos desde diferentes fuentes.

Adaptadores implementados:
- JsonlDocumentSource: Lectura de documentos desde archivos JSONL

Estado: ✅ IMPLEMENTADO
"""

from .jsonl_source import JsonlDocumentSource

__all__ = ["JsonlDocumentSource"]
