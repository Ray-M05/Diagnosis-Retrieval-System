"""Unit tests — JsonlDeltaWriter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sri_dx.modules.web_search.delta_writer import JsonlDeltaWriter


class TestJsonlDeltaWriter:
    def test_creates_file(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path / "deltas")
        docs = [{"doc_id": "d1", "title": "Test"}]
        path = writer.write(docs, query_hash="abcd1234")
        assert path.exists()
        assert path.name == "api_query_abcd1234.jsonl"

    def test_creates_directory(self, tmp_path: Path):
        delta_dir = tmp_path / "deep" / "nested" / "dir"
        writer = JsonlDeltaWriter(delta_dir)
        writer.write([{"doc_id": "d1"}], query_hash="00000001")
        assert delta_dir.exists()

    def test_one_line_per_document(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path)
        docs = [
            {"doc_id": "d1", "val": 1},
            {"doc_id": "d2", "val": 2},
            {"doc_id": "d3", "val": 3},
        ]
        path = writer.write(docs, query_hash="test0001")
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3

    def test_each_line_is_valid_json(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path)
        docs = [{"doc_id": f"d{i}", "score": 0.5 + i * 0.1} for i in range(5)]
        path = writer.write(docs, query_hash="validjson")
        for line in path.read_text(encoding="utf-8").splitlines():
            obj = json.loads(line)
            assert "doc_id" in obj

    def test_overwrites_existing_file(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path)
        writer.write([{"doc_id": "old"}], query_hash="same")
        writer.write([{"doc_id": "new1"}, {"doc_id": "new2"}], query_hash="same")
        path = tmp_path / "api_query_same.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert "new1" in lines[0]

    def test_empty_list_writes_empty_file(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path)
        path = writer.write([], query_hash="empty0001")
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip() == ""

    def test_returns_path_object(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path)
        result = writer.write([{"doc_id": "d1"}], query_hash="pathtst")
        assert isinstance(result, Path)

    def test_unicode_content_preserved(self, tmp_path: Path):
        writer = JsonlDeltaWriter(tmp_path)
        docs = [{"doc_id": "d1", "title": "Diagnosis of café disease — résumé"}]
        path = writer.write(docs, query_hash="unicode1")
        content = path.read_text(encoding="utf-8")
        assert "café" in content
        assert "résumé" in content
