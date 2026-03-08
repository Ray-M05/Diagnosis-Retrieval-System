from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sri_dx.core.ports.acquisition.manifest_store import ManifestEntry, ManifestStorePort


@dataclass
class SqliteManifestStore(ManifestStorePort):
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS manifest (
                doc_id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                pipeline_version TEXT NOT NULL,
                indexed_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_manifest_hash ON manifest(content_hash)")
            con.commit()
            # Ensure journal mode is not WAL (which can leave .wal/.shm files on Windows)
            try:
                con.execute("PRAGMA journal_mode=DELETE")
                con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                # Best effort; don't fail initialization if pragmas aren't supported
                pass

    def _connect(self) -> sqlite3.Connection:
        # Use a small timeout and disable WAL by default to avoid leftover
        # journal files locking the DB on Windows during test teardown.
        con = sqlite3.connect(str(self.path), timeout=5)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA journal_mode=DELETE")
        except Exception:
            pass
        return con

    def get(self, doc_id: str) -> ManifestEntry | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT doc_id, content_hash, pipeline_version FROM manifest WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if not row:
                return None
            return ManifestEntry(
                doc_id=row["doc_id"],
                content_hash=row["content_hash"],
                pipeline_version=row["pipeline_version"],
            )

    def get_many(self, doc_ids: Iterable[str]) -> dict[str, ManifestEntry]:
        ids = list(dict.fromkeys(doc_ids))
        if not ids:
            return {}
        placeholders = ",".join(["?"] * len(ids))
        q = f"SELECT doc_id, content_hash, pipeline_version FROM manifest WHERE doc_id IN ({placeholders})"
        with self._connect() as con:
            rows = con.execute(q, ids).fetchall()
        
        out: dict[str, ManifestEntry] = {}
        for r in rows:
            out[r["doc_id"]] = ManifestEntry(
                doc_id=r["doc_id"],
                content_hash=r["content_hash"],
                pipeline_version=r["pipeline_version"],
            )
        return out

    def upsert_many(self, entries: Iterable[ManifestEntry]) -> None:
        rows = [(e.doc_id, e.content_hash, e.pipeline_version) for e in entries]
        if not rows:
            return
        with self._connect() as con:
            con.executemany("""
            INSERT INTO manifest (doc_id, content_hash, pipeline_version)
            VALUES (?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                content_hash=excluded.content_hash,
                pipeline_version=excluded.pipeline_version,
                indexed_at=datetime('now')
            """, rows)
            con.commit()
