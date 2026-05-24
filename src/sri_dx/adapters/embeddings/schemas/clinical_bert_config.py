import logging

from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)


def _resolve_device(device: str) -> str:
    """Resolves 'auto' to the best available device."""
    if device != "auto":
        return device
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            logger.info("GPU detected: %s (%.1f GB VRAM)", gpu_name, gpu_mem)
            return "cuda"
        else:
            logger.info("No GPU available, using CPU")
            return "cpu"
    except ImportError:
        logger.info("torch not installed, using CPU")
        return "cpu"


def _cuda_memory_gb() -> float | None:
    """Returns total CUDA VRAM in GB, or None if unavailable."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except ImportError:
        return None
    return None


class ClinicalBERTConfig(BaseModel):
    """Pydantic config for the Bio_ClinicalBERT adapter."""

    model_config = ConfigDict(frozen=False)

    model_name: str = "emilyalsentzer/Bio_ClinicalBERT"
    max_length: int = 256  # 256 tokens covers ~1000 chars; reduces padding and doubles GPU throughput
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
            gpu_mem = _cuda_memory_gb()
            if gpu_mem is not None and gpu_mem >= 4.0:
                # With max_length=256 and FP16, GPUs with 4 GB+ can handle larger batches.
                object.__setattr__(self, "batch_size", 256)
                logger.info("Batch size auto-scaled to 256 for GPU (%.1f GB VRAM)", gpu_mem)
            elif gpu_mem is not None:
                logger.info("GPU with %.1f GB VRAM: keeping batch_size=%d", gpu_mem, self.batch_size)
        logger.info("ClinicalBERT config — device=%s, batch_size=%d, max_length=%d, fp16=%s",
                     resolved, self.batch_size, self.max_length, self.use_fp16)
        return self
