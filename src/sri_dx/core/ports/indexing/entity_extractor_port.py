# core/ports/indexing/entity_extractor_port.py
"""Port for clinical entity extraction strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from sri_dx.core.schemas.indexing.entity_schema import (
    ClinicalEntity,
    EntityExtractionConfig,
)


class EntityExtractorPort(ABC):
    """
    Port for clinical entity extraction strategies.

    Allows switching the model/strategy without affecting the pipeline.
    Possible implementations:
    - Bio_ClinicalBERT (NER)
    - ScispaCy
    - Dictionary + rules
    - LLM-based extraction
    """
    
    @abstractmethod
    def extract(
        self, 
        text: str, 
        config: Optional[EntityExtractionConfig] = None
    ) -> List[ClinicalEntity]:
        """
        Extracts clinical entities from a text.

        Args:
            text: Clinical text to process
            config: Extraction configuration

        Returns:
            List of entities found with their metadata
        """
    
    @abstractmethod
    def extract_batch(
        self, 
        texts: List[str], 
        config: Optional[EntityExtractionConfig] = None
    ) -> List[List[ClinicalEntity]]:
        """
        Extracts entities from multiple texts (optimised for GPU/batching).

        Args:
            texts: List of texts to process
            config: Extraction configuration

        Returns:
            List of entity lists (preserves input order)
        """
    
    @abstractmethod
    def get_supported_labels(self) -> List[str]:
        """
        Returns the entity types this extractor can identify.

        Returns:
            List of supported labels. E.g.: ['PROBLEM', 'TREATMENT', 'TEST']
        """
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name/identifier of the model in use."""
