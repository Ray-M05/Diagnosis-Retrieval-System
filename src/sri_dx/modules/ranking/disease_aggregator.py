"""Agregación de chunks rankeados en un ranking de enfermedades.

Dado un conjunto de RetrievalResult (chunks rerankeados por cross-encoder),
extrae entidades NER con label PROBLEM (enfermedades), las agrupa por nombre
normalizado y produce un ranking de enfermedades ponderado por
rerank_score × ner_confidence.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sri_dx.core.schemas.search.disease_result import DiseaseEvidence, DiseaseResult

logger = logging.getLogger(__name__)


@dataclass
class DiseaseAggregatorConfig:
    """Configuración para la agregación de enfermedades."""

    min_ner_score: float = 0.5  # Confianza mínima de NER para considerar la entidad
    max_diseases: int = 10  # Máximo de enfermedades a retornar
    min_evidence_count: int = 1  # Mínimo de chunks para que una enfermedad califique


class DiseaseAggregator:
    """Agrega chunks rerankeados en un ranking de enfermedades.

    Fórmula de scoring:
        disease_score = Σ (chunk_rerank_score × ner_confidence_score)
    para todos los chunks que mencionan la enfermedad.
    """

    def __init__(self, config: Optional[DiseaseAggregatorConfig] = None) -> None:
        self.config = config or DiseaseAggregatorConfig()

    def aggregate(self, retrieval_results: list) -> List[DiseaseResult]:
        """Agrega resultados de chunks en un ranking de enfermedades.

        Args:
            retrieval_results: Lista de RetrievalResult del pipeline de dos etapas.

        Returns:
            Lista de DiseaseResult ordenada por aggregated_score descendente.
        """
        # disease_name_normalized → list of (evidence, display_name)
        disease_map: Dict[str, List[Tuple[DiseaseEvidence, str]]] = defaultdict(list)

        for result in retrieval_results:
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
                combined = result.rerank_score * ner_score

                evidence = DiseaseEvidence(
                    chunk_id=result.metadata.get("chunk_id", ""),
                    doc_id=result.doc_id,
                    rerank_score=result.rerank_score,
                    ner_score=ner_score,
                    combined_score=combined,
                    content_preview=(result.content or "")[:200],
                    url=result.metadata.get("url", ""),
                )
                disease_map[normalized].append((evidence, disease_text))

        # Construir DiseaseResult por cada enfermedad
        results: List[DiseaseResult] = []
        for normalized_name, entries in disease_map.items():
            if len(entries) < self.config.min_evidence_count:
                continue

            evidence_list = [ev for ev, _ in entries]
            evidence_list.sort(key=lambda e: e.combined_score, reverse=True)

            aggregated_score = sum(e.combined_score for e in evidence_list)

            # Display name: usar el texto del match con mayor combined_score
            best_display = entries[0][1]
            best_combined = entries[0][0].combined_score
            for ev, display in entries:
                if ev.combined_score > best_combined:
                    best_combined = ev.combined_score
                    best_display = display

            results.append(
                DiseaseResult(
                    disease_name=normalized_name,
                    disease_name_display=best_display,
                    aggregated_score=aggregated_score,
                    evidence_count=len(evidence_list),
                    evidence=evidence_list,
                )
            )

        # Ordenar por score descendente y asignar rank
        results.sort(key=lambda d: d.aggregated_score, reverse=True)
        for i, r in enumerate(results[: self.config.max_diseases]):
            r.rank = i + 1

        return results[: self.config.max_diseases]

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalización mínima del nombre de enfermedad."""
        return text.strip().lower()
