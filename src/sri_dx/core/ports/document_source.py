from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from sri_dx.core.schemas.acquired_document import AcquiredDocument


class DocumentSourcePort(ABC):
    """
    Fuente de documentos (JSONL hoy, mañana podría ser DB, API, etc.).
    """
    @abstractmethod
    def iter_documents(self) -> Iterable[AcquiredDocument]:
        raise NotImplementedError
