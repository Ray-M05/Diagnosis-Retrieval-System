from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FeedbackStorePort(ABC):
    @abstractmethod
    def save_feedback(
        self,
        session_id: str,
        query: str,
        chunk_id: str,
        doc_id: str,
        relevant: bool,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_feedback(
        self,
        session_id: str,
        query: str,
        chunk_id: str,
        doc_id: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_feedback_for_session(self, session_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_query_expansion(
        self,
        session_id: str | None,
        original_query: str,
        expanded_query: str,
        strategy: str,
    ) -> None:
        raise NotImplementedError
