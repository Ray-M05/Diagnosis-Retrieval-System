"""Entity Extraction Module - Extracción de Entidades Clínicas

Módulo para identificar y extraer entidades médicas del texto.

Implementaciones disponibles:
- ClinicalBERTEntityExtractor: NER usando Bio_ClinicalBERT

Tipos de entidades soportadas:
- PROBLEM: Síntomas, diagnósticos, condiciones
- TREATMENT: Medicamentos, procedimientos, terapias  
- TEST: Pruebas diagnósticas, laboratorios
- ANATOMY: Partes del cuerpo, órganos

Estado: ✅ IMPLEMENTADO
"""

from .biomedical_ner_extractor import BiomedicalNEREntityExtractor
from .schemas.extractor_config import BiomedicalNERExtractorConfig

__all__ = ["BiomedicalNEREntityExtractor", "BiomedicalNERExtractorConfig"]
