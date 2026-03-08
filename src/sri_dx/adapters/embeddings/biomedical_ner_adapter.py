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
    "Disease":   "PROBLEM",
    "Chemical":  "TREATMENT",
    "Gene":      "TEST",
    "Species":   "ANATOMY",
    "Mutation":  "PROBLEM",
    "CellLine":  "ANATOMY",
    "CellType":  "ANATOMY",
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
        return self._enrich(raw)

    def predict_batch(self, texts: List[str]) -> List[List[Dict[str, Any]]]:
        self._load()
        results: List[List[Dict[str, Any]]] = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            batch_output: List[List[Dict[str, Any]]] = self._pipeline(batch)  # type: ignore[arg-type]
            for raw_list in batch_output:
                results.append(self._enrich(raw_list))
        return results

    def map_label(self, entity_group: str) -> Optional[str]:
        return self.config.label_map.get(entity_group)

    def get_model_labels(self) -> List[str]:
        return list(self.config.label_map.keys())

    def get_domain_labels(self) -> List[str]:
        return sorted(set(self.config.label_map.values()))

    def _enrich(self, raw_spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []
        for span in raw_spans:
            entity_group: str = span.get("entity_group", span.get("entity", ""))
            domain_label = self.config.label_map.get(entity_group)
            if domain_label is None:
                logger.debug("Etiqueta sin mapeo ignorada: '%s'", entity_group)
                continue
            enriched.append(
                {
                    "entity_group": entity_group,
                    "domain_label": domain_label,
                    "word": span["word"],
                    "score": float(span["score"]),
                    "start": span["start"],
                    "end": span["end"],
                }
            )
        return enriched
