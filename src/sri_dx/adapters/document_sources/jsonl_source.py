from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Any

from sri_dx.core.schemas.acquisition.acquired_document import (
    AcquiredDocument, CrawlMeta, Content, PageMeta, Section
)
from sri_dx.core.ports.acquisition.document_source import DocumentSourcePort


class InvalidDocumentError(ValueError):
    pass


def _require(obj: dict, key: str, where: str) -> Any:
    if key not in obj:
        raise InvalidDocumentError(f"Missing required field '{key}' in {where}")
    return obj[key]


def _as_str(v: Any, where: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise InvalidDocumentError(f"Expected non-empty string in {where}")
    return v


def _as_int(v: Any, where: str) -> int:
    if not isinstance(v, int):
        raise InvalidDocumentError(f"Expected int in {where}")
    return v


def _as_opt_str(v: Any, where: str) -> Optional[str]:
    if v is None:
        return None
    if not isinstance(v, str):
        raise InvalidDocumentError(f"Expected string|null in {where}")
    vv = v.strip()
    return vv if vv else None


def _parse_sections(raw_sections: Any) -> list[Section]:
    if not isinstance(raw_sections, list):
        raise InvalidDocumentError("content.sections must be a list")
    sections: list[Section] = []
    for i, s in enumerate(raw_sections):
        if not isinstance(s, dict):
            raise InvalidDocumentError(f"content.sections[{i}] must be an object")
        heading = _as_str(_require(s, "heading", f"content.sections[{i}]"), f"content.sections[{i}].heading")
        text = _as_str(_require(s, "text", f"content.sections[{i}]"), f"content.sections[{i}].text")
        sections.append(Section(heading=heading, text=text))
    return sections


@dataclass
class JsonlDocumentSource(DocumentSourcePort):
    """Reads one or more JSONL files (HTML + PDF) and streams AcquiredDocument objects."""
    paths: list[Path]

    def iter_documents(self) -> Iterable[AcquiredDocument]:
        for p in self.paths:
            yield from self._iter_one_file(p)

    def _iter_one_file(self, path: Path) -> Iterable[AcquiredDocument]:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise InvalidDocumentError("JSONL line is not a JSON object")

                    doc_id = _as_str(_require(raw, "doc_id", "root"), "doc_id")
                    url = _as_str(_require(raw, "url", "root"), "url")
                    source_domain = _as_str(_require(raw, "source_domain", "root"), "source_domain")
                    fetched_at = _as_str(_require(raw, "fetched_at", "root"), "fetched_at")

                    crawl_raw = _require(raw, "crawl", "root")
                    if not isinstance(crawl_raw, dict):
                        raise InvalidDocumentError("crawl must be an object")
                    crawl = CrawlMeta(
                        depth=_as_int(_require(crawl_raw, "depth", "crawl"), "crawl.depth"),
                        parent_url=_as_opt_str(crawl_raw.get("parent_url"), "crawl.parent_url"),
                        seed_id=_as_str(_require(crawl_raw, "seed_id", "crawl"), "crawl.seed_id"),
                        seed_group=_as_str(_require(crawl_raw, "seed_group", "crawl"), "crawl.seed_group"),
                    )

                    content_raw = _require(raw, "content", "root")
                    if not isinstance(content_raw, dict):
                        raise InvalidDocumentError("content must be an object")

                    content = Content(
                        mime_type=_as_str(_require(content_raw, "mime_type", "content"), "content.mime_type"),
                        title=_as_opt_str(content_raw.get("title"), "content.title"),
                        sections=_parse_sections(_require(content_raw, "sections", "content")),
                        body=_as_str(_require(content_raw, "body", "content"), "content.body"),
                    )

                    page_meta = None
                    pm_raw = raw.get("page_meta")
                    if pm_raw is not None:
                        if not isinstance(pm_raw, dict):
                            raise InvalidDocumentError("page_meta must be an object|null")
                        page_meta = PageMeta(
                            published_at=_as_opt_str(pm_raw.get("published_at"), "page_meta.published_at"),
                            updated_at=_as_opt_str(pm_raw.get("updated_at"), "page_meta.updated_at"),
                            author=_as_opt_str(pm_raw.get("author"), "page_meta.author"),
                            language=_as_opt_str(pm_raw.get("language"), "page_meta.language"),
                        )

                    content_hash = _as_opt_str(raw.get("content_hash"), "content_hash")

                    yield AcquiredDocument(
                        doc_id=doc_id,
                        url=url,
                        source_domain=source_domain,
                        fetched_at=fetched_at,
                        crawl=crawl,
                        content=content,
                        page_meta=page_meta,
                        content_hash=content_hash,
                    )

                except Exception as e:
                    raise InvalidDocumentError(
                        f"[{path.name}:{line_no}] Documento inválido: {e}"
                    ) from e