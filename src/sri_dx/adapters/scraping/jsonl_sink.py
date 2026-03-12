from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Any

from sri_dx.core.ports.acquisition.jsonl_sink_port import JsonlSinkPort


class JsonlFileSink(JsonlSinkPort):
    """
    1 doc = 1 línea JSON. Thread-safe.
    """
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, doc: dict[str, Any]) -> None:
        line = json.dumps(doc, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")