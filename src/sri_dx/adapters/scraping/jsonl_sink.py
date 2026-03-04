from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from sri_dx.modules.acquisition.ports import JsonlSink


class JsonlFileSink(JsonlSink):
    """
    1 doc = 1 línea JSON
    """
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, doc: dict[str, Any]) -> None:
        line = json.dumps(doc, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")