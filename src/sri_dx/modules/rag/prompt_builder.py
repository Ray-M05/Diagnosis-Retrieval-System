"""ClinicalPromptBuilder — builds the system + user prompt for the clinical RAG.

Design principles:
- The system prompt encodes the assistant role, strict citation rules, and the
  required output structure. It is fixed per request (good for caching).
- The user message contains: patient chart text, extracted entities summary,
  candidate diseases hint (from the NER aggregator), retrieved evidence chunks,
  and finally the physician's query.
- context_block (the formatted chunks) is kept as a separate attribute on
  BuiltPrompt so callers can handle it independently (e.g. for caching).

Output structure requested from the model (markdown):
  ## Diagnostic Hypotheses
  ## Key Evidence
  ## Red Flags
  ## Differential Diagnosis
  ## Suggested Next Steps
  ## Limitations
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sri_dx.core.schemas.search.disease_result import DiseaseResult
    from sri_dx.modules.rag.context_builder import ContextBlock
    from sri_dx.modules.rag.patient_chart_enricher import PatientChartEntities
    from sri_dx.core.schemas.rag.patient_chart import PatientChart


# ---------------------------------------------------------------------------
# System prompt (EN only in MVP)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_EN = """You are a clinical decision support assistant working alongside a qualified physician.

RULES — follow them strictly:
1. Cite every claim with [CHUNK n] referring to the evidence blocks provided. If a claim has no supporting chunk, say so explicitly.
2. Do NOT fabricate information, invent citations, or reference chunks not present in the evidence.
3. If the evidence is insufficient or contradictory, declare this openly.
4. Do NOT issue a definitive diagnosis — provide ranked hypotheses with confidence reasoning.
5. Tone: technically precise, clinically grounded, collegial. Assume the reader is a qualified physician.
6. When you are uncertain, say so. Prefer "likely", "consider", "rule out" over absolute statements.

REQUIRED OUTPUT STRUCTURE (use these exact markdown headings in this order):

## Diagnostic Hypotheses
List the top 3–5 differential diagnoses in ranked order. For each: name, brief rationale, supporting evidence citations.

## Key Evidence
Map the patient's specific findings (symptoms, vitals, labs) to the retrieved chunks that support or refute each hypothesis.

## Red Flags
Identify any alarm signs from the patient chart that require urgent attention.

## Differential Diagnosis
Brief table or list of alternative diagnoses to keep in mind, with distinguishing features.

## Suggested Next Steps
Recommended workup (labs, imaging, referrals) based on the hypotheses above.

## Limitations
What information is missing, ambiguous, or outside the scope of the retrieved evidence.
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BuiltPrompt:
    system: str
    user_message: str
    context_block: str   # the raw formatted chunks — kept separate for traceability


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class ClinicalPromptBuilder:
    """Pure function object — stateless, easy to test."""

    def build(
        self,
        chart: "PatientChart",
        entities: "PatientChartEntities",
        user_query: str,
        context_blocks: list["ContextBlock"],
        candidate_diseases: list["DiseaseResult"] | None = None,
    ) -> BuiltPrompt:
        context_block = self._format_context(context_blocks)
        user_message = self._build_user_message(
            chart, entities, user_query, context_block, candidate_diseases or []
        )
        return BuiltPrompt(
            system=SYSTEM_PROMPT_EN,
            user_message=user_message,
            context_block=context_block,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_context(blocks: list["ContextBlock"]) -> str:
        if not blocks:
            return "(No evidence retrieved from the corpus.)"
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

    @staticmethod
    def _format_diseases(diseases: list["DiseaseResult"]) -> str:
        if not diseases:
            return "(NER aggregator found no candidate diseases in the retrieved chunks.)"
        lines: list[str] = []
        for d in diseases[:5]:
            lines.append(f"  {d.rank}. {d.disease_name_display} (evidence chunks: {d.evidence_count})")
        return "\n".join(lines)

    def _build_user_message(
        self,
        chart: "PatientChart",
        entities: "PatientChartEntities",
        user_query: str,
        context_block: str,
        candidate_diseases: list["DiseaseResult"],
    ) -> str:
        sections: list[str] = []

        # 1. Patient chart
        chart_text = chart.to_clinical_text()
        sections.append(f"### Patient Chart\n{chart_text}")

        # 2. Extracted entities (NER summary — compact)
        entities_text = entities.summary()
        sections.append(f"### Extracted Clinical Entities\n{entities_text}")

        # 3. Candidate diseases from NER aggregator (hint, not ground truth)
        diseases_text = self._format_diseases(candidate_diseases)
        sections.append(
            f"### Candidate Diseases (NER aggregator — treat as hint only)\n{diseases_text}"
        )

        # 4. Retrieved evidence
        sections.append(f"### Retrieved Evidence\n{context_block}")

        # 5. Physician's question
        q = user_query.strip() or "What is your clinical assessment of this patient?"
        sections.append(f"### Physician's Question\n{q}")

        return "\n\n".join(sections)
