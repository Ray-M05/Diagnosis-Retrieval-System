# Búsquedas Implementadas

Este documento describe las tres estrategias de búsqueda implementadas en el sistema.

## 🔍 1. Búsqueda Léxica (BM25)

**Implementación:** `SearchLexicalUseCase`  
**Backend:** OpenSearch con algoritmo BM25  
**Índice:** `clinical_docs`  
**Casos de uso:** Búsqueda por palabras clave exactas, términos médicos específicos

### Uso:
```python
from sri_dx.usecases.search import SearchLexicalUseCase
from sri_dx.adapters.stores import OpenSearchSearchBackend, OpenSearchSearchConfig

# Configurar backend
config = OpenSearchSearchConfig(index_alias="clinical_docs")
backend = OpenSearchSearchBackend(config)

# Crear UseCase
search_uc = SearchLexicalUseCase(backend=backend)

# Buscar
results = search_uc.search(
    query="diabetes mellitus tipo 2",
    k=10,
    with_highlights=True
)

for hit in results.hits:
    print(f"{hit.score:.2f} - {hit.title}")
    print(f"  {hit.highlights.get('body', [''])[0]}")
```

### Características:
- ✅ Búsqueda por coincidencia de términos
- ✅ Boosting de campos (título > secciones > cuerpo)
- ✅ Highlighting de resultados
- ✅ Facetas (source_domain, mime_type, seed_group)
- ✅ Filtros avanzados

---

## 🧠 2. Búsqueda Semántica (Vector kNN)

**Implementación:** `SearchSemanticUseCase`  
**Modelo:** Bio_ClinicalBERT (768 dims)  
**Índice:** `clinical_embeddings_v1`  
**Casos de uso:** Búsqueda por significado, conceptos relacionados, sinónimos

### Uso:
```python
from sri_dx.usecases.search import SearchSemanticUseCase
from sri_dx.adapters.stores import OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig

# Configurar embedding store
config = OpenSearchEmbeddingConfig(index_name="clinical_embeddings_v1")
store = OpenSearchEmbeddingSink(config)

# Crear UseCase
search_uc = SearchSemanticUseCase(embedding_store=store)

# Buscar
results = search_uc.search(
    query="tratamiento diabetes tipo 2",
    k=10,
    min_score=0.5
)

for result in results:
    print(f"{result.score:.3f} - {result.chunk_text_preview}")
    print(f"  Doc: {result.doc_id}, Chunk: {result.chunk_id}")
```

### Características:
- ✅ Comprende sinónimos y paráfrasis
- ✅ Búsqueda por similitud semántica (coseno)
- ✅ Retorna chunks relevantes con contexto
- ✅ Filtros por metadatos (seed_group, source_domain)
- ✅ Preview del texto del chunk

### Flujo interno:
1. Query → Bio_ClinicalBERT → embedding 768D
2. kNN search en OpenSearch (algoritmo HNSW)
3. Retorna K chunks más similares
4. Mapea chunk_id → doc_id

---

## ⚡ 3. Búsqueda Híbrida (Léxica + Semántica)

**Implementación:** `SearchHybridUseCase`  
**Fusión:** RRF (Reciprocal Rank Fusion) o Weighted Sum  
**Casos de uso:** Mejor calidad combinando precisión léxica + comprensión semántica

### Uso:
```python
from sri_dx.usecases.search import SearchHybridUseCase, HybridSearchConfig
from sri_dx.adapters.stores import (
    OpenSearchSearchBackend, 
    OpenSearchEmbeddingSink,
    OpenSearchSearchConfig,
    OpenSearchEmbeddingConfig
)

# Configurar backends
lexical_backend = OpenSearchSearchBackend(
    OpenSearchSearchConfig(index_alias="clinical_docs")
)
embedding_store = OpenSearchEmbeddingSink(
    OpenSearchEmbeddingConfig(index_name="clinical_embeddings_v1")
)

# Configurar fusión
config = HybridSearchConfig(
    fusion_method="rrf",  # o "weighted_sum"
    rrf_k=60,             # constante RRF
    lexical_k=100,        # resultados léxicos
    semantic_k=100,       # resultados semánticos
    min_semantic_score=0.3
)

# Crear UseCase
search_uc = SearchHybridUseCase(
    lexical_backend=lexical_backend,
    embedding_store=embedding_store,
    config=config
)

# Buscar
results = search_uc.search(
    query="síntomas hipertensión arterial",
    k=10
)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"  Léxico: {result.lexical_score or 'N/A'}")
    print(f"  Semántico: {result.vector_score or 'N/A'}")
    print(f"  Doc: {result.doc_id}")
```

### Métodos de Fusión:

#### RRF (Reciprocal Rank Fusion) - DEFAULT
```python
config = HybridSearchConfig(
    fusion_method="rrf",
    rrf_k=60  # k=60 es el valor típico en la literatura
)
```

**Fórmula:**  
`RRF_score(d) = sum( 1 / (k + rank(d)) )`

**Ventajas:**
- ✅ No requiere calibración de pesos
- ✅ Robusto a diferencias de escala de scores
- ✅ Favorece documentos que aparecen en ambos rankings
- ✅ Estado del arte en IR (SIGIR 2009)

#### Weighted Sum
```python
config = HybridSearchConfig(
    fusion_method="weighted_sum",
    lexical_weight=0.6,    # 60% peso léxico
    semantic_weight=0.4,   # 40% peso semántico
    normalize_scores=True
)
```

**Ventajas:**
- ✅ Control explícito de balance léxico/semántico
- ✅ Interpretable

### Características:
- ✅ Combina fortalezas de ambas búsquedas
- ✅ Múltiples métodos de fusión (RRF, weighted_sum, borda)
- ✅ Metadatos enriquecidos de ambas fuentes
- ✅ Elimina duplicados automáticamente

---

## 📊 Comparación de Estrategias

| Característica | Léxica | Semántica | Híbrida |
|----------------|--------|-----------|---------|
| **Búsqueda exacta** | ✅ Excelente | ❌ Regular | ✅ Buena |
| **Sinónimos** | ❌ No | ✅ Excelente | ✅ Excelente |
| **Términos raros** | ✅ Buena | ❌ Regular | ✅ Buena |
| **Contexto semántico** | ❌ No | ✅ Excelente | ✅ Excelente |
| **Velocidad** | ⚡ Rápida | 🐢 Media | 🏃 Media |
| **Calidad general** | 🥈 Buena | 🥈 Buena | 🥇 **Mejor** |

---

## 🔧 Módulos de Ranking

### Reciprocal Rank Fusion (RRF)
```python
from sri_dx.modules.ranking import reciprocal_rank_fusion

rankings = [
    ["doc1", "doc2", "doc3"],  # ranking léxico
    ["doc2", "doc4", "doc1"]   # ranking semántico
]

fused = reciprocal_rank_fusion(rankings, k=60)
# Resultado: [("doc2", 0.0322), ("doc1", 0.0321), ...]
```

### Weighted Sum
```python
from sri_dx.modules.ranking import weighted_sum_fusion

rankings_with_scores = [
    (["doc1", "doc2"], [10.5, 8.2]),  # léxico
    (["doc2", "doc3"], [0.95, 0.87])  # semántico
]

fused = weighted_sum_fusion(
    rankings_with_scores,
    weights=[0.6, 0.4],
    normalize=True
)
```

### Borda Count
```python
from sri_dx.modules.ranking import borda_count_fusion

rankings = [
    ["doc1", "doc2", "doc3"],
    ["doc2", "doc1", "doc4"]
]

fused = borda_count_fusion(rankings, max_points=100)
```

---

## 🎯 Recomendaciones de Uso

### Usar **Léxica** cuando:
- Buscas términos médicos específicos (ej: "ICD-10 E11.9")
- Necesitas coincidencias exactas
- Tienes queries con nombres propios (medicamentos, genes)
- Priorizas velocidad

### Usar **Semántica** cuando:
- Buscas conceptos o ideas (ej: "cómo controlar azúcar en sangre")
- Necesitas encontrar sinónimos o paráfrasis
- La query es descriptiva/contextual
- Quieres diversidad de resultados

### Usar **Híbrida** cuando:
- Quieres la mejor calidad (recomendado para producción)
- Combinas términos exactos + conceptos
- Necesitas robustez ante variaciones de query
- Tienes recursos computacionales suficientes

---

## 📖 Referencias

- **RRF:** Cormack et al. "Reciprocal Rank Fusion outperforms Condorcet" (SIGIR 2009)
- **Bio_ClinicalBERT:** Alsentzer et al. "Publicly Available Clinical BERT Embeddings" (2019)
- **OpenSearch kNN:** https://opensearch.org/docs/latest/search-plugins/knn/
