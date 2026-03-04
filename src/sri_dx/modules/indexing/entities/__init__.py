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

from .clinical_bert_extractor import ClinicalBERTEntityExtractor

__all__ = ["ClinicalBERTEntityExtractor"]
