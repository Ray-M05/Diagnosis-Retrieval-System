from __future__ import annotations
from sri_dx.core.ports.feedback.feedback_store_port import FeedbackStorePort


class FeedbackService:

    def __init__(self, store: FeedbackStorePort) -> None:
        self.store = store

    def record_feedback(
        self,
        session_id: str,
        query: str,
        chunk_id: str,
        doc_id: str,
        relevant: bool,
    ) -> None:
        if not session_id.strip():
            raise ValueError("session_id is required")
        if not query.strip():
            raise ValueError("query is required")
        if not chunk_id.strip():
            raise ValueError("chunk_id is required")
        if not doc_id.strip():
            raise ValueError("doc_id is required")

        self.store.save_feedback(
            session_id=session_id,
            query=query,
            chunk_id=chunk_id,
            doc_id=doc_id,
            relevant=relevant,
        )

    def retract_feedback(
        self,
        session_id: str,
        query: str,
        chunk_id: str,
        doc_id: str,
    ) -> bool:
        """Remove a previously recorded vote. Returns True if removed."""
        if not session_id.strip():
            raise ValueError("session_id is required")
        if not query.strip():
            raise ValueError("query is required")
        if not chunk_id.strip():
            raise ValueError("chunk_id is required")
        if not doc_id.strip():
            raise ValueError("doc_id is required")

        return self.store.delete_feedback(
            session_id=session_id,
            query=query,
            chunk_id=chunk_id,
            doc_id=doc_id,
        )
