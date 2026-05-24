"""Pydantic configuration schemas for the embedding generator.

These models are used within `sri_dx.modules.indexing` to maintain
consistency with other `core.schemas` and allow validation.
"""

from pydantic import BaseModel, Field


class EmbeddingGeneratorConfig(BaseModel):
    """Configuration for the embedding generator."""

    model_name: str = Field(default="Bio_ClinicalBERT", description="Model name")
    model_version: str = Field(default="1.0", description="Model version")
    embedding_dim: int = Field(default=768, ge=1, description="Embedding dimension")
    batch_size: int = Field(default=128, ge=1, description="Batch size for inference")
    text_preview_length: int = Field(default=200, ge=0, description="Text preview length")
    normalize_vectors: bool = Field(default=True, description="Normalize vectors after generation")
    device: str = Field(default="auto", description="Device: auto, cpu, cuda")
