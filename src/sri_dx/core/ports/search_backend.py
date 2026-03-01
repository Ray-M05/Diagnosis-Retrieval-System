from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from sri_dx.core.schemas.search_request import SearchRequest
from sri_dx.core.schemas.search_response import SearchResponse, DocumentRecord


class SearchBackendPort(ABC):
    @abstractmethod
    def search(self, req: SearchRequest) -> SearchResponse:
        raise NotImplementedError

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        raise NotImplementedError
