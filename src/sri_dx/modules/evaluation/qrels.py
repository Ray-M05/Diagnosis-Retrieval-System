"""Qrels (query relevance judgments) loader.

JSONL format — one judgment per line:

    {"query": "...", "relevant_disease_names": ["acromegalia"]}
    {"query": "...", "relevant_disease_names": [...],
     "relevant_chunk_ids": [...], "relevant_doc_ids": [...]}

Disease names are normalized at load time so downstream metrics can do plain
set-membership checks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from sri_dx.modules.evaluation.normalization import normalize_disease_name


@dataclass
class QrelEntry:
    query: str
    relevant_disease_names: list[str] = field(default_factory=list)
    relevant_chunk_ids: list[str] | None = None
    relevant_doc_ids: list[str] | None = None

    @property
    def has_chunk_level(self) -> bool:
        return bool(self.relevant_chunk_ids) or bool(self.relevant_doc_ids)


@dataclass
class Qrels:
    entries: list[QrelEntry]
    qrels_hash: str

    @classmethod
    def load_jsonl(cls, content: str) -> "Qrels":
        """Parse JSONL content (string). Empty/whitespace lines are skipped."""
        entries: list[QrelEntry] = []
        for line_num, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_num}: {exc}") from exc

            query = obj.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"Line {line_num}: missing or empty 'query'")

            diseases_raw = obj.get("relevant_disease_names") or []
            if not isinstance(diseases_raw, list):
                raise ValueError(f"Line {line_num}: 'relevant_disease_names' must be a list")
            diseases = [normalize_disease_name(str(d)) for d in diseases_raw if str(d).strip()]

            chunk_ids = obj.get("relevant_chunk_ids")
            if chunk_ids is not None and not isinstance(chunk_ids, list):
                raise ValueError(f"Line {line_num}: 'relevant_chunk_ids' must be a list or null")
            chunk_ids = [str(c) for c in chunk_ids] if chunk_ids else None

            doc_ids = obj.get("relevant_doc_ids")
            if doc_ids is not None and not isinstance(doc_ids, list):
                raise ValueError(f"Line {line_num}: 'relevant_doc_ids' must be a list or null")
            doc_ids = [str(d) for d in doc_ids] if doc_ids else None

            entries.append(
                QrelEntry(
                    query=query.strip(),
                    relevant_disease_names=diseases,
                    relevant_chunk_ids=chunk_ids,
                    relevant_doc_ids=doc_ids,
                )
            )

        if not entries:
            raise ValueError("Qrels file is empty — no valid entries found")

        qrels_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return cls(entries=entries, qrels_hash=qrels_hash)

    @property
    def has_any_chunk_level(self) -> bool:
        return any(e.has_chunk_level for e in self.entries)
