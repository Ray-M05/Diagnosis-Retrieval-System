# adapters/embeddings/biomedical_ner_adapter.py
"""
Adaptador para d4data/biomedical-ner-all.

Este adaptador encapsula el pipeline de HuggingFace para NER biomédico.
"""

from __future__ import annotations

import logging
from dataclasses import field
from typing import List, Optional, Union, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from transformers import pipeline, Pipeline

logger = logging.getLogger(__name__)


# Mapa de etiquetas nativas del modelo → labels del dominio
LABEL_MAP: Dict[str, str] = {
    # Labels reales del modelo d4data/biomedical-ner-all
    "Disease_disorder": "PROBLEM",
    "Sign_symptom": "SYMPTOM",
    "Medication": "TREATMENT",
    "Therapeutic_procedure": "TREATMENT",
    "Diagnostic_procedure": "TEST",
    "Lab_value": "TEST",
    "Biological_structure": "ANATOMY",
    "Biological_attribute": "ANATOMY",
}


from .schemas.biomedical_ner_config import BiomedicalNERConfig


class BiomedicalNERAdapter:
    """Singleton adapter for the d4data biomedical NER pipeline."""

    _instance: Optional["BiomedicalNERAdapter"] = None
    _pipeline: Optional["Pipeline"] = None

    def __init__(self, config: Optional[BiomedicalNERConfig] = None) -> None:
        self.config = config or BiomedicalNERConfig()
        self._loaded = False

    @classmethod
    def get_instance(
        cls, config: Optional[BiomedicalNERConfig] = None
    ) -> "BiomedicalNERAdapter":
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        if cls._instance is not None:
            cls._instance._unload()
        cls._instance = None

    def _load(self) -> None:
        if self._loaded:
            return
        logger.info("Cargando pipeline NER '%s'...", self.config.model_name)
        from transformers import pipeline as hf_pipeline

        self._pipeline = hf_pipeline(
            task="ner",
            model=self.config.model_name,
            aggregation_strategy=self.config.aggregation_strategy,
            device=self.config.device,
            stride=self.config.stride,
        )
        self._loaded = True

    def _unload(self) -> None:
        self._pipeline = None
        self._loaded = False
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def predict(self, text: str) -> List[Dict[str, Any]]:
        self._load()
        raw: List[Dict[str, Any]] = self._pipeline(text)  # type: ignore[arg-type]
        return self._enrich(raw, text)

    def predict_batch(self, texts: List[str]) -> List[List[Dict[str, Any]]]:
        self._load()
        results: List[List[Dict[str, Any]]] = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            batch_output: List[List[Dict[str, Any]]] = self._pipeline(batch)  # type: ignore[arg-type]
            for raw_list, original_text in zip(batch_output, batch):
                results.append(self._enrich(raw_list, original_text))
        return results

    def map_label(self, entity_group: str) -> Optional[str]:
        return self.config.label_map.get(entity_group)

    def get_model_labels(self) -> List[str]:
        return list(self.config.label_map.keys())

    def get_domain_labels(self) -> List[str]:
        return sorted(set(self.config.label_map.values()))

    def _enrich(self, raw_spans: List[Dict[str, Any]], original_text: str = "") -> List[Dict[str, Any]]:
        # Paso 1: convertir spans con texto del original
        mapped = []
        for span in raw_spans:
            entity_group: str = span.get("entity_group", span.get("entity", ""))
            domain_label = self.config.label_map.get(entity_group)
            if domain_label is None:
                continue
            start, end = span["start"], span["end"]
            if original_text and start < len(original_text):
                word = original_text[start:end].strip()
            else:
                word = span["word"].replace(" ##", "").replace("##", "").strip()
            if len(word) < 2:
                continue
            mapped.append({
                "entity_group": entity_group,
                "domain_label": domain_label,
                "word": word,
                "score": float(span["score"]),
                "start": start,
                "end": end,
            })

        # Paso 2: fusionar entidades adyacentes del mismo tipo dentro del mismo
        # "phrase span" — abarca tokens partidos por el tokenizer subword
        # (ej: "Diabetic" + "ketoacidosis", "Pulmonary" + "embolism" partido en
        # "em" + "bolism"). Toleramos hasta 4 chars de gap para puentear
        # subtokens internos que el modelo etiquetó como O.
        merged: List[Dict[str, Any]] = []
        for ent in mapped:
            if (
                merged
                and merged[-1]["domain_label"] == ent["domain_label"]
                and 0 <= ent["start"] - merged[-1]["end"] <= 4
                and original_text
                and not original_text[merged[-1]["end"]:ent["start"]].strip().endswith((".", ",", ";", ":", "!", "?"))
            ):
                prev = merged[-1]
                prev["word"] = original_text[prev["start"]:ent["end"]].strip()
                prev["end"] = ent["end"]
                prev["score"] = max(prev["score"], ent["score"])
            else:
                merged.append(ent.copy())

        # Paso 3: filtrar entidades demasiado cortas
        return [e for e in merged if len(e["word"]) >= 3]
