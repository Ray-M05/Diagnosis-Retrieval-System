"""ContextBuilder — selects and formats retrieved chunks for LLM injection.

Takes a list of RetrievalResult (from TwoStageRetrievalPipeline) and produces
a list of ContextBlock objects, respecting:
  - max_chunks cap
  - deduplication by doc_id (diversity across documents)
  - per-chunk character truncation at sentence boundaries
  - global character budget (fits within llama3.1:8b 8K context)

The formatted string from format_for_prompt() is what gets injected into the
LLM prompt. Each block is labelled [CHUNK n] so citations are traceable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sri_dx.usecases.search.two_stage_retrieval_pipeline import RetrievalResult


@dataclass
class ContextBlock:
    index: int           # 1-based; matches [CHUNK n] in the prompt
    chunk_id: str
    doc_id: str
    url: str
    source_domain: str
    section_heading: str
    text: str            # truncated chunk text, ready for prompt


@dataclass
class ContextBuilderConfig:
    max_chunks: int = 10
    max_chars_per_chunk: int = 1200
    max_total_chars: int = 12_000   # ~3k tokens; leaves room for system + user + response
    dedupe_by: str = "doc_id"       # field to use for diversity dedup
    max_per_doc: int = 2            # max consecutive chunks from the same doc_id


class ContextBuilder:

    def __init__(self, config: ContextBuilderConfig | None = None) -> None:
        self.cfg = config or ContextBuilderConfig()

    def build(self, retrieval_results: list["RetrievalResult"]) -> list[ContextBlock]:
        """
        Select, deduplicate, and truncate results into ContextBlocks.

        Already ordered by rerank_score descending (pipeline guarantees this).
        We apply a greedy diversity pass: no more than cfg.max_per_doc chunks
        from the same doc_id.
        """
        blocks: list[ContextBlock] = []
        doc_counts: dict[str, int] = {}
        total_chars = 0

        for result in retrieval_results:
            if len(blocks) >= self.cfg.max_chunks:
                break
            if total_chars >= self.cfg.max_total_chars:
                break

            doc_id = result.doc_id
            if doc_counts.get(doc_id, 0) >= self.cfg.max_per_doc:
                continue

            # Extract text from result
            text = self._get_text(result)
            if not text.strip():
                continue

            # Truncate to budget
            text = self._truncate(text, self.cfg.max_chars_per_chunk)
            remaining = self.cfg.max_total_chars - total_chars
            if len(text) > remaining:
                text = self._truncate(text, remaining)
            if not text.strip():
                continue

            meta = result.metadata or {}
            block = ContextBlock(
                index=len(blocks) + 1,
                chunk_id=meta.get("chunk_id", result.doc_id),
                doc_id=doc_id,
                url=meta.get("url", ""),
                source_domain=meta.get("source_domain", ""),
                section_heading=meta.get("section_heading", ""),
                text=text,
            )
            blocks.append(block)
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            total_chars += len(text)

        return blocks

    def format_for_prompt(self, blocks: list[ContextBlock]) -> str:
        """
        Produce the injected context string.

        Format per block:
            [CHUNK n | source=<domain> | section=<heading> | url=<url>]
            <text>
        """
        parts: list[str] = []
        for b in blocks:
            header = f"[CHUNK {b.index}"
            if b.source_domain:
                header += f" | source={b.source_domain}"
            if b.section_heading:
                header += f" | section={b.section_heading}"
            if b.url:
                header += f" | url={b.url}"
            header += "]"
            parts.append(f"{header}\n{b.text}")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_text(result: "RetrievalResult") -> str:
        """Prefer result.content; fall back to metadata fields."""
        if result.content:
            return result.content
        meta = result.metadata or {}
        return meta.get("chunk_text", meta.get("content", meta.get("text", "")))

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Truncate at max_chars, preferring a sentence boundary."""
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars]
        # Try to cut at last sentence-ending punctuation
        m = re.search(r"[.!?]\s", cut[::-1])
        if m and m.start() < 300:   # don't cut too aggressively
            cut = cut[: max_chars - m.start()].rstrip()
        else:
            # Fall back to last whitespace
            last_space = cut.rfind(" ")
            if last_space > max_chars // 2:
                cut = cut[:last_space]
        return cut.rstrip()
