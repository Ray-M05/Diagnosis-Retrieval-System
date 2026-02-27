from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from sri_dx.core.schemas import AcquiredDocument, IndexDocument


class DocumentSourcePort(ABC):
    """
    Fuente de documentos (JSONL hoy, mañana podría ser DB, API, etc.).
    """
    @abstractmethod
    def iter_documents(self) -> Iterable[AcquiredDocument]:
        raise NotImplementedError


class IndexDocumentSinkPort(ABC):
    """
    Aún no lo usamos en Fase A, pero lo defines ya para Fase C:
    - Elasticsearch, Whoosh, índice casero, etc.
    """
    @abstractmethod
    def upsert(self, doc: IndexDocument) -> None:
        raise NotImplementedError