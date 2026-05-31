"""Aggregation of ranked chunks into a disease ranking.

Given a set of RetrievalResult objects (chunks reranked by the cross-encoder),
extracts NER entities with the PROBLEM label (diseases), groups them by
normalised name and produces a disease ranking weighted by
rerank_score × ner_confidence.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sri_dx.core.ports.search.disease_normalizer_port import DiseaseNormalizerPort
from sri_dx.core.schemas.search.disease_result import DiseaseEvidence, DiseaseResult

__all__ = ["DiseaseAggregator", "DiseaseAggregatorConfig", "DiseaseNormalizerPort"]

logger = logging.getLogger(__name__)

# Single-word tokens that BioBERT-NER tags as PROBLEM but are not standalone
# diagnoses (anatomy, symptoms, generic clinical words). Multi-word phrases
# containing these are still valid (e.g. "pulmonary embolism", "coronary
# artery disease"). Valid single-word diseases like "pneumonia",
# "tuberculosis", "acromegaly" are NOT in this list.
_SINGLE_WORD_NOISE: frozenset[str] = frozenset({
    # anatomy / tissue
    "blood", "heart", "lung", "lungs", "kidney", "kidneys", "liver", "brain",
    "artery", "vein", "vessel", "tissue", "muscle", "bone", "joint",
    "pulmonary", "cardiac", "hepatic", "renal", "cerebral", "vascular",
    "coronary", "arterial", "venous", "respiratory", "intestinal", "gastric",
    "collarbone", "shoulder", "knee", "hip", "wrist", "ankle", "spine",
    # symptoms (not diseases)
    "pain", "chest", "cough", "fever", "fatigue", "dyspnea", "dyspnoea",
    "tachycardia", "hypoxia", "hypoxemia", "syncope", "nausea", "vomiting",
    "swelling", "edema", "oedema", "rash", "bleeding",
    # generic disease words (need a qualifier to be meaningful)
    "infection", "inflammation", "disorder", "disease", "syndrome",
    "condition", "abnormality", "failure", "insufficiency", "deficiency",
    "lesion", "mass", "nodule", "effusion", "stenosis", "occlusion",
    "thrombus", "clot", "embolus", "emboli", "infarct",
    "cancer", "tumor", "tumour", "neoplasm", "carcinoma",
    "necrosis",
    "fracture", "injury", "trauma", "wound",
    # adjectives / qualifiers (no diagnostic value alone)
    "acute", "chronic", "bilateral", "unilateral",
    "broken", "injured", "infected", "inflamed", "swollen", "ruptured",
    "torn", "bruised", "damaged", "affected", "impaired",
})


# Boilerplate section headings that are never a disease name. Used to avoid
# orphan cards titled "Overview", "Summary", etc. when NER finds nothing.
_GENERIC_HEADINGS: frozenset[str] = frozenset({
    "overview", "summary", "introduction", "description", "main",
    "symptoms", "causes", "diagnosis", "treatment", "prevention",
    "symptoms and causes", "signs and symptoms", "about", "general",
    "complications", "risk factors", "when to see a doctor", "outlook",
    "definition", "background", "epidemiology",
})


# Common acronyms -> canonical name (local expansion, no network call)
_ACRONYM_MAP: Dict[str, str] = {
    "uti": "urinary tract infection",
    "utis": "urinary tract infection",
    "dka": "diabetic ketoacidosis",
    "copd": "chronic obstructive pulmonary disease",
    "chf": "congestive heart failure",
    "cad": "coronary artery disease",
    "ckd": "chronic kidney disease",
    "htn": "hypertension",
    "mi": "myocardial infarction",
    "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism",
    "tb": "tuberculosis",
    "hiv": "human immunodeficiency virus",
    "aids": "acquired immunodeficiency syndrome",
    "ms": "multiple sclerosis",
    "ra": "rheumatoid arthritis",
    "sle": "systemic lupus erythematosus",
    "gerd": "gastroesophageal reflux disease",
    "ibs": "irritable bowel syndrome",
    "afib": "atrial fibrillation",
    "t2dm": "type 2 diabetes mellitus",
    "t1dm": "type 1 diabetes mellitus",
}



@dataclass
class DiseaseAggregatorConfig:
    """Configuration for disease aggregation."""

    min_ner_score: float = 0.5  # Minimum NER confidence to consider an entity
    max_diseases: int = 10  # Maximum number of diseases to return
    min_evidence_count: int = 1  # Minimum number of chunks for a disease to qualify
    # When a chunk's text yields no PROBLEM entity, fall back to NER run on its
    # heading/title (see TwoStageRetrievalPipeline._apply_ner_to_results, which
    # stores those under metadata["ner_entities_title"]). If that also fails,
    # the chunk is grouped in a title-keyed orphan bucket so it still produces a
    # card. Set to False to restore the legacy "drop chunks without NER" path.
    title_fallback: bool = True


class DiseaseAggregator:
    """Aggregates reranked chunks into a disease ranking.

    Ranks diseases by their best (earliest) position in the cross-encoder ranking.
    Each disease is ranked by its highest (earliest) position and the number of
    chunks in which it is mentioned.
    """

    def __init__(
        self,
        config: Optional[DiseaseAggregatorConfig] = None,
        normalizer: Optional[DiseaseNormalizerPort] = None,
    ) -> None:
        self.config = config or DiseaseAggregatorConfig()
        self._normalizer = normalizer

    def aggregate(self, retrieval_results: list) -> List[DiseaseResult]:
        """Aggregates chunk results into a disease ranking.

        Args:
            retrieval_results: List of RetrievalResult from the two-stage pipeline.

        Returns:
            List of DiseaseResult ordered by best position in the ranking.
        """
        # disease_name_normalized → list of (evidence, display_name, position, from_ner)
        disease_map: Dict[str, List[Tuple[DiseaseEvidence, str, int, bool]]] = defaultdict(list)

        for position, result in enumerate(retrieval_results):
            meta = result.metadata or {}
            section_heading = str(meta.get("section_heading") or "")
            title = str(meta.get("title") or "")

            # One chunk contributes to EXACTLY ONE disease: the highest-scoring
            # PROBLEM entity that passes all filters. This guarantees chunk-to-
            # disease is 1:1 in the final ranking.
            best = self._best_problem(meta.get("ner_entities", []))

            # Fallback 1: NER over the chunk's heading/title (pre-computed in a
            # single batch by the pipeline) when the text yielded no PROBLEM.
            if best is None and self.config.title_fallback:
                best = self._best_problem(meta.get("ner_entities_title", []))

            from_ner = best is not None
            if best is not None:
                ner_score, disease_text, normalized = best
            elif self.config.title_fallback:
                # Fallback 2: orphan chunk (no PROBLEM entity). Derive the disease
                # from the document title/URL and group by its NORMALISED form so
                # that (a) several headingless chunks of the same condition merge
                # into one card, and (b) they merge with NER-detected chunks of
                # the same disease (e.g. doc-title "Acromegaly - Symptoms and
                # causes" → "acromegaly" → same bucket as the NER "acromegaly").
                display = self._orphan_display(
                    title=title,
                    url=str(meta.get("url") or ""),
                    section_heading=section_heading,
                )
                if not display:
                    continue
                normalized = self._normalize(display, self._normalizer)
                if not normalized:
                    continue
                ner_score = 0.0
                disease_text = display
            else:
                # Legacy behavior: drop chunks without a PROBLEM entity.
                continue

            evidence = DiseaseEvidence(
                chunk_id=meta.get("chunk_id", ""),
                doc_id=result.doc_id,
                rerank_score=result.rerank_score,
                ner_score=ner_score,
                combined_score=ner_score,
                content_preview=(result.content or "")[:200],
                url=meta.get("url", ""),
                title=title,
                section_heading=section_heading,
            )
            disease_map[normalized].append((evidence, disease_text, position, from_ner))

        # Build one DiseaseResult per disease
        results: List[DiseaseResult] = []
        for normalized_name, entries in disease_map.items():
            if len(entries) < self.config.min_evidence_count:
                continue

            # Best (earliest) position in the ranking
            best_position = min(pos for _, _, pos, _ in entries)
            evidence_list = [ev for ev, _, _, _ in entries]

            # Display name: use the one from the chunk with the best position
            best_display = normalized_name
            for ev, display, pos, _ in entries:
                if pos == best_position:
                    best_display = display
                    break

            # The disease is NER-backed if ANY of its chunks matched a real
            # PROBLEM entity (vs. all coming from the title/URL fallback).
            disease_from_ner = any(fn for _, _, _, fn in entries)

            results.append(
                DiseaseResult(
                    disease_name=normalized_name,
                    disease_name_display=best_display,
                    aggregated_score=float(best_position),
                    evidence_count=len(evidence_list),
                    evidence=evidence_list,
                    from_ner=disease_from_ner,
                )
            )

        # Sort by best position (lower = better)
        results.sort(key=lambda d: d.aggregated_score)
        for i, r in enumerate(results[: self.config.max_diseases]):
            r.rank = i + 1

        return results[: self.config.max_diseases]

    def _orphan_display(self, *, title: str, url: str, section_heading: str) -> str:
        """Pick a human display name for an orphan chunk (no PROBLEM entity).

        Generic boilerplate headings are never a disease, so they are skipped in
        favor of the document title or a URL-derived name.
        """
        from sri_dx.modules.indexing.title import title_from_url

        t = (title or "").strip()
        if t:
            return t
        from_url = title_from_url(url)
        if from_url:
            return from_url
        sh = (section_heading or "").strip()
        if sh and sh.lower() not in _GENERIC_HEADINGS:
            return sh
        return ""

    def _best_problem(
        self, ner_entities: list
    ) -> Optional[Tuple[float, str, str]]:
        """Return (ner_score, disease_text, normalized) for the highest-scoring
        PROBLEM entity passing all filters, or None if none qualifies."""
        best: Optional[Tuple[float, str, str]] = None
        for entity in ner_entities or []:
            if entity.get("label", "") != "PROBLEM":
                continue

            ner_score = float(entity.get("score", 0.0))
            if ner_score < self.config.min_ner_score:
                continue

            disease_text = entity.get("text", "").strip()
            if not disease_text:
                continue

            # Strip dangling open/close punctuation (e.g. "Pulmonary embolism (PE")
            disease_text = re.sub(r"^[\s\(\[\{<]+|[\s\)\]\}>]+$", "", disease_text).strip()
            if not disease_text:
                continue

            # Filter single-word noise (anatomy/symptoms/generic terms).
            # Multi-word entities always pass through.
            words = disease_text.split()
            if len(words) == 1 and disease_text.lower() in _SINGLE_WORD_NOISE:
                continue

            normalized = self._normalize(disease_text, self._normalizer)
            if not normalized:
                continue

            if best is None or ner_score > best[0]:
                best = (ner_score, disease_text, normalized)
        return best

    @staticmethod
    def _normalize(text: str, normalizer: Optional[DiseaseNormalizerPort] = None) -> str:
        name = text.strip().lower()
        name = re.sub(r"^\d+\s+", "", name)
        # Strip doc-title boilerplate suffixes so a document title like
        # "Acromegaly - Symptoms and causes" or "Type 1 Diabetes Mellitus -
        # Endocrinology - MSD Manual ..." normalises to the disease itself and
        # merges with the NER-detected bucket of the same condition.
        name = re.split(
            r"\s*[-–|]\s*(symptoms?\b|signs?\b|causes?\b|diagnosis\b|treatment\b|"
            r"overview\b|endocrinology\b|pulmonology\b|cardiology\b|neurology\b|"
            r"msd manual\b|mayo clinic\b)",
            name,
        )[0].strip()
        name = re.sub(r"\s+(symptoms?|signs?|disease|disorder|syndrome)\s*$", "", name)
        name = name.strip()
        if name in _ACRONYM_MAP:
            name = _ACRONYM_MAP[name]
        if normalizer is not None:
            name = normalizer.normalize(name)
        return name
