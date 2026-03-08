from typing import Dict
from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(frozen=True)

    model_name: str = "d4data/biomedical-ner-all"
    device: int = -1
    aggregation_strategy: str = "simple"
    batch_size: int = 16
    stride: int = 128
    label_map: Dict[str, str] = LABEL_MAP.copy()
