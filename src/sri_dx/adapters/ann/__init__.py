"""ANN (Approximate Nearest Neighbors) Adapters

Adaptadores para índices vectoriales externos.

Nota: OpenSearch ya incluye kNN nativo con HNSW.
Este módulo es para integración con otras librerías si es necesario.

Adaptadores por implementar:
- HNSWLibAdapter: Integración con hnswlib
- FAISSAdapter: Integración con FAISS

Estado: ❌ OPCIONAL (OpenSearch kNN es suficiente)
"""
