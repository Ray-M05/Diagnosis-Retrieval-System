"""SQLite persistence for query expansion traces and relevance feedback."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sri_dx.core.ports.feedback.feedback_store_port import FeedbackStorePort


class SqliteFeedbackStore(FeedbackStorePort):
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=5, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS relevance_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                query TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                relevant INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_relevance_feedback_session
            ON relevance_feedback(session_id, created_at);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_relevance_feedback_vote
            ON relevance_feedback(session_id, query, chunk_id, doc_id);

            CREATE TABLE IF NOT EXISTS query_expansions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                original_query TEXT NOT NULL,
                expanded_query TEXT NOT NULL,
                strategy TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_query_expansions_session
            ON query_expansions(session_id, created_at);
            """
        )
        # Best-effort dedup of any pre-existing duplicate votes from before the
        # unique index existed. Keep the most recent (highest id) for each key.
        try:
            self.conn.execute(
                """
                DELETE FROM relevance_feedback
                WHERE id NOT IN (
                    SELECT MAX(id) FROM relevance_feedback
                    GROUP BY session_id, query, chunk_id, doc_id
                )
                """
            )
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def save_feedback(
        self,
        session_id: str,
        query: str,
        chunk_id: str,
        doc_id: str,
        relevant: bool,
    ) -> None:
        # Upsert: a user can change their mind (thumbs up → thumbs down) without
        # creating duplicate rows.
        self.conn.execute(
            """
            INSERT INTO relevance_feedback (session_id, query, chunk_id, doc_id, relevant)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id, query, chunk_id, doc_id) DO UPDATE SET
                relevant = excluded.relevant,
                created_at = CURRENT_TIMESTAMP
            """,
            (session_id, query, chunk_id, doc_id, int(relevant)),
        )
        self.conn.commit()

    def delete_feedback(
        self,
        session_id: str,
        query: str,
        chunk_id: str,
        doc_id: str,
    ) -> bool:
        """Retract a vote. Returns True if a row was deleted."""
        cursor = self.conn.execute(
            """
            DELETE FROM relevance_feedback
            WHERE session_id = ? AND query = ? AND chunk_id = ? AND doc_id = ?
            """,
            (session_id, query, chunk_id, doc_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_feedback_for_session(self, session_id: str) -> list[dict[str, Any]]:
        cursor = self.conn.execute(
            """
            SELECT session_id, query, chunk_id, doc_id, relevant, created_at
            FROM relevance_feedback
            WHERE session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (session_id,),
        )
        return [
            {
                "session_id": row["session_id"],
                "query": row["query"],
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "relevant": bool(row["relevant"]),
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

    def save_query_expansion(
        self,
        session_id: str | None,
        original_query: str,
        expanded_query: str,
        strategy: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO query_expansions (session_id, original_query, expanded_query, strategy)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, original_query, expanded_query, strategy),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
