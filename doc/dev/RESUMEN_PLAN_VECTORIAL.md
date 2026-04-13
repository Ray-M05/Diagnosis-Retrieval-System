# Resumen Ejecutivo: Plan de Implementación Vectorial SRI-DX

## 🎯 Objetivo

Implementar un sistema de base de datos vectorial genérico y de alta calidad para recuperación de diagnósticos médicos, con capacidades de:
- Búsqueda semántica y léxica híbrida
- Operaciones de conjuntos complejas
- Indexación eficiente (ANN/KNN)
- Abstracción total de tecnologías subyacentes

---

## 📊 Arquitectura en una Página

```
[Documentos Médicos]
        ↓
    Chunking (Secciones Médicas)
        ↓
    Embeddings (BioBERT/PubMedBERT)
        ↓
    ┌─────────────┬─────────────┐
    ↓             ↓             ↓
[Vectorial]  [Léxico]   [Metadata]
 (HNSW)      (BM25/ES)    (ES)
    ↓             ↓             ↓
    └─────────────┴─────────────┘
              ↓
        Fusión (RRF)
              ↓
    Operaciones de Conjuntos
    (AND, OR, NOT, Filtros)
              ↓
      [Resultados Rankeados]
```

---

## 🏗️ Componentes Principales

### 1. **Chunking Inteligente**
- **MedicalSectionChunker**: Segmenta por secciones médicas (síntomas, diagnóstico, tratamiento)
- **SlidingWindowChunker**: Fallback con overlap configurable
- **SemanticChunker**: Segmentación por coherencia semántica

### 2. **Embeddings**
- **Modelos recomendados**:
  - Desarrollo: all-MiniLM-L6-v2 (384 dim)
  - **Producción**: BiomedNLP-PubMedBERT (768 dim) ⭐
  - Máxima precisión: Bio_ClinicalBERT (768 dim)
- **Caché inteligente**: Memoria + disco
- **Batch processing**: Optimizado para grandes volúmenes

### 3. **Indexación Vectorial (ANN)**
- **HNSW**: Rápido, hasta 10M vectores
- **FAISS** (opcional): Para datasets masivos
- **ScaNN** (opcional): Google's Scalable Nearest Neighbors
- Parámetros configurables: ef_construction, M, ef_search

### 4. **Motor de Búsqueda Híbrido**
- **Búsqueda vectorial**: Similitud semántica (cosine/L2)
- **Búsqueda léxica**: BM25, TF-IDF (Elasticsearch)
- **Fusión**: Reciprocal Rank Fusion (RRF)
- **Balance configurable**: α (0=léxico, 1=vectorial, 0.5=balanceado)

### 5. **Operaciones de Conjuntos**
- **Intersección** (AND): Documentos en TODOS los conjuntos
- **Unión** (OR): Documentos en AL MENOS un conjunto
- **Negación** (NOT): Excluir resultados
- **Filtros por metadata**: Especialidad, año, nivel de evidencia

### 6. **Sistema de Metadatos**
- **DocumentMetadata**: ICD-10, SNOMED, MeSH, nivel de evidencia
- **ChunkMetadata**: Sección, entidades, calidad
- **Almacenamiento**: Elasticsearch (búsqueda eficiente)

---

## 🚀 Cronograma (12 semanas)

| Sprint | Semanas | Entregables |
|--------|---------|-------------|
| 1 | 1-2 | Puertos (interfaces), Schemas, MedicalSectionChunker |
| 2 | 3-4 | Embedder, HNSW Adapter, Pipeline indexación |
| 3 | 5-6 | RRF Fusion, HybridSearchUseCase, Tests |
| 4 | 7 | SetOperations, Query builder |
| 5 | 8 | MetadataStore, Medical NER básico |
| 6 | 9-10 | QueryExpander, MedicalReRanker, Evaluación |
| 7 | 11 | Integración UI, Visualizaciones |
| 8 | 12 | Optimización, Deployment, Docs |

---

## 📏 Métricas de Éxito

| Métrica | Target | Importancia |
|---------|--------|-------------|
| **Recall@10** | ≥ 85% | ⭐⭐⭐ No perder diagnósticos |
| **Precision@10** | ≥ 70% | ⭐⭐⭐ Minimizar ruido |
| **MAP** | ≥ 75% | ⭐⭐ Calidad global |
| **NDCG@10** | ≥ 80% | ⭐⭐ Orden correcto |
| **Latencia** | < 200ms | ⭐⭐⭐ UX responsiva |
| **Throughput** | > 100 qps | ⭐⭐ Escalabilidad |

---

## 🔑 Principios de Diseño

### 1. **Genericidad Total**
```python
# ✅ BIEN: Depende de abstracción
class HybridSearchUseCase:
    def __init__(
        self,
        embedder: EmbeddingPort,  # Cualquier modelo
        vector_index: VectorIndexPort,  # HNSW, FAISS, etc.
        lexical_index: LexicalIndexPort  # ES, Lucene, etc.
    ):
        ...

# ❌ MAL: Depende de implementación concreta
class HybridSearchUseCase:
    def __init__(self):
        self.embedder = SentenceTransformer("model-name")
        self.index = hnswlib.Index(...)
```

### 2. **Arquitectura Hexagonal**
- **Core**: Schemas, Ports (interfaces)
- **Use Cases**: Orquestación de negocio
- **Modules**: Implementaciones genéricas
- **Adapters**: Tecnologías específicas (HNSW, ES, etc.)

### 3. **Optimizaciones Médicas**
- **NER médico**: ICD-10, SNOMED, MeSH
- **Query expansion**: Sinónimos médicos ("MI" → "myocardial infarction")
- **Re-ranking**: Por evidencia, recencia, especialidad
- **Explicabilidad**: Auditoría completa de scores

---

## 💡 Casos de Uso Ejemplo

### Ejemplo 1: Búsqueda Simple
```python
query = HybridQuery(
    text="síntomas de infarto agudo de miocardio",
    k=10,
    alpha=0.6  # Más peso a semántico
)

results = hybrid_search_usecase.execute(query)
```

### Ejemplo 2: Búsqueda con Filtros
```python
query = HybridQuery(
    text="tratamiento de diabetes tipo 2",
    filters={
        "specialty": "endocrinology",
        "year": {"$gte": 2020},
        "evidence_level": {"$lte": 2}
    },
    k=20
)

results = hybrid_search_usecase.execute(query)
```

### Ejemplo 3: Query Compleja
```python
# "síntomas de infarto" AND "diagnóstico" NOT "infarto antiguo"
# WHERE specialty='cardiology'

set_ops = SetOperations()

# Búsquedas individuales
r1 = search("síntomas de infarto", k=50)
r2 = search("diagnóstico", k=50)
r3 = search("infarto antiguo", k=50)

# Operaciones
intersected = set_ops.intersect([r1, r2])
negated = set_ops.negate(intersected, r3)
filtered = set_ops.filter_by_metadata(
    negated,
    lambda m: m.get("specialty") == "cardiology"
)
```

---

## 📦 Stack Tecnológico

| Componente | Tecnología Principal | Alternativas |
|------------|---------------------|--------------|
| Embeddings | BiomedNLP-PubMedBERT | Bio_ClinicalBERT, BioBERT |
| Vector Index | HNSWLib | FAISS, ScaNN, Milvus |
| Búsqueda Léxica | Elasticsearch | Lucene, Solr |
| Metadatos | Elasticsearch | PostgreSQL, MongoDB |
| Caché | Disco + LRU Memoria | Redis (opcional) |
| Fusión | RRF | CombSUM, Weighted |

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Modelo embedding incorrecto | Alto | Benchmark de múltiples modelos en Sprint 2 |
| Latencia alta de búsqueda | Alto | Profiling, caché, indexación optimizada |
| Recall bajo | Crítico | Query expansion, tuning de α, evaluación continua |
| Escalabilidad limitada | Medio | Arquitectura modular, sharding de ES |
| Explicabilidad insuficiente | Alto | Sistema de metadata completo, scoring detallado |

---

## 📚 Documentación Relacionada

- **Plan Completo**: [PLAN_IMPLEMENTACION_VECTORIAL.md](./PLAN_IMPLEMENTACION_VECTORIAL.md)
- **Arquitectura General**: [../../ARQUITECTURA.md](../../ARQUITECTURA.md)
- **Workflow UV**: [uv_workflow.md](./uv_workflow.md)
- **Deployment**: [../prod/deployment.md](../prod/deployment.md)

---

## ✅ Checklist de Inicio

Antes de comenzar la implementación:

- [ ] Validar requisitos con stakeholders médicos
- [ ] Definir dataset de evaluación (ground truth)
- [ ] Configurar entorno de desarrollo (Docker + UV)
- [ ] Crear repositorio de código con estructura base
- [ ] Configurar CI/CD básico
- [ ] Definir métricas específicas del dominio
- [ ] Identificar fuentes de datos iniciales
- [ ] Establecer protocolo de evaluación

---

## 🎓 Recursos de Aprendizaje

### Embeddings Médicos
- [PubMedBERT Paper](https://arxiv.org/abs/2007.15779)
- [BioClinicalBERT](https://github.com/EmilyAlsentzer/clinicalBERT)

### Búsqueda Híbrida
- [RRF Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Hybrid Search Guide](https://www.pinecone.io/learn/hybrid-search-intro/)

### ANN Algorithms
- [HNSW Paper](https://arxiv.org/abs/1603.09320)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)

### Medical NLP
- [scispaCy](https://allenai.github.io/scispacy/)
- [Medical NER with BERT](https://arxiv.org/abs/1810.04805)

---

**Última actualización**: Marzo 2026  
**Versión**: 1.0  
**Autor**: Equipo SRI-DX
