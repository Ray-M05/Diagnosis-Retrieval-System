from pydantic import BaseModel, Field
from typing import Optional


class CrossEncoderConfig(BaseModel):
    """Configuration for the cross-encoder."""

    model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Model name"
    )
    model_version: str = Field(
        default="1.0",
        description="Model version"
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=512,                         # upper bound to avoid OOM
        description="Batch size for inference"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        description="Number of results to return after reranking"
    )
    max_length: int = Field(
        default=512,
        ge=64,
        le=512,
        description="Maximum token length for concatenated query+document"
    )
    device: str = Field(
        default="cpu",
        pattern="^(cpu|cuda|mps)$",    # validates a supported device
        description="Inference device"
    )
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum score to include a result. None = no filter"
    )

    class Config:
        frozen = True