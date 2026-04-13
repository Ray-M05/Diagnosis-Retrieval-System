# Búsqueda Híbrida con Reranking

Este documento describe la arquitectura y el funcionamiento del pipeline de búsqueda en dos etapas implementado en el sistema SRI-DX.

## Descripción General

El sistema utiliza un enfoque de **recuperación y re-clasificación** (Retrieve & Re-rank) para optimizar tanto la velocidad como la precisión de los resultados.

### Etapa 1: Recuperación Híbrida (Hybrid Retrieval)
En esta fase, el sistema busca candidatos potencialmente relevantes utilizando dos métodos complementarios:
- **Búsqueda Léxica (BM25):** Para coincidencias exactas de términos médicos y palabras clave.
- **Búsqueda Semántica (Bi-Encoder):** Para capturar el significado y contexto utilizando embeddings de `ClinicalBERT`.

Los resultados se fusionan mediante **Reciprocal Rank Fusion (RRF)** o **Suma Ponderada** para obtener un pool de candidatos (típicamente los mejores 50-100).

### Etapa 2: Re-ranking (Cross-Encoder)
Los candidatos obtenidos en la Etapa 1 se pasan por un modelo **Cross-Encoder**. A diferencia del Bi-Encoder, el Cross-Encoder procesa la consulta y el documento simultáneamente, permitiendo una interacción completa entre los términos. Esto proporciona una puntuación de relevancia mucho más precisa para el reordenamiento final.

## Configuración

La búsqueda se configura a través de `HybridSearchConfig`. Los parámetros clave para el re-ranking son:

| Parámetro | Descripción | Default |
| :--- | :--- | :--- |
| `use_reranking` | Activa la segunda etapa de re-ranking | `False` |
| `rerank_top_k` | Número de resultados finales tras el re-ranking | `10` |
| `rerank_model_name` | Modelo de Cross-Encoder a utilizar | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `rerank_score_threshold` | Umbral mínimo de score para filtrar resultados | `None` |

## Ventajas del Pipeline
- **Precisión Superior:** El Cross-Encoder corrige errores de posicionamiento de la búsqueda inicial.
- **Eficiencia:** Solo se aplica el modelo pesado (Cross-Encoder) a un pequeño subset de documentos, manteniendo tiempos de respuesta bajos.
- **Robustez:** La búsqueda híbrida asegura que no se pierdan documentos relevantes por falta de palabras clave exactas.
