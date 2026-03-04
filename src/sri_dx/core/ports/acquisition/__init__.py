# Ports para el módulo de Acquisition
# Interfaces para obtención y persistencia de documentos

from .document_sink import IndexDocumentSinkPort
from .document_source import DocumentSourcePort
from .manifest_store import ManifestStorePort

__all__ = [
    "IndexDocumentSinkPort",
    "DocumentSourcePort", 
    "ManifestStorePort",
]
