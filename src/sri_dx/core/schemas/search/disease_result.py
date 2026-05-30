"""Schemas for diagnosis results grouped by disease."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DiseaseEvidence:
    """A chunk that mentions a specific disease."""

    chunk_id: str
    doc_id: str
    rerank_score: float
    ner_score: float
    combined_score: float  # rerank_score * ner_score (not currently multiplied; kept for future use)
    content_preview: str
    url: str
    # Header context carried from the chunk so cards always have a heading to
    # show below the aggregation, even when the doc title is empty.
    title: str = ""
    section_heading: str = ""


@dataclass
class DiseaseResult:
    """Ranked disease with supporting evidence."""

    disease_name: str  # Normalized form (lowercase, stripped)
    disease_name_display: str  # Original text from the best NER match
    aggregated_score: float  # Aggregated score across all evidence
    evidence_count: int
    evidence: List[DiseaseEvidence] = field(default_factory=list)
    rank: int = 0  # 1-based position in the final ranking

    def __str__(self) -> str:
        lines = [
            f"#{self.rank} - {self.disease_name_display} (score: {self.aggregated_score:.4f})",
            f"  Evidence: {self.evidence_count} chunk(s)",
        ]
        for ev in self.evidence[:3]:
            lines.append(
                f"    - chunk={ev.chunk_id}, rerank={ev.rerank_score:.4f}, "
                f"ner={ev.ner_score:.4f}, combined={ev.combined_score:.4f}"
            )
        if self.evidence_count > 3:
            lines.append(f"    ... and {self.evidence_count - 3} more")
        return "\n".join(lines)
