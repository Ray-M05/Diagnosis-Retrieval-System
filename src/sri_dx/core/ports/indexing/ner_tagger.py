# src/sri_dx/core/ports/indexing/ner_tagger.py
from __future__ import annotations

from typing import Protocol, List, Optional
from sri_dx.core.schemas.indexing.ner import NerEntity


class NerTaggerPort(Protocol):
    """
    Port for Named Entity Recognition tagging.
    Should be implemented by adapters wrapping concrete NER models.
    """

    def tag(self, text: str, language: Optional[str] = "en") -> List[NerEntity]:
        """
        Extract entities from text and return normalized NerEntity objects.

        Args:
            text: The unstructured text to extract entities from.
            language: Expected language of the text. E.g. "en" or "es".
        """
        ...
