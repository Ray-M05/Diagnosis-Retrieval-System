"""
Writes a list of ``AcquiredDocument``-compatible dicts to a JSONL file
(one JSON object per line) under the configured delta directory.

The file is named ``api_query_<query_hash>.jsonl`` and is overwritten on
every call for the same query hash, making repeated runs idempotent.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class JsonlDeltaWriter:
    """
    Writes document dicts to a JSONL delta file.

    Parameters
    ----------
    delta_dir:
        Directory where delta files are stored
        (e.g. ``data/processed/api_deltas``).
    """

    def __init__(self, delta_dir: Path | str) -> None:
        self.delta_dir = Path(delta_dir)

    def write(self, docs: list[dict], query_hash: str) -> Path:
        """
        Serialise *docs* to ``<delta_dir>/api_query_<query_hash>.jsonl``.

        Parameters
        ----------
        docs:
            List of ``AcquiredDocument``-compatible dicts.
        query_hash:
            Short hash (e.g. first 8 hex chars of SHA-1 of the query string)
            used to name the file.

        Returns
        -------
        Path
            Absolute path of the written file.
        """
        self.delta_dir.mkdir(parents=True, exist_ok=True)
        path = self.delta_dir / f"api_query_{query_hash}.jsonl"

        with path.open("w", encoding="utf-8") as fh:
            for doc in docs:
                fh.write(json.dumps(doc, ensure_ascii=False, default=str) + "\n")

        logger.info(
            "Delta writer: wrote %d document(s) to '%s'", len(docs), path
        )
        return path
