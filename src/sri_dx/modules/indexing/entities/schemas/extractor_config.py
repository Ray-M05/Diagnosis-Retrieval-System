"""Pydantic config schema for Biomedical NER extractor.

Defines the configuration model used by `BiomedicalNEREntityExtractor`.
"""

from pydantic import BaseModel, Field


class BiomedicalNERExtractorConfig(BaseModel):
    """Configuration for `BiomedicalNEREntityExtractor`.

    Converted from the original dataclass to a Pydantic model for
    consistent schema validation inside module-local configs.
    """

    min_entity_chars: int = Field(default=2, ge=0, description="Minimum entity length in chars")
    max_entity_words: int = Field(default=10, ge=1, description="Maximum words in an entity span")
    deduplicate: bool = Field(default=True, description="Remove overlapping entities keeping highest confidence")
