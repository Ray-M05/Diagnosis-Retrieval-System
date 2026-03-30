import logging
from typing import Dict
from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)


LABEL_MAP: Dict[str, str] = {
    "Disease": "PROBLEM",
    "Chemical": "TREATMENT",
    "Gene": "TEST",
    "Species": "ANATOMY",
    "Mutation": "PROBLEM",
    "CellLine": "ANATOMY",
    "CellType": "ANATOMY",
}


class BiomedicalNERConfig(BaseModel):
    """Pydantic config for the biomedical NER adapter."""

    model_config = ConfigDict(frozen=False)

    model_name: str = "d4data/biomedical-ner-all"
    device: int = -1
    aggregation_strategy: str = "simple"
    batch_size: int = 32
    stride: int = 128
    label_map: Dict[str, str] = LABEL_MAP.copy()

    @model_validator(mode="after")
    def _auto_detect_gpu(self) -> "BiomedicalNERConfig":
        if self.device == -1:
            try:
                import torch
                if torch.cuda.is_available():
                    object.__setattr__(self, "device", 0)
                    logger.info("NER: GPU detectada, usando device=0")
                else:
                    logger.info("NER: GPU no disponible, usando CPU (device=-1)")
            except ImportError:
                logger.info("NER: torch no instalado, usando CPU (device=-1)")
        return self
