import logging

from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)


def _resolve_device(device: str) -> str:
    """Resuelve 'auto' al mejor dispositivo disponible."""
    if device != "auto":
        return device
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
            logger.info("GPU detectada: %s (%.1f GB VRAM)", gpu_name, gpu_mem)
            return "cuda"
        else:
            logger.info("GPU no disponible, usando CPU")
            return "cpu"
    except ImportError:
        logger.info("torch no instalado, usando CPU")
        return "cpu"


class ClinicalBERTConfig(BaseModel):
    """Pydantic config for the Bio_ClinicalBERT adapter."""

    model_config = ConfigDict(frozen=False)

    model_name: str = "emilyalsentzer/Bio_ClinicalBERT"
    max_length: int = 512
    batch_size: int = 64
    device: str = "auto"
    pooling_strategy: str = "mean"
    normalize_embeddings: bool = True
    use_fp16: bool = True
    use_onnx: bool = True

    @model_validator(mode="after")
    def _resolve(self) -> "ClinicalBERTConfig":
        resolved = _resolve_device(self.device)
        object.__setattr__(self, "device", resolved)
        if resolved == "cuda" and self.batch_size <= 64:
            object.__setattr__(self, "batch_size", 128)
            logger.info("Batch size auto-escalado a 128 para GPU")
        logger.info("ClinicalBERT config: device=%s, batch_size=%d, fp16=%s", resolved, self.batch_size, self.use_fp16)
        return self
