# modules/indexing/entities/biomedical_ner_extractor.py
"""
Extractor de Entidades Clínicas usando d4data/biomedical-ner-all.

Implementación del EntityExtractorPort que usa un modelo NER nativo
para identificar entidades biomédicas.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, TYPE_CHECKING

from sri_dx.core.ports.indexing.entity_extractor_port import (
    EntityExtractorPort,
    ClinicalEntity,
    EntityExtractionConfig,
)

if TYPE_CHECKING:
    from sri_dx.adapters.embeddings.biomedical_ner_adapter import BiomedicalNERAdapter

logger = logging.getLogger(__name__)


from .schemas.extractor_config import BiomedicalNERExtractorConfig


class BiomedicalNEREntityExtractor(EntityExtractorPort):
    """Entity extractor backed by the d4data/biomedical-ner-all model."""

    SUPPORTED_LABELS = ["PROBLEM", "TREATMENT", "TEST", "ANATOMY"]

    def __init__(
        self,
        extractor_config: Optional[BiomedicalNERExtractorConfig] = None,
        ner_adapter: Optional["BiomedicalNERAdapter"] = None,
    ) -> None:
        self.extractor_config = extractor_config or BiomedicalNERExtractorConfig()
        self._ner_adapter = ner_adapter

    @property
    def ner_adapter(self) -> "BiomedicalNERAdapter":
        if self._ner_adapter is None:
            from sri_dx.adapters.embeddings.biomedical_ner_adapter import (
                BiomedicalNERAdapter,
            )
            self._ner_adapter = BiomedicalNERAdapter.get_instance()
        return self._ner_adapter

    @property
    def model_name(self) -> str:
        return "d4data/biomedical-ner-all"

    def get_supported_labels(self) -> List[str]:
        return self.SUPPORTED_LABELS.copy()

    def extract(self, text: str, config: Optional[EntityExtractionConfig] = None) -> List[ClinicalEntity]:
        config = config or EntityExtractionConfig()
        raw_spans = self.ner_adapter.predict(text)
        entities = self._spans_to_entities(raw_spans, config)
        return entities

    def extract_batch(self, texts: List[str], config: Optional[EntityExtractionConfig] = None) -> List[List[ClinicalEntity]]:
        config = config or EntityExtractionConfig()
        all_raw = self.ner_adapter.predict_batch(texts)
        return [self._spans_to_entities(raw, config) for raw in all_raw]

    def _spans_to_entities(self, raw_spans: List[dict], config: EntityExtractionConfig) -> List[ClinicalEntity]:
        labels_to_extract = config.labels_to_extract or self.SUPPORTED_LABELS
        labels_to_extract = [lbl for lbl in labels_to_extract if lbl in self.SUPPORTED_LABELS]

        entities: List[ClinicalEntity] = []

        for span in raw_spans:
            domain_label: str = span["domain_label"]
            if domain_label not in labels_to_extract:
                continue
            word: str = span["word"].strip()
            if len(word) < self.extractor_config.min_entity_chars:
                continue
            if len(word.split()) > self.extractor_config.max_entity_words:
                continue

            entity = ClinicalEntity(
                text=word,
                label=domain_label,
                start_char=span["start"],
                end_char=span["end"],
                confidence=span["score"],
                normalized_text=self._normalize_text(word),
                metadata={
                    "extraction_method": "ner",
                    "model": self.model_name,
                    "native_label": span.get("entity_group"),
                },
            )
            entities.append(entity)

        if self.extractor_config.deduplicate:
            entities = self._deduplicate(entities)

        entities = [e for e in entities if e.confidence >= config.min_confidence]
        entities.sort(key=lambda e: e.start_char)
        return entities

    def _deduplicate(self, entities: List[ClinicalEntity]) -> List[ClinicalEntity]:
        if not entities:
            return entities
        sorted_ents = sorted(entities, key=lambda e: -e.confidence)
        accepted: List[ClinicalEntity] = []
        for candidate in sorted_ents:
            overlaps = any(
                not (
                    candidate.end_char <= accepted_ent.start_char
                    or candidate.start_char >= accepted_ent.end_char
                )
                for accepted_ent in accepted
            )
            if not overlaps:
                accepted.append(candidate)
        return accepted

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.lower()
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
        return text
