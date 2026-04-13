"""Agregación de chunks rankeados en un ranking de enfermedades.

Dado un conjunto de RetrievalResult (chunks rerankeados por cross-encoder),
extrae entidades NER con label PROBLEM (enfermedades), las agrupa por nombre
normalizado y produce un ranking de enfermedades ponderado por
rerank_score × ner_confidence.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sri_dx.core.schemas.search.disease_result import DiseaseEvidence, DiseaseResult

logger = logging.getLogger(__name__)

# Acrónimos comunes → nombre canónico
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
    """Configuración para la agregación de enfermedades."""

    min_ner_score: float = 0.5  # Confianza mínima de NER para considerar la entidad
    max_diseases: int = 10  # Máximo de enfermedades a retornar
    min_evidence_count: int = 1  # Mínimo de chunks para que una enfermedad califique


class DiseaseAggregator:
    """Agrega chunks rerankeados en un ranking de enfermedades.

    Ranking por mejor posición en el ranking del cross-encoder.
    Cada enfermedad se rankea por la posición más alta (más temprana)
    en la que aparece y se cuenta la cantidad de chunks donde se menciona.
    """

    def __init__(self, config: Optional[DiseaseAggregatorConfig] = None) -> None:
        self.config = config or DiseaseAggregatorConfig()

    def aggregate(self, retrieval_results: list) -> List[DiseaseResult]:
        """Agrega resultados de chunks en un ranking de enfermedades.

        Args:
            retrieval_results: Lista de RetrievalResult del pipeline de dos etapas.

        Returns:
            Lista de DiseaseResult ordenada por mejor posición en el ranking.
        """
        # disease_name_normalized → list of (evidence, display_name, position)
        disease_map: Dict[str, List[Tuple[DiseaseEvidence, str, int]]] = defaultdict(list)

        for position, result in enumerate(retrieval_results):
            ner_entities = (result.metadata or {}).get("ner_entities", [])
            if not ner_entities:
                continue

            for entity in ner_entities:
                label = entity.get("label", "")
                if label != "PROBLEM":
                    continue

                ner_score = float(entity.get("score", 0.0))
                if ner_score < self.config.min_ner_score:
                    continue

                disease_text = entity.get("text", "").strip()
                if not disease_text:
                    continue

                normalized = self._normalize(disease_text)

                evidence = DiseaseEvidence(
                    chunk_id=result.metadata.get("chunk_id", ""),
                    doc_id=result.doc_id,
                    rerank_score=result.rerank_score,
                    ner_score=ner_score,
                    combined_score=ner_score,
                    content_preview=(result.content or "")[:200],
                    url=result.metadata.get("url", ""),
                )
                disease_map[normalized].append((evidence, disease_text, position))

        # Construir DiseaseResult por cada enfermedad
        results: List[DiseaseResult] = []
        for normalized_name, entries in disease_map.items():
            if len(entries) < self.config.min_evidence_count:
                continue

            # Mejor posición (más temprana) en el ranking
            best_position = min(pos for _, _, pos in entries)
            evidence_list = [ev for ev, _, _ in entries]

            # Display name: usar el del chunk con mejor posición
            best_display = normalized_name
            for ev, display, pos in entries:
                if pos == best_position:
                    best_display = display
                    break

            results.append(
                DiseaseResult(
                    disease_name=normalized_name,
                    disease_name_display=best_display,
                    aggregated_score=float(best_position),
                    evidence_count=len(evidence_list),
                    evidence=evidence_list,
                )
            )

        # Ordenar por mejor posición (menor = mejor)
        results.sort(key=lambda d: d.aggregated_score)
        for i, r in enumerate(results[: self.config.max_diseases]):
            r.rank = i + 1

        return results[: self.config.max_diseases]

    @staticmethod
    def _normalize(text: str) -> str:
        """Normaliza nombre de enfermedad: lowercase, limpia prefijos numéricos,
        resuelve acrónimos y aplica deduplicación por contenido."""
        name = text.strip().lower()
        # Quitar prefijos numéricos (ej: "1 diabetes symptoms" → "diabetes symptoms")
        name = re.sub(r"^\d+\s+", "", name)
        # Quitar sufijos genéricos (ej: "diabetes symptoms" → "diabetes")
        name = re.sub(r"\s+(symptoms?|signs?|disease|disorder|syndrome)\s*$", "", name)
        name = name.strip()
        # Resolver acrónimos
        if name in _ACRONYM_MAP:
            name = _ACRONYM_MAP[name]
        return name
