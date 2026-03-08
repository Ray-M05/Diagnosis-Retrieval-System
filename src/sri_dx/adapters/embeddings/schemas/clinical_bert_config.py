from pydantic import BaseModel, ConfigDict


class ClinicalBERTConfig(BaseModel):
    """Pydantic config for the Bio_ClinicalBERT adapter."""

    model_config = ConfigDict(frozen=True)

    model_name: str = "emilyalsentzer/Bio_ClinicalBERT"
    max_length: int = 512
    batch_size: int = 16
    device: str = "cpu"
    pooling_strategy: str = "mean"
    normalize_embeddings: bool = True
