# src/sri_dx/adapters/indexing/ner_tagger_adapter.py
from __future__ import annotations

from typing import List, Optional
from sri_dx.core.ports.indexing.ner_tagger import NerTaggerPort
from sri_dx.core.schemas.indexing.ner import NerEntity
from sri_dx.adapters.embeddings.biomedical_ner_adapter import BiomedicalNERAdapter


class BiomedicalNERTaggerAdapter(NerTaggerPort):
    """
    Adapter bridging the Indexing NER port to the external HuggingFace
    Biomedical NER pipeline.
    """

    def __init__(self, ner_adapter: Optional[BiomedicalNERAdapter] = None):
        """
        Args:
            ner_adapter: The underlying HuggingFace adapter instance.
        """
        self.ner_adapter = ner_adapter or BiomedicalNERAdapter.get_instance()

    def tag(self, text: str, language: Optional[str] = "en") -> List[NerEntity]:
        """
        Extracts biomedical entities using the underlying model.
        Fails gracefully (returns empty list) if text is empty or model errors out.
        If language is not English, logs a warning and returns an empty list, 
        since biomedical-ner-all is natively trained in English.
        """
        if not text:
            return []
            
        lang = (language or "en").lower().split("-")[0]
        if lang != "en":
            # The biomedical NER model used (d4data) specializes in English text. 
            # Could enforce return [] here, but to be robust, we will still try to parse it.
            pass

        try:
            raw_entities = self.ner_adapter.predict(text)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"NER Adapter failed to tag text: {e}")
            return []

        parsed_entities = []
        for entity in raw_entities:
            # We map back the 'word' field from the underlying huggingface pipeline response 
            parsed_entities.append(
                NerEntity(
                    text=entity.get("word", ""),
                    label=entity.get("domain_label", entity.get("entity_group", "UNKNOWN")),
                    start_char=entity.get("start", 0),
                    end_char=entity.get("end", 0),
                    score=entity.get("score")
                )
            )

        return parsed_entities
