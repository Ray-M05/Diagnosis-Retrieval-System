"""Embeddings Adapters

Adaptadores para modelos de embeddings.

Implementados:
- ClinicalBERTAdapter: Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT) ✅
  - Entrenado en MIMIC-III (notas clínicas reales)
  - Ideal para: diagnósticos, procedimientos, registros de pacientes
  - Singleton pattern para reusar el modelo

Por implementar:
- SentenceTransformerAdapter: Modelos locales (PubMedBERT)
- OpenAIAdapter: API de OpenAI (text-embedding-ada-002)
- CachedEmbeddingAdapter: Decorator para caché de embeddings

Estado: ✅ PARCIAL (ClinicalBERTAdapter implementado)
"""

from .clinical_bert_adapter import ClinicalBERTAdapter
from .schemas.clinical_bert_config import ClinicalBERTConfig
from .biomedical_ner_adapter import BiomedicalNERAdapter
from .schemas.biomedical_ner_config import BiomedicalNERConfig

__all__ = [
  "ClinicalBERTAdapter",
  "ClinicalBERTConfig",
  "BiomedicalNERAdapter",
  "BiomedicalNERConfig",
]
