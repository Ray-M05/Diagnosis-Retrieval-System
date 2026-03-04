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

from .clinical_bert_adapter import ClinicalBERTAdapter, ClinicalBERTConfig

__all__ = ["ClinicalBERTAdapter", "ClinicalBERTConfig"]
