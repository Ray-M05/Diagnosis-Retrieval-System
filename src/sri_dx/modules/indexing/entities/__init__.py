"""Entity Extraction Module - Clinical Entity Extraction

Module for identifying and extracting medical entities from text.

Available implementations:
- ClinicalBERTEntityExtractor: NER using Bio_ClinicalBERT

Supported entity types:
- PROBLEM: Symptoms, diagnoses, conditions
- TREATMENT: Medications, procedures, therapies
- TEST: Diagnostic tests, laboratory tests
- ANATOMY: Body parts, organs

Status: ✅ IMPLEMENTED
"""

from .biomedical_ner_extractor import BiomedicalNEREntityExtractor
from .schemas.extractor_config import BiomedicalNERExtractorConfig

__all__ = ["BiomedicalNEREntityExtractor", "BiomedicalNERExtractorConfig"]
