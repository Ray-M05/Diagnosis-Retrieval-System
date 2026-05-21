# core/schemas/indexing/chunk_config.py
"""Configuration for chunking strategies."""

from pydantic import BaseModel, Field
from typing import Optional


class ChunkingConfig(BaseModel):
    """Configuration for a chunking strategy."""

    chunk_size: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Maximum chunk size in tokens"
    )

    strategy: str = Field(
        default="sliding_window",
        description="Strategy: sliding_window, semantic, medical_section"
    )

    preserve_sentences: bool = Field(
        default=True,
        description="If true, sentences are not split across chunks"
    )

    min_chunk_size: int = Field(
        default=100,
        description="Minimum chunk size (smaller chunks are discarded/merged)"
    )

    metadata_fields: Optional[list[str]] = Field(
        default=None,
        description="Metadata fields to preserve in each chunk"
    )
