"""PatientChartEnricher — extracts medical entities from a PatientChart.

Reuses:
- BiomedicalNERAdapter (singleton, d4data/biomedical-ner-all)
  predict(text) -> list[{domain_label, word, score, start, end}]
  domain_label values: PROBLEM, SYMPTOM, TREATMENT, TEST, ANATOMY
- ConceptExtractor (Aho-Corasick over LEXICON_EN)
  extract(text) -> list[concept_id str]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from sri_dx.core.schemas.rag.patient_chart import PatientChart

if TYPE_CHECKING:
    from sri_dx.adapters.embeddings.biomedical_ner_adapter import BiomedicalNERAdapter
    from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor

logger = logging.getLogger(__name__)


@dataclass
class PatientChartEntities:
    """Extracted medical entities from a PatientChart."""

    symptoms: list[str] = field(default_factory=list)      # PROBLEM + SYMPTOM labels
    treatments: list[str] = field(default_factory=list)    # TREATMENT label
    tests: list[str] = field(default_factory=list)         # TEST label
    anatomy: list[str] = field(default_factory=list)       # ANATOMY label
    concept_ids: list[str] = field(default_factory=list)   # lexicon concept IDs
    raw_ner: list[dict] = field(default_factory=list)      # full NER output for traceability

    def all_terms(self) -> list[str]:
        """All unique extracted terms (symptoms + treatments + tests + anatomy)."""
        seen: set[str] = set()
        result: list[str] = []
        for term in self.symptoms + self.treatments + self.tests + self.anatomy:
            if term not in seen:
                seen.add(term)
                result.append(term)
        return result

    def summary(self) -> str:
        """One-line summary for prompt injection."""
        parts: list[str] = []
        if self.symptoms:
            parts.append("Symptoms/Problems: " + ", ".join(self.symptoms[:8]))
        if self.treatments:
            parts.append("Treatments: " + ", ".join(self.treatments[:5]))
        if self.tests:
            parts.append("Tests: " + ", ".join(self.tests[:5]))
        if self.anatomy:
            parts.append("Anatomy: " + ", ".join(self.anatomy[:5]))
        if self.concept_ids:
            parts.append("Concept IDs: " + ", ".join(self.concept_ids[:10]))
        return "\n".join(parts) if parts else "No entities extracted."


class PatientChartEnricher:
    """Enrich a PatientChart with NER entities and concept IDs."""

    def __init__(
        self,
        ner_adapter: Optional["BiomedicalNERAdapter"] = None,
        concept_extractor: Optional["ConceptExtractor"] = None,
    ) -> None:
        self._ner = ner_adapter
        self._concepts = concept_extractor

    def _get_ner(self) -> "BiomedicalNERAdapter":
        if self._ner is None:
            from sri_dx.adapters.embeddings.biomedical_ner_adapter import BiomedicalNERAdapter
            self._ner = BiomedicalNERAdapter.get_instance()
        return self._ner

    def _get_concepts(self) -> "ConceptExtractor":
        if self._concepts is None:
            from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
            self._concepts = ConceptExtractor()
        return self._concepts

    def enrich(self, chart: PatientChart) -> PatientChartEntities:
        """Run NER and concept extraction over the chart's clinical text."""
        text = chart.to_clinical_text()
        if not text.strip():
            return PatientChartEntities()

        # NER
        raw_ner: list[dict] = []
        symptoms: list[str] = []
        treatments: list[str] = []
        tests: list[str] = []
        anatomy: list[str] = []

        try:
            raw_ner = self._get_ner().predict(text)
        except Exception as exc:
            logger.warning("NER prediction failed: %s", exc)

        seen: set[str] = set()
        for ent in raw_ner:
            word = ent.get("word", "").strip()
            label = ent.get("domain_label", "")
            if not word or word in seen:
                continue
            seen.add(word)
            if label in ("PROBLEM", "SYMPTOM"):
                symptoms.append(word)
            elif label == "TREATMENT":
                treatments.append(word)
            elif label == "TEST":
                tests.append(word)
            elif label == "ANATOMY":
                anatomy.append(word)

        # Also fold explicit symptoms / medications from the chart itself
        # (they were structured by the parser; NER may miss abbreviations)
        for s in chart.symptoms:
            if s and s not in seen:
                seen.add(s)
                symptoms.append(s)
        for m in chart.current_medications:
            if m and m not in seen:
                seen.add(m)
                treatments.append(m)

        # Concept IDs (Aho-Corasick lexicon)
        concept_ids: list[str] = []
        try:
            concept_ids = self._get_concepts().extract(text)
        except Exception as exc:
            logger.warning("Concept extraction failed: %s", exc)

        return PatientChartEntities(
            symptoms=symptoms,
            treatments=treatments,
            tests=tests,
            anatomy=anatomy,
            concept_ids=concept_ids,
            raw_ner=raw_ner,
        )
