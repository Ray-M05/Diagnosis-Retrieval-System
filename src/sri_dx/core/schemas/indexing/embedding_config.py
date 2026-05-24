# core/schemas/indexing/embedding_config.py
"""Configuration for embedding generation."""

from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model_name: str = Field(
        default="Bio_ClinicalBERT",
        description="Embedding model name"
    )

    embedding_dim: int = Field(
        default=768,
        description="Output vector dimensionality"
    )

    normalize: bool = Field(
        default=True,
        description="If true, normalises vectors to unit norm"
    )

    batch_size: int = Field(
        default=32,
        description="Batch size for processing"
    )

    max_length: int = Field(
        default=512,
        description="Maximum sequence length in tokens"
    )
