from __future__ import annotations

from abc import ABC, abstractmethod

from sri_dx.core.schemas.index_document import IndexDocument


class IndexDocumentSinkPort(ABC):
    """
    Aún no lo usamos en Fase A, pero lo defines ya para Fase C:
    - Elasticsearch, Whoosh, índice casero, etc.
    """
    @abstractmethod
    def upsert(self, doc: IndexDocument) -> None:
        raise NotImplementedError
