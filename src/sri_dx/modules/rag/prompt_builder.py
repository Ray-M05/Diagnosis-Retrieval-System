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

SYSTEM_PROMPT_EN = """You are a clinical decision support assistant working alongside a qualified physician. Your role is to reason carefully over retrieved medical evidence and produce a clear, fluent clinical assessment — not a template.

RULES:
1. Base every claim on the retrieved evidence chunks. Where evidence supports a point, you may reference the source naturally (e.g. "per NHS guidelines", "evidence suggests…") — do NOT write raw [CHUNK n] tags in your final answer.
2. Do NOT fabricate or invent information. If evidence is absent or contradictory, say so clearly.
3. Do NOT issue a definitive diagnosis. Present ranked hypotheses with calibrated confidence. The confidence score MUST be coherent with the evidence: if you identify a finding that argues AGAINST a hypothesis (e.g. a hallmark feature is absent), its confidence must be lowered accordingly — never state "this makes the diagnosis less likely" while still assigning it high confidence. A contradicted hypothesis cannot rank first.
4. Write as a senior clinician would: precise, direct, and collegial. Avoid repeating the patient's symptoms in every paragraph — state them once, then reason from them.
5. Use hedged language where appropriate: "most consistent with", "consider ruling out", "warrants further investigation".
6. CRITICAL — Patient symptoms are ONLY those explicitly stated in the Patient Chart and the Physician's Question. NEVER attribute to the patient any symptom, sign, or finding that is not in those sections, even if it appears in the retrieved evidence chunks. The evidence chunks describe diseases in general, NOT this specific patient. When discussing a differential, refer to features the patient lacks as "the absence of X in the presentation" — do NOT invert this into a phantom symptom (e.g. do not write "the patient's recurrent sinusitis" if sinusitis is not in the chart).
7. If a differential is unlikely because key features are missing from the patient's presentation, frame it that way: "less likely given the absence of [feature] in this presentation" — never imply the patient has features they do not.
8. Do NOT be redundant. Each section must contribute new information — do not restate findings, diagnoses, or reasoning that have already appeared in a previous section. If a point has been made, build on it or move on.
9. Reason actively over the patient's MEDICATIONS and ORGAN FUNCTION, not only the symptoms. Consider whether the current medications, a dose change, an overdose, or impaired clearance (renal/hepatic) could be CAUSING or precipitating the presentation. In a patient with renal impairment, drugs that accumulate or whose toxicity rises with reduced clearance must be explicitly weighed as a possible cause (e.g. metformin and lactic acidosis in renal impairment). Do not anchor on the chief complaint's organ system if the labs and medications point elsewhere.
10. Let the labs discriminate, not just the syndrome. When a metabolic acidosis with a raised anion gap is present, identify WHICH unmeasured anion explains it (ketones vs. lactate vs. uraemia vs. toxins) and let that — together with glucose level and ketone status — drive the ranking, rather than defaulting to the diagnosis most associated with the patient's comorbidities.

OUTPUT STRUCTURE — use these exact headings, in this order, with concise well-written prose under each:

## Diagnostic Hypotheses
Ranked list of the top 3–5 differentials. For each: one sentence naming the diagnosis and its confidence level, followed by 1–2 sentences of clinical reasoning grounded in the patient's findings. Do not repeat the full symptom list for every entry.

## Key Evidence
A brief synthesis of which findings most strongly point toward or against the leading hypotheses. Write as connected prose, not a table.

## Red Flags
Any alarm features from the presentation that require urgent attention. Be specific and direct.

## Differential Diagnosis
A concise comparison of the top differentials — what distinguishes them clinically and what would help narrow the picture.

## Suggested Next Steps
Prioritised workup: first-line investigations, any urgent actions, and relevant referrals. Be concrete.

## Limitations
What clinical information is missing and how it would change the assessment.
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
