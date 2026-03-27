"""Schemas para resultados de diagnóstico agrupados por enfermedad."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DiseaseEvidence:
    """Un chunk que menciona una enfermedad específica."""

    chunk_id: str
    doc_id: str
    rerank_score: float
    ner_score: float
    combined_score: float  # rerank_score * ner_score
    content_preview: str
    url: str


@dataclass
class DiseaseResult:
    """Enfermedad rankeada con evidencia de soporte."""

    disease_name: str  # Normalizado (lowercase, stripped)
    disease_name_display: str  # Texto original del mejor NER match
    aggregated_score: float  # sum(combined_score) de toda la evidencia
    evidence_count: int
    evidence: List[DiseaseEvidence] = field(default_factory=list)
    rank: int = 0  # Posición 1-based en el ranking final

    def __str__(self) -> str:
        lines = [
            f"#{self.rank} - {self.disease_name_display} (score: {self.aggregated_score:.4f})",
            f"  Evidencia: {self.evidence_count} chunk(s)",
        ]
        for ev in self.evidence[:3]:
            lines.append(
                f"    - chunk={ev.chunk_id}, rerank={ev.rerank_score:.4f}, "
                f"ner={ev.ner_score:.4f}, combined={ev.combined_score:.4f}"
            )
        if self.evidence_count > 3:
            lines.append(f"    ... y {self.evidence_count - 3} más")
        return "\n".join(lines)
