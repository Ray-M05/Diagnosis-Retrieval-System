"""SQLite persistence for evaluation runs.

Schema is intentionally simple — two tables, JSON blobs for metric dicts.
Lets the UI list past runs and re-fetch their per-query detail without
recomputing.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from sri_dx.modules.evaluation.evaluator import EvaluationReport


class EvaluationStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=5, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mode TEXT NOT NULL,
                k INTEGER NOT NULL,
                level TEXT NOT NULL,
                qrels_hash TEXT NOT NULL,
                corpus_size INTEGER NOT NULL,
                macro_disease_json TEXT NOT NULL,
                macro_chunk_json TEXT,
                errors_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_evaluation_runs_timestamp
                ON evaluation_runs(timestamp DESC);

            CREATE TABLE IF NOT EXISTS evaluation_per_query (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                retrieved_disease_json TEXT NOT NULL,
                relevant_disease_json TEXT NOT NULL,
                disease_metrics_json TEXT NOT NULL,
                retrieved_chunk_json TEXT,
                relevant_chunk_json TEXT,
                chunk_metrics_json TEXT,
                FOREIGN KEY(run_id) REFERENCES evaluation_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_evaluation_per_query_run
                ON evaluation_per_query(run_id);
            """
        )
        self.conn.commit()

    def save_run(self, report: EvaluationReport) -> int:
        """Persist a run + its per-query rows. Returns the new run id."""
        cur = self.conn.execute(
            """
            INSERT INTO evaluation_runs
                (timestamp, mode, k, level, qrels_hash, corpus_size,
                 macro_disease_json, macro_chunk_json, errors_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.timestamp,
                report.mode,
                report.k,
                report.level,
                report.qrels_hash,
                report.corpus_size,
                json.dumps(report.macro_disease),
                json.dumps(report.macro_chunk) if report.macro_chunk else None,
                json.dumps(report.errors) if report.errors else None,
            ),
        )
        run_id = int(cur.lastrowid)

        for r in report.per_query:
            self.conn.execute(
                """
                INSERT INTO evaluation_per_query
                    (run_id, query,
                     retrieved_disease_json, relevant_disease_json, disease_metrics_json,
                     retrieved_chunk_json, relevant_chunk_json, chunk_metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    r.query,
                    json.dumps(r.retrieved_disease_names),
                    json.dumps(r.relevant_disease_names),
                    json.dumps(r.disease_metrics),
                    json.dumps(r.retrieved_chunk_ids) if r.retrieved_chunk_ids is not None else None,
                    json.dumps(r.relevant_chunk_ids) if r.relevant_chunk_ids is not None else None,
                    json.dumps(r.chunk_metrics) if r.chunk_metrics is not None else None,
                ),
            )

        self.conn.commit()
        report.run_id = run_id
        return run_id

    def list_runs(self) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT id, timestamp, mode, k, level, qrels_hash, corpus_size,
                   macro_disease_json, macro_chunk_json
            FROM evaluation_runs
            ORDER BY id DESC
            """
        )
        return [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "mode": row["mode"],
                "k": row["k"],
                "level": row["level"],
                "qrels_hash": row["qrels_hash"],
                "corpus_size": row["corpus_size"],
                "macro": json.loads(row["macro_disease_json"]),
                "macro_chunk": json.loads(row["macro_chunk_json"]) if row["macro_chunk_json"] else None,
            }
            for row in cur.fetchall()
        ]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        cur = self.conn.execute(
            """
            SELECT id, timestamp, mode, k, level, qrels_hash, corpus_size,
                   macro_disease_json, macro_chunk_json, errors_json
            FROM evaluation_runs WHERE id = ?
            """,
            (run_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        per_query_cur = self.conn.execute(
            """
            SELECT query,
                   retrieved_disease_json, relevant_disease_json, disease_metrics_json,
                   retrieved_chunk_json, relevant_chunk_json, chunk_metrics_json
            FROM evaluation_per_query
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        )
        per_query = [
            {
                "query": pq["query"],
                "retrieved_disease_names": json.loads(pq["retrieved_disease_json"]),
                "relevant_disease_names": json.loads(pq["relevant_disease_json"]),
                "disease_metrics": json.loads(pq["disease_metrics_json"]),
                "retrieved_chunk_ids": json.loads(pq["retrieved_chunk_json"]) if pq["retrieved_chunk_json"] else None,
                "relevant_chunk_ids": json.loads(pq["relevant_chunk_json"]) if pq["relevant_chunk_json"] else None,
                "chunk_metrics": json.loads(pq["chunk_metrics_json"]) if pq["chunk_metrics_json"] else None,
            }
            for pq in per_query_cur.fetchall()
        ]

        return {
            "run_id": row["id"],
            "timestamp": row["timestamp"],
            "mode": row["mode"],
            "k": row["k"],
            "level": row["level"],
            "qrels_hash": row["qrels_hash"],
            "corpus_size": row["corpus_size"],
            "macro": json.loads(row["macro_disease_json"]),
            "macro_chunk": json.loads(row["macro_chunk_json"]) if row["macro_chunk_json"] else None,
            "errors": json.loads(row["errors_json"]) if row["errors_json"] else [],
            "per_query": per_query,
        }

    def close(self) -> None:
        self.conn.close()
