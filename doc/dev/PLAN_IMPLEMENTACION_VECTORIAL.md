# Plan de Implementación: Sistema de Base de Datos Vectorial para Diagnósticos Médicos

**Versión**: 2.0 (Actualizada - Arquitectura centrada en Elasticsearch)  
**Fecha**: Marzo 2026  
**Proyecto**: SRI-DX (Diagnosis Retrieval System)  
**Objetivo**: Implementar un sistema vectorial genérico usando **Elasticsearch como núcleo central** para recuperación de diagnósticos médicos de alta calidad

---

## 📋 Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [🎯 Decisión Arquitectural: Elasticsearch Central](#2-decisión-arquitectural-elasticsearch-central)
3. [Arquitectura del Sistema Vectorial](#3-arquitectura-del-sistema-vectorial)
4. [Fase 1: Definición de Puertos (Interfaces)](#4-fase-1-definición-de-puertos-interfaces)
5. [Fase 2: Procesamiento de Documentos y Chunking](#5-fase-2-procesamiento-de-documentos-y-chunking)
6. [Fase 3: Generación de Embeddings](#6-fase-3-generación-de-embeddings)
7. [Fase 4: Adaptador Elasticsearch (Núcleo)](#7-fase-4-adaptador-elasticsearch-núcleo)
8. [Fase 5: Casos de Uso de Búsqueda](#8-fase-5-casos-de-uso-de-búsqueda)
9. [Fase 6: Optimizaciones Específicas para Dominio Médico](#9-fase-6-optimizaciones-específicas-para-dominio-médico)
10. [Cronograma de Implementación](#10-cronograma-de-implementación)
11. [Métricas de Calidad](#11-métricas-de-calidad)
12. [Consideraciones de Producción](#12-consideraciones-de-producción)

---

## 1. Visión General

### 1.1 Objetivos

- **Genericidad**: Interfaces abstractas que permitan cambiar BD, modelos o algoritmos sin reescribir código
- **Calidad Médica**: Precisión y recall óptimos para diagnósticos
- **Rendimiento**: Búsquedas sub-segundo en millones de documentos
- **Extensibilidad**: Fácil añadir nuevos tipos de búsqueda o rankings
- **Trazabilidad**: Metadatos completos para auditoría y explicabilidad

### 1.2 Flujo de Datos (Arquitectura centrada en Elasticsearch)

```
┌─────────────────────────────────────────────────────────────────┐
│ ENTRADA: Documentos Médicos (PDF, TXT, JSON, etc.)             │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ FASE 1: Chunking Inteligente (Python local)                     │
│ - MedicalSectionChunker: Segmenta por secciones clínicas        │
│ - Preservación de contexto                                      │
│ - Overlapping configurable                                      │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ FASE 2: Generación de Embeddings (Python local)                 │
│ - BioBERT/PubMedBERT: Vectorización médica                      │
│ - Normalización L2                                              │
│ - Caché local (Redis opcional)                                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌═════════════════════════════════════════════════════════════════┐
║ 🎯 ELASTICSEARCH (Núcleo Central)                              ║
╠═════════════════════════════════════════════════════════════════╣
║ FASE 3: Indexación Unificada                                   ║
║ ✅ Índice Dense Vector (kNN con HNSW interno)                  ║
║ ✅ Índice Invertido (BM25 optimizado)                          ║
║ ✅ Metadata estructurada (filtros rápidos)                     ║
║                                                                 ║
║ FASE 4: Motor de Búsqueda Nativo                               ║
║ ✅ Búsqueda Semántica: kNN search                              ║
║ ✅ Búsqueda Léxica: match/multi_match queries                  ║
║ ✅ Búsqueda Híbrida: kNN + query en una sola request          ║
║                                                                 ║
║ FASE 5: Operaciones Avanzadas (Query DSL)                      ║
║ ✅ Bool queries: must (AND), should (OR), must_not (NOT)      ║
║ ✅ Filtros: term, range, terms, exists                         ║
║ ✅ Boosting: por campo, por query, function_score              ║
║ ✅ Aggregations: métricas por especialidad, año, etc.          ║
║ ✅ Explain API: scoring transparente                           ║
╚═════════════════┬═══════════════════════════════════════════════╝
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ FASE 6: Post-Procesamiento (Python local - opcional)            │
│ - Re-ranking médico (boost por evidencia, especialidad)         │
│ - Deduplicación                                                 │
│ - Formateo de resultados                                        │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ SALIDA: Diagnósticos Rankeados con Explicaciones                │
│ - Scores híbridos                                               │
│ - Metadata clínica                                              │
│ - Explicación de relevancia                                     │
└─────────────────────────────────────────────────────────────────┘
```

**🔑 VENTAJAS de esta arquitectura**:

| Aspecto | Con ES Centralizado | Con Múltiples Backends |
|---------|---------------------|------------------------|
| **Complejidad** | 🟢 Baja (1 sistema) | 🔴 Alta (ES + HNSW + fusión manual) |
| **Latencia** | 🟢 <100ms (1 red call) | 🟡 150-300ms (2+ calls + fusión) |
| **Mantenimiento** | 🟢 Un solo servicio | 🔴 Múltiples servicios + sync |
| **Filtros** | 🟢 Nativos (Query DSL) | 🟡 Post-procesamiento |
| **Escalabilidad** | 🟢 Sharding automático | 🟡 Manual por componente |
| **Debugging** | 🟢 Explain API built-in | 🔴 Debug múltiple |
| **Costo** | 🟢 Infraestructura única | 🔴 Múltiples instancias |

---

## 2. 🎯 Decisión Arquitectural: Elasticsearch Central

### 2.1 Capacidades Nativas de Elasticsearch

Elasticsearch (versión 8.0+) incluye **todas** las capacidades necesarias para el sistema:

| Capacidad | Implementación en ES | Reemplaza Módulo |
|-----------|---------------------|------------------|
| **Búsqueda Vectorial** | `dense_vector` field type + kNN search | ❌ HNSW/FAISS adapters |
| **Algoritmo ANN** | HNSW interno optimizado | ❌ HNSWLib standalone |
| **Búsqueda Léxica** | BM25 nativo + analyzers | ❌ Whoosh/PyTerrier |
| **Búsqueda Híbrida** | kNN + query en una request | ❌ Módulo fusion/ completo |
| **Operaciones Booleanas** | Bool queries (must/should/must_not) | ❌ Módulo set_ops/ |
| **Filtros** | Term/Range/Terms filters | ❌ Post-processing |
| **Metadata** | Object/Nested fields | ❌ Metadata store separado |
| **Scoring** | Function score, boosting | ❌ Re-rankers externos |
| **Explicabilidad** | Explain API | ❌ Logging manual |
| **Escalabilidad** | Sharding automático | ❌ Configuración manual |

### 2.2 Ejemplo de Query Híbrida Nativa

**Con Elasticsearch (1 request)**:
```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [0.1, 0.2, ...],
    "k": 10,
    "boost": 0.7
  },
  "query": {
    "bool": {
      "should": [
        {
          "match": {
            "content": {
              "query": "chest pain shortness breath",
              "boost": 0.3
            }
          }
        }
      ],
      "filter": [
        {"term": {"metadata.specialty": "cardiology"}},
        {"range": {"metadata.year": {"gte": 2020}}}
      ]
    }
  }
}
```

**Sin Elasticsearch (múltiples requests + código Python)**:
```python
# 1. Búsqueda vectorial
vector_results = hnsw_index.search(vector, k=50)

# 2. Búsqueda léxica
lexical_results = bm25_index.search("chest pain", k=50)

# 3. Fusión manual (RRF)
hybrid_results = reciprocal_rank_fusion(vector_results, lexical_results, alpha=0.7)

# 4. Filtrar manualmente
filtered = [r for r in hybrid_results 
            if r.metadata['specialty'] == 'cardiology' 
            and r.metadata['year'] >= 2020]

# 5. Re-ordenar
final = sorted(filtered, key=lambda x: x.score, reverse=True)[:10]
```

**Resultado**: Elasticsearch es **más simple**, **más rápido** (1 red call vs 2+), y **más mantenible**.

### 2.3 Beneficios vs Costos

| Aspecto | Beneficio | Detalle |
|---------|-----------|---------|
| ✅ **Desarrollo** | -60% líneas código | No necesitas fusion/, set_ops/, metadata_store/ |
| ✅ **Latencia** | -50% tiempo | 1 request vs 2+ requests + procesamiento |
| ✅ **Mantenimiento** | 1 servicio | Solo ES vs ES+HNSW+Redis |
| ✅ **Debugging** | Explain API | Scores transparentes built-in |
| ✅ **Escalabilidad** | Automática | Sharding, réplicas out-of-the-box |
| ⚠️ **Lock-in** | Moderado | Código usa Query DSL de ES (pero port interface abstrae) |
| ⚠️ **Recursos** | +RAM | ES usa más memoria que HNSW puro |

**Decisión**: Los beneficios **superan ampliamente** los costos para SRI-DX.

---

## 3. Arquitectura del Sistema Vectorial

### 3.1 Estructura de Directorios (Arquitectura centrada en Elasticsearch)

**🎯 DECISIÓN ARQUITECTURAL**: Elasticsearch como núcleo central del sistema.

**Ventajas**:
- ✅ Un solo sistema para vectorial + léxico + híbrido
- ✅ Código más simple (menos adaptadores)
- ✅ Búsqueda híbrida nativa (sin fusión manual)
- ✅ Filtros de metadata nativos (Query DSL)
- ✅ Escalabilidad probada (sharding automático)
- ✅ Monitoreo incluido (Kibana)

```
src/sri_dx/
├── core/
│   ├── ports/
│   │   ├── chunker_port.py              # Interface para chunking
│   │   ├── embedding_port.py            # Interface para embeddings
│   │   └── search_port.py               # Interface unificada para búsqueda (ES)
│   │
│   ├── schemas/
│   │   ├── chunk_schema.py              # Modelo de Chunk
│   │   ├── embedding_schema.py          # Modelo de Embedding
│   │   ├── search_query_schema.py       # Modelo de Query (léxica/vectorial/híbrida)
│   │   ├── search_result_schema.py      # Modelo de Resultado
│   │   └── metadata_schema.py           # Modelo de Metadatos médicos
│   │
│   └── domain/
│       ├── chunking_strategy.py         # Estrategias de chunking médico
│       └── ranking_strategy.py          # Estrategias de re-ranking
│
├── modules/
│   ├── chunking/
│   │   ├── medical_section_chunker.py   # Chunking por secciones médicas ⭐
│   │   ├── semantic_chunker.py          # Chunking semántico
│   │   └── sliding_window_chunker.py    # Chunking de ventana (fallback)
│   │
│   ├── embedding/
│   │   ├── biomedical_embedder.py       # BioBERT/PubMedBERT ⭐
│   │   ├── cached_embedder.py           # Decorator: caché de embeddings
│   │   └── batch_embedder.py            # Decorator: procesamiento batch
│   │
│   ├── ner/
│   │   └── medical_ner.py               # Extracción entidades médicas
│   │
│   ├── query_expansion/
│   │   └── medical_query_expander.py    # Expansión términos médicos
│   │
│   └── ranking/
│       └── medical_reranker.py          # Re-ranking específico médico
│
├── adapters/
│   ├── elasticsearch/
│   │   └── es_adapter.py                # 🎯 ADAPTADOR PRINCIPAL
│   │                                    # - Índices vectoriales (kNN)
│   │                                    # - Búsqueda léxica (BM25)
│   │                                    # - Búsqueda híbrida nativa
│   │                                    # - Metadatos y filtros (Query DSL)
│   │                                    # - Operaciones de conjuntos (bool queries)
│   │
│   └── embeddings/
│       ├── sentence_transformer_adapter.py  # Sentence-BERT local
│       └── openai_adapter.py                # OpenAI API (opcional)
│
└── usecases/
    ├── indexing_usecase.py              # Indexar documentos con chunks + embeddings
    ├── search_usecase.py                # Búsqueda unificada (delega a ES)
    └── evaluation_usecase.py            # Evaluar calidad de búsqueda
```

**📦 SIMPLIFICACIÓN**: 
- ❌ **Eliminados** módulos `fusion/` → Elasticsearch lo hace nativamente
- ❌ **Eliminados** múltiples adaptadores ANN → Solo Elasticsearch
- ❌ **Eliminados** módulos `set_ops/` → Query DSL de ES (bool queries)
- ✅ **Centralizados** todos los índices en ES
- ✅ **Unificado** puerto de búsqueda (un solo adaptador)

### 2.2 Principios de Diseño

1. **SOLID**
   - Single Responsibility: Cada clase una responsabilidad
   - Open/Closed: Extensible sin modificar código existente
   - Liskov Substitution: Los adaptadores son intercambiables
   - Interface Segregation: Interfaces pequeñas y específicas
   - Dependency Inversion: Dependencias hacia abstracciones

2. **Design Patterns**
   - **Strategy Pattern**: Para algoritmos de chunking, embedding, ranking
   - **Adapter Pattern**: Para Elasticsearch (único backend de búsqueda)
   - **Decorator Pattern**: Para caché de embeddings, logging, métricas
   - **Facade Pattern**: Search UseCase simplifica acceso a ES
   - **Builder Pattern**: Para construcción de queries complejas de ES

3. **Principios Médicos**
   - **Trazabilidad**: Cada resultado debe ser explicable
   - **Reproducibilidad**: Mismos inputs → mismos outputs
   - **Validación**: Verificación de calidad en cada etapa
   - **Privacidad**: Manejo seguro de datos sensibles

---

## 4. Fase 1: Definición de Puertos (Interfaces)

### 4.1 ChunkerPort

```python
# core/ports/chunker_port.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ..schemas.chunk_schema import Chunk, ChunkingConfig
from ..schemas.schema import Document

class ChunkerPort(ABC):
    """
    Puerto para estrategias de chunking.
    Permite cambiar algoritmos sin afectar al sistema.
    """
    
    @abstractmethod
    def chunk_document(
        self, 
        document: Document, 
        config: Optional[ChunkingConfig] = None
    ) -> List[Chunk]:
        """
        Divide un documento en chunks.
        
        Args:
            document: Documento a dividir
            config: Configuración de chunking (tamaño, overlap, etc.)
            
        Returns:
            Lista de chunks con metadatos
        """
        pass
    
    @abstractmethod
    def chunk_batch(
        self, 
        documents: List[Document], 
        config: Optional[ChunkingConfig] = None
    ) -> List[List[Chunk]]:
        """
        Procesa múltiples documentos en lote.
        
        Returns:
            Lista de listas de chunks (preserva orden)
        """
        pass
    
    @abstractmethod
    def estimate_chunks(self, document: Document) -> int:
        """
        Estima cuántos chunks generará un documento.
        Útil para pre-allocación de memoria.
        """
        pass
```

### 3.2 EmbeddingPort

```python
# core/ports/embedding_port.py
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from ..schemas.embedding_schema import EmbeddingConfig

class EmbeddingPort(ABC):
    """
    Puerto para modelos de embeddings.
    Permite cambiar modelos sin modificar pipeline.
    """
    
    @abstractmethod
    def encode(
        self, 
        texts: List[str], 
        config: Optional[EmbeddingConfig] = None
    ) -> np.ndarray:
        """
        Genera embeddings para una lista de textos.
        
        Args:
            texts: Textos a vectorizar
            config: Configuración (normalización, dimensionalidad, etc.)
            
        Returns:
            Array numpy de shape (len(texts), embedding_dim)
        """
        pass
    
    @abstractmethod
    def encode_query(
        self, 
        query: str, 
        config: Optional[EmbeddingConfig] = None
    ) -> np.ndarray:
        """
        Genera embedding para query (puede tener tratamiento especial).
        
        Returns:
            Vector numpy de shape (embedding_dim,)
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Retorna la dimensionalidad de los embeddings."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Retorna información del modelo.
        Útil para trazabilidad y versionado.
        """
        pass
```

### 3.3 VectorIndexPort

```python
# core/ports/vector_index_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np
from ..schemas.search_result_schema import VectorSearchResult

class VectorIndexPort(ABC):
    """
    Puerto para índices vectoriales (ANN/KNN).
    Permite cambiar de HNSW a FAISS, ScaNN, etc.
    """
    
    @abstractmethod
    def build_index(
        self, 
        vectors: np.ndarray, 
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict] = None
    ) -> None:
        """
        Construye el índice vectorial.
        
        Args:
            vectors: Array de vectores (n_samples, dimension)
            ids: IDs únicos para cada vector
            metadata: Metadatos asociados a cada vector
            config: Parámetros del índice (ef_construction, M, etc.)
        """
        pass
    
    @abstractmethod
    def search(
        self, 
        query_vector: np.ndarray, 
        k: int = 10,
        filter_criteria: Optional[Dict] = None
    ) -> List[VectorSearchResult]:
        """
        Búsqueda de K vecinos más cercanos.
        
        Args:
            query_vector: Vector de consulta
            k: Número de resultados
            filter_criteria: Filtros por metadatos
            
        Returns:
            Lista de resultados con scores y metadatos
        """
        pass
    
    @abstractmethod
    def batch_search(
        self, 
        query_vectors: np.ndarray, 
        k: int = 10
    ) -> List[List[VectorSearchResult]]:
        """Búsqueda por lotes (optimizada)."""
        pass
    
    @abstractmethod
    def add_vectors(
        self, 
        vectors: np.ndarray, 
        ids: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """Añade vectores al índice existente."""
        pass
    
    @abstractmethod
    def remove_vectors(self, ids: List[str]) -> None:
        """Elimina vectores del índice."""
        pass
    
    @abstractmethod
    def save_index(self, path: str) -> None:
        """Persiste el índice en disco."""
        pass
    
    @abstractmethod
    def load_index(self, path: str) -> None:
        """Carga el índice desde disco."""
        pass
    
    @abstractmethod
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Estadísticas del índice.
        Ej: tamaño, número de vectores, memoria usada, etc.
        """
        pass
```

### 3.4 LexicalIndexPort

```python
# core/ports/lexical_index_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..schemas.search_result_schema import LexicalSearchResult
from ..schemas.search_query_schema import LexicalQuery

class LexicalIndexPort(ABC):
    """
    Puerto para búsqueda léxica (BM25, TF-IDF, etc.).
    """
    
    @abstractmethod
    def index_documents(
        self, 
        documents: List[Dict[str, Any]], 
        text_field: str = "content",
        config: Optional[Dict] = None
    ) -> None:
        """
        Indexa documentos para búsqueda léxica.
        
        Args:
            documents: Lista de documentos (dicts con id, content, metadata)
            text_field: Campo que contiene el texto
            config: Parámetros (k1, b para BM25, etc.)
        """
        pass
    
    @abstractmethod
    def search(
        self, 
        query: LexicalQuery, 
        k: int = 10,
        filter_criteria: Optional[Dict] = None
    ) -> List[LexicalSearchResult]:
        """
        Búsqueda léxica.
        
        Args:
            query: Query con términos, operadores, etc.
            k: Número de resultados
            filter_criteria: Filtros adicionales
            
        Returns:
            Resultados con scores BM25/TF-IDF
        """
        pass
    
    @abstractmethod
    def explain_score(self, query: str, doc_id: str) -> Dict[str, Any]:
        """
        Explica por qué un documento tiene cierto score.
        Crucial para auditoría médica.
        """
        pass
```

### 3.5 HybridSearchPort

```python
# core/ports/hybrid_search_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..schemas.search_query_schema import HybridQuery
from ..schemas.search_result_schema import HybridSearchResult

class HybridSearchPort(ABC):
    """
    Puerto para búsqueda híbrida (fusión de vectorial + léxica).
    """
    
    @abstractmethod
    def search(
        self, 
        query: HybridQuery, 
        k: int = 10,
        alpha: float = 0.5,  # Balance vectorial vs léxico
        filter_criteria: Optional[Dict] = None
    ) -> List[HybridSearchResult]:
        """
        Búsqueda híbrida con fusión de resultados.
        
        Args:
            query: Query con componentes semánticos y léxicos
            k: Número de resultados finales
            alpha: Peso (0=solo léxico, 1=solo vectorial, 0.5=balanceado)
            filter_criteria: Filtros por metadatos
            
        Returns:
            Resultados fusionados con scores combinados
        """
        pass
    
    @abstractmethod
    def get_fusion_strategy(self) -> str:
        """Retorna la estrategia de fusión usada (RRF, CombSUM, etc.)."""
        pass
```

### 3.6 SetOperationsPort

```python
# core/ports/set_operations_port.py
from abc import ABC, abstractmethod
from typing import List, Set, Callable, Optional
from ..schemas.search_result_schema import SearchResult

class SetOperationsPort(ABC):
    """
    Puerto para operaciones de conjuntos sobre resultados.
    """
    
    @abstractmethod
    def intersect(
        self, 
        result_sets: List[List[SearchResult]],
        merge_strategy: str = "max_score"
    ) -> List[SearchResult]:
        """
        Intersección de múltiples conjuntos de resultados.
        
        Args:
            result_sets: Listas de resultados a intersectar
            merge_strategy: Cómo combinar scores (max, min, avg)
            
        Returns:
            Documentos que aparecen en TODOS los conjuntos
        """
        pass
    
    @abstractmethod
    def union(
        self, 
        result_sets: List[List[SearchResult]],
        dedup_strategy: str = "keep_highest"
    ) -> List[SearchResult]:
        """
        Unión de múltiples conjuntos.
        
        Args:
            dedup_strategy: Cómo manejar duplicados (keep_highest, keep_first, avg)
            
        Returns:
            Documentos que aparecen en AL MENOS UN conjunto
        """
        pass
    
    @abstractmethod
    def negate(
        self, 
        positive_results: List[SearchResult],
        negative_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Negación: resultados en positive pero NO en negative.
        Ejemplo: "diabetes" NOT "tipo 1"
        """
        pass
    
    @abstractmethod
    def filter_by_metadata(
        self, 
        results: List[SearchResult],
        filter_fn: Callable[[Dict], bool]
    ) -> List[SearchResult]:
        """
        Filtra resultados según función de metadatos.
        
        Example:
            lambda m: m["specialty"] == "cardiology" and m["year"] >= 2020
        """
        pass
    
    @abstractmethod
    def filter_by_score_threshold(
        self, 
        results: List[SearchResult],
        min_score: float
    ) -> List[SearchResult]:
        """Filtra por score mínimo."""
        pass
```

### 3.7 MetadataStorePort

```python
# core/ports/metadata_store_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..schemas.metadata_schema import DocumentMetadata, ChunkMetadata

class MetadataStorePort(ABC):
    """
    Puerto para almacenamiento y consulta de metadatos.
    """
    
    @abstractmethod
    def store_document_metadata(
        self, 
        doc_id: str, 
        metadata: DocumentMetadata
    ) -> None:
        """Almacena metadatos de documento."""
        pass
    
    @abstractmethod
    def store_chunk_metadata(
        self, 
        chunk_id: str, 
        metadata: ChunkMetadata
    ) -> None:
        """Almacena metadatos de chunk."""
        pass
    
    @abstractmethod
    def get_document_metadata(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Recupera metadatos de documento."""
        pass
    
    @abstractmethod
    def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Recupera metadatos de chunk."""
        pass
    
    @abstractmethod
    def query_by_metadata(
        self, 
        filters: Dict[str, Any]
    ) -> List[str]:
        """
        Consulta IDs que cumplen criterios de metadatos.
        
        Example:
            filters = {
                "specialty": "cardiology",
                "year": {"$gte": 2020},
                "language": "en"
            }
        """
        pass
    
    @abstractmethod
    def enrich_results(
        self, 
        doc_ids: List[str]
    ) -> List[DocumentMetadata]:
        """
        Enriquece lista de IDs con sus metadatos.
        Optimizado para batch.
        """
        pass
```

---

## 5. Fase 2: Procesamiento de Documentos y Chunking

### 5.1 Schemas de Chunk

```python
# core/schemas/chunk_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ChunkingConfig(BaseModel):
    """Configuración para estrategia de chunking."""
    
    chunk_size: int = Field(
        default=512, 
        ge=64, 
        le=4096,
        description="Tamaño máximo del chunk en tokens"
    )
    
    chunk_overlap: int = Field(
        default=50, 
        ge=0,
        description="Tokens de overlap entre chunks"
    )
    
    strategy: str = Field(
        default="sliding_window",
        description="Estrategia: sliding_window, semantic, medical_section"
    )
    
    preserve_sentences: bool = Field(
        default=True,
        description="Si true, no rompe oraciones"
    )
    
    min_chunk_size: int = Field(
        default=100,
        description="Tamaño mínimo (chunks más pequeños se descartan/fusionan)"
    )
    
    metadata_fields: Optional[list[str]] = Field(
        default=None,
        description="Campos de metadata a preservar en cada chunk"
    )


class Chunk(BaseModel):
    """Representa un chunk de documento."""
    
    chunk_id: str = Field(
        description="ID único del chunk (formato: {doc_id}_chunk_{index})"
    )
    
    document_id: str = Field(
        description="ID del documento padre"
    )
    
    content: str = Field(
        description="Texto del chunk"
    )
    
    chunk_index: int = Field(
        ge=0,
        description="Índice del chunk dentro del documento (0-based)"
    )
    
    start_char: int = Field(
        ge=0,
        description="Posición de inicio en el documento original"
    )
    
    end_char: int = Field(
        ge=0,
        description="Posición de fin en el documento original"
    )
    
    token_count: int = Field(
        ge=0,
        description="Número aproximado de tokens"
    )
    
    # Metadatos específicos médicos
    section_type: Optional[str] = Field(
        default=None,
        description="Tipo de sección médica: symptoms, diagnosis, treatment, etc."
    )
    
    medical_entities: Optional[list[str]] = Field(
        default=None,
        description="Entidades médicas detectadas (ICD codes, SNOMED, etc.)"
    )
    
    # Metadatos heredados del documento
    original_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos del documento padre"
    )
    
    # Control de calidad
    quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de calidad del chunk (completitud, coherencia)"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de creación"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "doc_123_chunk_0",
                "document_id": "doc_123",
                "content": "Patient presents with acute chest pain...",
                "chunk_index": 0,
                "start_char": 0,
                "end_char": 512,
                "token_count": 128,
                "section_type": "symptoms",
                "medical_entities": ["I21.9", "R07.4"],
                "quality_score": 0.95
            }
        }
```

### 4.2 Implementación: MedicalSectionChunker

```python
# modules/chunking/medical_section_chunker.py
from typing import List, Optional, Dict
import re
from ...core.ports.chunker_port import ChunkerPort
from ...core.schemas.chunk_schema import Chunk, ChunkingConfig
from ...core.schemas.schema import Document

class MedicalSectionChunker(ChunkerPort):
    """
    Chunker especializado en documentos médicos.
    Segmenta por secciones clínicas estándar.
    """
    
    # Secciones médicas comunes
    MEDICAL_SECTIONS = {
        "chief_complaint": r"(?i)chief complaint|presenting complaint",
        "hpi": r"(?i)history of present illness|hpi",
        "pmh": r"(?i)past medical history|pmh",
        "medications": r"(?i)medications|current medications",
        "allergies": r"(?i)allergies|drug allergies",
        "ros": r"(?i)review of systems|ros",
        "physical_exam": r"(?i)physical exam|examination",
        "assessment": r"(?i)assessment|impression|diagnosis",
        "plan": r"(?i)plan|treatment plan",
        "labs": r"(?i)laboratory|lab results",
        "imaging": r"(?i)imaging|radiology",
    }
    
    def __init__(self, tokenizer_fn: Optional[callable] = None):
        """
        Args:
            tokenizer_fn: Función para contar tokens (default: split por espacios)
        """
        self.tokenizer_fn = tokenizer_fn or self._simple_tokenizer
    
    def _simple_tokenizer(self, text: str) -> int:
        """Tokenizador simple (aproximación)."""
        # Aproximación: ~1.3 tokens por palabra en inglés médico
        return int(len(text.split()) * 1.3)
    
    def chunk_document(
        self, 
        document: Document, 
        config: Optional[ChunkingConfig] = None
    ) -> List[Chunk]:
        """
        Segmenta documento por secciones médicas.
        Si no detecta secciones, usa sliding window.
        """
        config = config or ChunkingConfig()
        
        # Intentar segmentar por secciones
        sections = self._detect_sections(document.content)
        
        if len(sections) > 1:
            # Usar segmentación por secciones
            chunks = self._chunk_by_sections(document, sections, config)
        else:
            # Fallback a sliding window
            chunks = self._sliding_window_chunk(document, config)
        
        # Calcular quality scores
        for chunk in chunks:
            chunk.quality_score = self._calculate_quality_score(chunk)
        
        return chunks
    
    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Detecta secciones médicas en el texto.
        
        Returns:
            Lista de secciones con su tipo, inicio y fin
        """
        sections = []
        
        for section_type, pattern in self.MEDICAL_SECTIONS.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                sections.append({
                    "type": section_type,
                    "start": match.start(),
                    "header": match.group(0)
                })
        
        # Ordenar por posición
        sections.sort(key=lambda x: x["start"])
        
        # Determinar fin de cada sección
        for i, section in enumerate(sections):
            if i < len(sections) - 1:
                section["end"] = sections[i + 1]["start"]
            else:
                section["end"] = len(text)
        
        # Si no se detectaron secciones, retornar el documento completo
        if not sections:
            return [{
                "type": "full_document",
                "start": 0,
                "end": len(text),
                "header": ""
            }]
        
        return sections
    
    def _chunk_by_sections(
        self, 
        document: Document, 
        sections: List[Dict], 
        config: ChunkingConfig
    ) -> List[Chunk]:
        """Crea chunks basados en secciones detectadas."""
        chunks = []
        
        for idx, section in enumerate(sections):
            start = section["start"]
            end = section["end"]
            section_text = document.content[start:end].strip()
            
            token_count = self.tokenizer_fn(section_text)
            
            # Si la sección es muy grande, sub-dividir
            if token_count > config.chunk_size:
                sub_chunks = self._split_large_section(
                    section_text, 
                    start, 
                    config
                )
                for sub_idx, sub_chunk_text in enumerate(sub_chunks):
                    chunk = self._create_chunk(
                        document=document,
                        content=sub_chunk_text,
                        chunk_index=len(chunks),
                        start_char=start,  # Aproximación
                        section_type=section["type"]
                    )
                    chunks.append(chunk)
            else:
                # Sección completa como un chunk
                chunk = self._create_chunk(
                    document=document,
                    content=section_text,
                    chunk_index=idx,
                    start_char=start,
                    section_type=section["type"]
                )
                chunks.append(chunk)
        
        return chunks
    
    def _sliding_window_chunk(
        self, 
        document: Document, 
        config: ChunkingConfig
    ) -> List[Chunk]:
        """Chunking por ventana deslizante (fallback)."""
        chunks = []
        text = document.content
        
        # Dividir en oraciones (preservar contexto semántico)
        sentences = self._split_sentences(text)
        
        current_chunk_sentences = []
        current_token_count = 0
        start_char = 0
        
        for sentence in sentences:
            sentence_tokens = self.tokenizer_fn(sentence)
            
            if current_token_count + sentence_tokens > config.chunk_size:
                # Crear chunk con oraciones acumuladas
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    chunk = self._create_chunk(
                        document=document,
                        content=chunk_text,
                        chunk_index=len(chunks),
                        start_char=start_char
                    )
                    chunks.append(chunk)
                    
                    # Overlap: mantener últimas N oraciones
                    overlap_sentences = self._get_overlap_sentences(
                        current_chunk_sentences, 
                        config.chunk_overlap
                    )
                    current_chunk_sentences = overlap_sentences + [sentence]
                    current_token_count = sum(
                        self.tokenizer_fn(s) for s in current_chunk_sentences
                    )
                    start_char = text.find(current_chunk_sentences[0])
                else:
                    # Oración muy larga, incluirla sola
                    current_chunk_sentences = [sentence]
                    current_token_count = sentence_tokens
            else:
                current_chunk_sentences.append(sentence)
                current_token_count += sentence_tokens
        
        # Último chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            chunk = self._create_chunk(
                document=document,
                content=chunk_text,
                chunk_index=len(chunks),
                start_char=start_char
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        document: Document,
        content: str,
        chunk_index: int,
        start_char: int,
        section_type: Optional[str] = None
    ) -> Chunk:
        """Helper para crear objeto Chunk."""
        chunk_id = f"{document.id}_chunk_{chunk_index}"
        
        return Chunk(
            chunk_id=chunk_id,
            document_id=document.id,
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=start_char + len(content),
            token_count=self.tokenizer_fn(content),
            section_type=section_type,
            original_metadata=document.metadata if hasattr(document, 'metadata') else None
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Divide texto en oraciones (aproximación simple)."""
        # Regex para detectar fin de oración
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_sentences(
        self, 
        sentences: List[str], 
        overlap_tokens: int
    ) -> List[str]:
        """Retorna últimas oraciones que sumen ~overlap_tokens."""
        overlap_sentences = []
        token_count = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = self.tokenizer_fn(sentence)
            if token_count + sentence_tokens > overlap_tokens:
                break
            overlap_sentences.insert(0, sentence)
            token_count += sentence_tokens
        
        return overlap_sentences
    
    def _split_large_section(
        self, 
        text: str, 
        base_start: int, 
        config: ChunkingConfig
    ) -> List[str]:
        """Divide sección grande en sub-chunks."""
        # Usar sliding window para sección grande
        sentences = self._split_sentences(text)
        sub_chunks = []
        current = []
        current_tokens = 0
        
        for sentence in sentences:
            tokens = self.tokenizer_fn(sentence)
            if current_tokens + tokens > config.chunk_size and current:
                sub_chunks.append(" ".join(current))
                # Overlap
                overlap = self._get_overlap_sentences(current, config.chunk_overlap)
                current = overlap + [sentence]
                current_tokens = sum(self.tokenizer_fn(s) for s in current)
            else:
                current.append(sentence)
                current_tokens += tokens
        
        if current:
            sub_chunks.append(" ".join(current))
        
        return sub_chunks
    
    def _calculate_quality_score(self, chunk: Chunk) -> float:
        """
        Calcula score de calidad del chunk.
        
        Factores:
        - Completitud (no muy corto)
        - Coherencia (tiene suficiente contexto)
        - Densidad de información médica
        """
        score = 1.0
        
        # Penalizar chunks muy cortos
        if chunk.token_count < 50:
            score *= 0.7
        
        # Penalizar chunks sin puntuación final
        if not chunk.content.strip().endswith(('.', '!', '?')):
            score *= 0.9
        
        # Bonus por sección identificada
        if chunk.section_type and chunk.section_type != "full_document":
            score *= 1.1
        
        # Bonus por entidades médicas (si existen)
        if chunk.medical_entities and len(chunk.medical_entities) > 0:
            score *= 1.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    def chunk_batch(
        self, 
        documents: List[Document], 
        config: Optional[ChunkingConfig] = None
    ) -> List[List[Chunk]]:
        """Procesa múltiples documentos."""
        return [self.chunk_document(doc, config) for doc in documents]
    
    def estimate_chunks(self, document: Document) -> int:
        """Estima número de chunks."""
        total_tokens = self.tokenizer_fn(document.content)
        config = ChunkingConfig()
        # Fórmula aproximada
        avg_chunk_size = config.chunk_size - config.chunk_overlap
        return max(1, total_tokens // avg_chunk_size)
```

### 4.3 Estrategia de Chunking RECOMENDADA para Médico

**Para documentos médicos, recomiendo:**

1. **Prioridad 1**: `MedicalSectionChunker` 
   - Respeta estructura médica estándar
   - Preserva contexto clínico
   - Facilita búsqueda por tipo de información

2. **Prioridad 2**: `SemanticChunker` (con embeddings)
   - Segmenta por coherencia semántica
   - Usa modelo para detectar cambios de tópicos
   - Más lento pero mejor calidad

3. **Fallback**: `SlidingWindowChunker`
   - Simple y rápido
   - Garantiza tamaño uniforme
   - Bueno para textos sin estructura clara

---

## 6. Fase 3: Generación de Embeddings

### 6.1 Schema de Embedding

```python
# core/schemas/embedding_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
import numpy as np

class EmbeddingConfig(BaseModel):
    """Configuración para generación de embeddings."""
    
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Nombre/path del modelo"
    )
    
    normalize: bool = Field(
        default=True,
        description="Normalizar vectores a longitud unitaria"
    )
    
    batch_size: int = Field(
        default=32,
        ge=1,
        le=512,
        description="Tamaño de lote para procesamiento"
    )
    
    device: Literal["cpu", "cuda", "mps"] = Field(
        default="cpu",
        description="Dispositivo de cómputo"
    )
    
    max_length: Optional[int] = Field(
        default=512,
        description="Longitud máxima de tokens"
    )
    
    pooling_strategy: Literal["mean", "cls", "max"] = Field(
        default="mean",
        description="Estrategia de pooling"
    )
    
    cache_enabled: bool = Field(
        default=True,
        description="Habilitar caché de embeddings"
    )


class EmbeddingResult(BaseModel):
    """Resultado de embedding."""
    
    text_id: str
    vector: list[float]  # Pydantic serializa numpy arrays
    model_name: str
    dimension: int
    normalized: bool
    
    class Config:
        arbitrary_types_allowed = True
```

### 5.2 Implementación: CachedBiomedicalEmbedder

```python
# adapters/embeddings/cached_biomedical_embedder.py
from typing import List, Optional, Dict
import numpy as np
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer

from ...core.ports.embedding_port import EmbeddingPort
from ...core.schemas.embedding_schema import EmbeddingConfig

class CachedBiomedicalEmbedder(EmbeddingPort):
    """
    Embedder con caché para dominios biomédicos.
    Soporta múltiples modelos:
    - all-MiniLM-L6-v2 (general, rápido)
    - PubMedBERT (biomédico, mejor calidad)
    - BioClinicalBERT (clínico)
    """
    
    RECOMMENDED_MODELS = {
        "fast": "sentence-transformers/all-MiniLM-L6-v2",  # 384 dim
        "biomedical": "dmis-lab/biobert-base-cased-v1.2",  # 768 dim
        "clinical": "emilyalsentzer/Bio_ClinicalBERT",     # 768 dim
        "pubmed": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"  # 768 dim
    }
    
    def __init__(
        self, 
        config: Optional[EmbeddingConfig] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Args:
            config: Configuración de embeddings
            cache_dir: Directorio para caché persistente
        """
        self.config = config or EmbeddingConfig()
        self.cache_dir = cache_dir or Path("./data/cache/embeddings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar modelo
        self.model = SentenceTransformer(
            self.config.model_name,
            device=self.config.device
        )
        
        # Caché en memoria (LRU)
        self._memory_cache: Dict[str, np.ndarray] = {}
        self._max_memory_cache = 10000
    
    def encode(
        self, 
        texts: List[str], 
        config: Optional[EmbeddingConfig] = None
    ) -> np.ndarray:
        """
        Genera embeddings con caché inteligente.
        """
        cfg = config or self.config
        
        # Verificar caché
        embeddings = []
        texts_to_encode = []
        indices_to_encode = []
        
        for idx, text in enumerate(texts):
            cache_key = self._generate_cache_key(text, cfg)
            
            # Buscar en memoria
            if cache_key in self._memory_cache:
                embeddings.append(self._memory_cache[cache_key])
            # Buscar en disco
            elif cfg.cache_enabled:
                cached = self._load_from_disk_cache(cache_key)
                if cached is not None:
                    embeddings.append(cached)
                    self._memory_cache[cache_key] = cached
                else:
                    texts_to_encode.append(text)
                    indices_to_encode.append(idx)
                    embeddings.append(None)  # Placeholder
            else:
                texts_to_encode.append(text)
                indices_to_encode.append(idx)
                embeddings.append(None)
        
        # Generar embeddings faltantes
        if texts_to_encode:
            new_embeddings = self.model.encode(
                texts_to_encode,
                batch_size=cfg.batch_size,
                normalize_embeddings=cfg.normalize,
                show_progress_bar=len(texts_to_encode) > 100,
                convert_to_numpy=True
            )
            
            # Actualizar caché y resultado
            for idx, text_idx in enumerate(indices_to_encode):
                embedding = new_embeddings[idx]
                embeddings[text_idx] = embedding
                
                # Guardar en caché
                if cfg.cache_enabled:
                    cache_key = self._generate_cache_key(texts[text_idx], cfg)
                    self._save_to_disk_cache(cache_key, embedding)
                    self._memory_cache[cache_key] = embedding
        
        # Limpiar caché en memoria si excede límite
        if len(self._memory_cache) > self._max_memory_cache:
            self._evict_memory_cache()
        
        return np.array(embeddings)
    
    def encode_query(
        self, 
        query: str, 
        config: Optional[EmbeddingConfig] = None
    ) -> np.ndarray:
        """
        Encode query (puede tener prefijo especial para modelos asimétricos).
        """
        cfg = config or self.config
        
        # Algunos modelos usan prefijos diferentes para queries
        # Por ejemplo: "query: " vs "passage: "
        query_text = self._prepare_query(query)
        
        return self.encode([query_text], cfg)[0]
    
    def _prepare_query(self, query: str) -> str:
        """
        Prepara query según el modelo.
        Algunos modelos asimétricos necesitan prefijos.
        """
        # Para modelos simétricos (como BioBERT), no hacer nada
        # Para modelos asimétricos, añadir prefijo
        
        if "asymmetric" in self.config.model_name.lower():
            return f"query: {query}"
        
        return query
    
    def _generate_cache_key(self, text: str, config: EmbeddingConfig) -> str:
        """
        Genera key de caché única basada en texto y configuración.
        """
        # Hash del texto + parámetros relevantes
        cache_input = {
            "text": text,
            "model": config.model_name,
            "normalize": config.normalize,
            "max_length": config.max_length
        }
        
        cache_str = json.dumps(cache_input, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def _load_from_disk_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """Carga embedding desde caché en disco."""
        cache_file = self.cache_dir / f"{cache_key}.npy"
        
        if cache_file.exists():
            try:
                return np.load(cache_file)
            except:
                # Caché corrupto, eliminar
                cache_file.unlink(missing_ok=True)
                return None
        
        return None
    
    def _save_to_disk_cache(self, cache_key: str, embedding: np.ndarray) -> None:
        """Guarda embedding en caché de disco."""
        cache_file = self.cache_dir / f"{cache_key}.npy"
        
        try:
            np.save(cache_file, embedding)
        except Exception as e:
            # Error al guardar caché, no es crítico
            pass
    
    def _evict_memory_cache(self) -> None:
        """
        Elimina entradas antiguas del caché en memoria.
        Estrategia: FIFO simple (eliminar primeras 20%)
        """
        num_to_remove = len(self._memory_cache) // 5
        keys_to_remove = list(self._memory_cache.keys())[:num_to_remove]
        
        for key in keys_to_remove:
            del self._memory_cache[key]
    
    def get_dimension(self) -> int:
        """Retorna dimensionalidad de embeddings."""
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """
        Retorna información del modelo.
        """
        return {
            "model_name": self.config.model_name,
            "dimension": self.get_dimension(),
            "max_seq_length": self.model.max_seq_length,
            "device": str(self.model.device),
            "normalize": self.config.normalize,
            "recommended_for": self._get_recommendations()
        }
    
    def _get_recommendations(self) -> List[str]:
        """Retorna para qué tipo de consultas es mejor este modelo."""
        model_name_lower = self.config.model_name.lower()
        
        if "pubmed" in model_name_lower or "bio" in model_name_lower:
            return ["medical", "biomedical", "clinical", "scientific"]
        elif "clinical" in model_name_lower:
            return ["clinical_notes", "patient_records", "diagnosis"]
        else:
            return ["general", "fast"]
    
    def clear_cache(self) -> None:
        """Limpia caché en memoria y disco."""
        self._memory_cache.clear()
        
        # Limpiar caché en disco
        for cache_file in self.cache_dir.glob("*.npy"):
            cache_file.unlink()
```

### 5.3 Recomendación de Modelos para Diagnósticos Médicos

| Modelo | Dimensión | Velocidad | Calidad Médica | Uso Recomendado |
|--------|-----------|-----------|----------------|-----------------|
| **all-MiniLM-L6-v2** | 384 | ⚡⚡⚡ Muy rápido | ⭐⭐ Básica | Prototipado, testing |
| **BiomedNLP-PubMedBERT** | 768 | ⚡⚡ Medio | ⭐⭐⭐⭐ Excelente | **Producción (RECOMENDADO)** |
| **Bio_ClinicalBERT** | 768 | ⚡⚡ Medio | ⭐⭐⭐⭐⭐ Superior | Notas clínicas, EHR |
| **BioBERT** | 768 | ⚡⚡ Medio | ⭐⭐⭐⭐ Muy buena | Literatura biomédica |

**Para SRI-DX, recomiendo:**
- **Desarrollo/Testing**: all-MiniLM-L6-v2 (rápido, suficientemente bueno)
- **Producción**: BiomedNLP-PubMedBERT (balance calidad/velocidad)
- **Máxima Precisión**: Bio_ClinicalBERT (si los datos son principalmente notas clínicas)

---

## 7. Fase 4: Adaptador Elasticsearch (Núcleo)

### 7.1 ⭐ Adaptador Elasticsearch (RECOMENDADO para SRI-DX)

**¿Por qué Elasticsearch primero?**

✅ **Todo-en-uno**: Índice léxico (BM25) + vectorial (kNN) en un solo sistema  
✅ **Híbrido nativo**: Combina ambos tipos de búsqueda en una sola query (desde ES 8.4+)  
✅ **Filtros nativos**: Metadata médica sin código adicional  
✅ **Escalabilidad probada**: Sharding, réplicas, clustering incluidos  
✅ **Ya funcional**: Según tu `main.py` ya tienes base trabajando  
✅ **Monitoreo**: Kibana, métricas, alertas out-of-the-box  

```python
# adapters/stores/elasticsearch_vector_adapter.py
from typing import List, Optional, Dict, Any
import numpy as np
from elasticsearch import Elasticsearch, helpers
from datetime import datetime

from ...core.ports.vector_index_port import VectorIndexPort
from ...core.ports.lexical_index_port import LexicalIndexPort
from ...core.schemas.search_result_schema import (
    VectorSearchResult, 
    LexicalSearchResult,
    HybridSearchResult
)
from ...core.schemas.search_query_schema import LexicalQuery

class ElasticsearchVectorAdapter(VectorIndexPort, LexicalIndexPort):
    """
    Adaptador dual para Elasticsearch:
    - Implementa búsqueda vectorial (kNN)
    - Implementa búsqueda léxica (BM25)
    - Soporta búsqueda híbrida nativa
    
    Ventajas:
    - Un solo sistema para ambos tipos de búsqueda
    - Filtros de metadata nativos
    - Escalabilidad horizontal (sharding)
    - Persistencia automática
    """
    
    def __init__(
        self,
        hosts: List[str] = None,
        index_name: str = "medical_diagnosis",
        dimension: int = 768,
        similarity: str = "cosine",  # "cosine", "dot_product", "l2_norm"
        **es_config
    ):
        """
        Args:
            hosts: Lista de hosts ES (default: ["http://localhost:9200"])
            index_name: Nombre del índice
            dimension: Dimensión de vectores
            similarity: Métrica de similitud
            **es_config: Parámetros adicionales para Elasticsearch client
        """
        self.hosts = hosts or ["http://localhost:9200"]
        self.index_name = index_name
        self.dimension = dimension
        self.similarity = similarity
        
        # Cliente Elasticsearch
        self.es = Elasticsearch(self.hosts, **es_config)
        
        # Verificar conexión
        if not self.es.ping():
            raise ConnectionError(f"No se pudo conectar a Elasticsearch en {self.hosts}")
        
        print(f"✅ Conectado a Elasticsearch: {self.es.info()['version']['number']}")
    
    def build_index(
        self,
        vectors: np.ndarray,
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict] = None
    ) -> None:
        """
        Crea el índice con mappings para vectores + texto.
        
        Schema del documento:
        {
            "id": "doc_123",
            "content": "texto del documento",
            "embedding": [0.1, 0.2, ...],  # Vector denso
            "metadata": {
                "specialty": "cardiology",
                "year": 2024,
                ...
            },
            "indexed_at": "2026-03-02T10:30:00Z"
        }
        """
        cfg = config or {}
        n_samples = vectors.shape[0]
        
        # 1. Eliminar índice si existe (recreación completa)
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)
            print(f"🗑️ Índice {self.index_name} eliminado")
        
        # 2. Crear índice con mappings
        index_mappings = {
            "settings": {
                "number_of_shards": cfg.get("num_shards", 1),
                "number_of_replicas": cfg.get("num_replicas", 1),
                "index": {
                    "similarity": {
                        "default": {
                            "type": "BM25",
                            "k1": cfg.get("bm25_k1", 1.2),
                            "b": cfg.get("bm25_b", 0.75)
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "standard",
                        "similarity": "default"  # BM25
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.dimension,
                        "index": True,
                        "similarity": self.similarity  # cosine, dot_product, l2_norm
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        self.es.indices.create(index=self.index_name, body=index_mappings)
        print(f"✅ Índice {self.index_name} creado con mappings vectoriales")
        
        # 3. Indexar documentos en bulk
        actions = []
        for i, (doc_id, vector) in enumerate(zip(ids, vectors)):
            doc = {
                "_index": self.index_name,
                "_id": doc_id,
                "_source": {
                    "id": doc_id,
                    "content": metadata[i].get("content", "") if metadata else "",
                    "embedding": vector.tolist(),
                    "metadata": metadata[i] if metadata else {},
                    "indexed_at": datetime.utcnow().isoformat()
                }
            }
            actions.append(doc)
        
        # Bulk insert
        success, errors = helpers.bulk(self.es, actions, raise_on_error=False)
        
        # Refresh para que sean buscables inmediatamente
        self.es.indices.refresh(index=self.index_name)
        
        print(f"✅ Indexados {success}/{n_samples} documentos")
        if errors:
            print(f"⚠️ {len(errors)} errores durante indexación")
    
    # ========== BÚSQUEDA VECTORIAL (kNN) ==========
    
    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        filter_criteria: Optional[Dict] = None
    ) -> List[VectorSearchResult]:
        """
        Búsqueda vectorial pura (kNN).
        
        Args:
            query_vector: Vector de consulta
            k: Número de resultados
            filter_criteria: Filtros sobre metadata
        
        Returns:
            Resultados ordenados por similitud vectorial
        """
        # Construir query kNN
        knn_query = {
            "field": "embedding",
            "query_vector": query_vector.tolist(),
            "k": k,
            "num_candidates": k * 10  # Sobre-fetch para mejor recall
        }
        
        # Agregar filtros si existen
        if filter_criteria:
            knn_query["filter"] = self._build_es_filter(filter_criteria)
        
        # Ejecutar búsqueda
        response = self.es.search(
            index=self.index_name,
            knn=knn_query,
            size=k
        )
        
        # Procesar resultados
        results = []
        for hit in response["hits"]["hits"]:
            result = VectorSearchResult(
                id=hit["_id"],
                score=hit["_score"],
                content=hit["_source"].get("content", ""),
                metadata=hit["_source"].get("metadata", {}),
                distance=1.0 - hit["_score"] if self.similarity == "cosine" else None
            )
            results.append(result)
        
        return results
    
    # ========== BÚSQUEDA LÉXICA (BM25) ==========
    
    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "content",
        config: Optional[Dict] = None
    ) -> None:
        """
        Indexa documentos para búsqueda léxica.
        (Ya incluido en build_index, pero útil para updates)
        """
        actions = []
        for doc in documents:
            action = {
                "_index": self.index_name,
                "_id": doc["id"],
                "_source": doc
            }
            actions.append(action)
        
        helpers.bulk(self.es, actions)
        self.es.indices.refresh(index=self.index_name)
    
    def search_lexical(
        self,
        query: LexicalQuery,
        k: int = 50,
        filter_criteria: Optional[Dict] = None
    ) -> List[LexicalSearchResult]:
        """
        Búsqueda léxica pura (BM25).
        """
        # Construir query BM25
        es_query = {
            "bool": {
                "must": [
                    {
                        "match": {
                            "content": {
                                "query": query.text,
                                "operator": query.operator.lower()
                            }
                        }
                    }
                ]
            }
        }
        
        # Agregar filtros
        if filter_criteria:
            es_query["bool"]["filter"] = self._build_es_filter(filter_criteria)
        
        # Ejecutar búsqueda
        response = self.es.search(
            index=self.index_name,
            query=es_query,
            size=k
        )
        
        # Procesar resultados
        results = []
        for hit in response["hits"]["hits"]:
            result = LexicalSearchResult(
                id=hit["_id"],
                score=hit["_score"],
                content=hit["_source"].get("content", ""),
                metadata=hit["_source"].get("metadata", {}),
                bm25_score=hit["_score"]
            )
            results.append(result)
        
        return results
    
    # ========== BÚSQUEDA HÍBRIDA NATIVA ==========
    
    def search_hybrid(
        self,
        query_text: str,
        query_vector: np.ndarray,
        k: int = 10,
        alpha: float = 0.5,  # Peso: 0.0 = solo léxico, 1.0 = solo vectorial
        filter_criteria: Optional[Dict] = None
    ) -> List[HybridSearchResult]:
        """
        Búsqueda híbrida NATIVA de Elasticsearch.
        Combina kNN + BM25 en una sola query.
        
        Elasticsearch 8.4+ permite combinar kNN con query tradicional:
        - kNN search para similitud semántica
        - Match query para coincidencias léxicas
        - Combina scores automáticamente
        """
        # Query híbrida
        hybrid_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector.tolist(),
                "k": k,
                "num_candidates": k * 10,
                "boost": alpha  # Peso para kNN
            },
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "content": {
                                    "query": query_text,
                                    "boost": 1.0 - alpha  # Peso para BM25
                                }
                            }
                        }
                    ]
                }
            },
            "size": k
        }
        
        # Agregar filtros
        if filter_criteria:
            hybrid_query["query"]["bool"]["filter"] = self._build_es_filter(filter_criteria)
        
        # Ejecutar búsqueda híbrida
        response = self.es.search(index=self.index_name, **hybrid_query)
        
        # Procesar resultados
        results = []
        for hit in response["hits"]["hits"]:
            result = HybridSearchResult(
                id=hit["_id"],
                score=hit["_score"],
                content=hit["_source"].get("content", ""),
                metadata=hit["_source"].get("metadata", {}),
                vector_score=hit.get("_knn_score", 0.0),  # Score kNN
                lexical_score=hit["_score"] - hit.get("_knn_score", 0.0),  # Aproximación
                fusion_method="elasticsearch_native",
                fusion_weights={"vector": alpha, "lexical": 1.0 - alpha}
            )
            results.append(result)
        
        return results
    
    # ========== UTILIDADES ==========
    
    def _build_es_filter(self, criteria: Dict) -> List[Dict]:
        """
        Convierte criterios de filtro a formato Elasticsearch.
        
        Ejemplo:
        {
            "specialty": "cardiology",
            "year": {"$gte": 2020}
        }
        ->
        [
            {"term": {"metadata.specialty": "cardiology"}},
            {"range": {"metadata.year": {"gte": 2020}}}
        ]
        """
        filters = []
        
        for key, value in criteria.items():
            field = f"metadata.{key}"
            
            if isinstance(value, dict):
                # Operadores
                for op, op_value in value.items():
                    if op in ["$eq", "$ne"]:
                        filters.append({"term": {field: op_value}})
                    elif op in ["$gt", "$gte", "$lt", "$lte"]:
                        es_op = op[1:]  # Quitar '$'
                        filters.append({"range": {field: {es_op: op_value}}})
                    elif op == "$in":
                        filters.append({"terms": {field: op_value}})
            else:
                # Igualdad simple
                filters.append({"term": {field: value}})
        
        return filters
    
    def add_vectors(
        self,
        vectors: np.ndarray,
        ids: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """Añade vectores al índice (incremental)."""
        actions = []
        for i, (doc_id, vector) in enumerate(zip(ids, vectors)):
            doc = {
                "_index": self.index_name,
                "_id": doc_id,
                "_source": {
                    "id": doc_id,
                    "content": metadata[i].get("content", "") if metadata else "",
                    "embedding": vector.tolist(),
                    "metadata": metadata[i] if metadata else {},
                    "indexed_at": datetime.utcnow().isoformat()
                }
            }
            actions.append(doc)
        
        helpers.bulk(self.es, actions)
        self.es.indices.refresh(index=self.index_name)
    
    def remove_vectors(self, ids: List[str]) -> None:
        """Elimina vectores del índice."""
        actions = [
            {"_op_type": "delete", "_index": self.index_name, "_id": doc_id}
            for doc_id in ids
        ]
        helpers.bulk(self.es, actions, raise_on_error=False)
    
    def save_index(self, path: str) -> None:
        """No necesario - Elasticsearch persiste automáticamente."""
        print("ℹ️ Elasticsearch persiste automáticamente. No se requiere save manual.")
    
    def load_index(self, path: str) -> None:
        """No necesario - Índice en Elasticsearch."""
        print("ℹ️ Conectado a índice existente en Elasticsearch.")
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Estadísticas del índice."""
        stats = self.es.indices.stats(index=self.index_name)
        index_stats = stats["indices"][self.index_name]
        
        return {
            "backend": "Elasticsearch",
            "index_name": self.index_name,
            "dimension": self.dimension,
            "similarity": self.similarity,
            "num_documents": index_stats["total"]["docs"]["count"],
            "size_bytes": index_stats["total"]["store"]["size_in_bytes"],
            "size_mb": index_stats["total"]["store"]["size_in_bytes"] / (1024 * 1024),
            "shards": index_stats["total"]["shard_stats"]["total_count"],
            "health": self.es.cluster.health()["status"]
        }
    
    def explain_score(self, query: str, doc_id: str) -> Dict[str, Any]:
        """Explica cómo se calculó el score de un documento."""
        response = self.es.explain(
            index=self.index_name,
            id=doc_id,
            query={"match": {"content": query}}
        )
        return response["explanation"]
```

**Ejemplo de uso:**

```python
# Inicialización
adapter = ElasticsearchVectorAdapter(
    hosts=["http://localhost:9200"],
    index_name="medical_diagnosis",
    dimension=768,
    similarity="cosine"
)

# Indexar documentos con vectores + texto
adapter.build_index(
    vectors=embeddings,  # np.array (n, 768)
    ids=["doc_1", "doc_2", ...],
    metadata=[
        {"content": "Patient with chest pain...", "specialty": "cardiology"},
        {"content": "Diabetes mellitus type 2...", "specialty": "endocrinology"},
    ]
)

# Búsqueda híbrida nativa
results = adapter.search_hybrid(
    query_text="chest pain shortness of breath",
    query_vector=query_embedding,
    k=10,
    alpha=0.7,  # 70% vectorial, 30% léxico
    filter_criteria={"specialty": "cardiology"}
)
```

---

### 6.2 Adaptador HNSW (Alternativa para casos específicos)

```python
# adapters/ann/hnsw_adapter.py
from typing import List, Optional, Dict, Any
import numpy as np
import hnswlib
import pickle
from pathlib import Path

from ...core.ports.vector_index_port import VectorIndexPort
from ...core.schemas.search_result_schema import VectorSearchResult

class HNSWAdapter(VectorIndexPort):
    """
    Adaptador para HNSWLib.
    - Rápido (búsquedas en milisegundos)
    - Eficiente en memoria
    - Soporta incremental indexing
    - Ideal hasta ~10M vectores
    """
    
    def __init__(
        self,
        dimension: int,
        space: str = "cosine",  # "cosine", "l2", "ip" (inner product)
        max_elements: int = 1000000
    ):
        """
        Args:
            dimension: Dimensionalidad de vectores
            space: Métrica de distancia
            max_elements: Capacidad máxima del índice
        """
        self.dimension = dimension
        self.space = space
        self.max_elements = max_elements
        
        # Índice HNSW
        self.index = hnswlib.Index(space=space, dim=dimension)
        
        # Mapeo de índices internos a IDs externos
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}
        
        # Almacén de metadatos
        self.metadata_store: Dict[str, Dict[str, Any]] = {}
        
        # Control
        self.current_count = 0
        self.is_initialized = False
    
    def build_index(
        self, 
        vectors: np.ndarray, 
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict] = None
    ) -> None:
        """
        Construye el índice HNSW.
        
        Args:
            vectors: Array (n_samples, dimension)
            ids: IDs únicos (len == n_samples)
            metadata: Metadatos opcionales por vector
            config: Parámetros HNSW
                - ef_construction: Calidad construcción (default: 200)
                - M: Conexiones por nodo (default: 32)
        """
        n_samples = vectors.shape[0]
        
        if len(ids) != n_samples:
            raise ValueError(f"IDs length ({len(ids)}) != vectors length ({n_samples})")
        
        # Configuración HNSW
        cfg = config or {}
        ef_construction = cfg.get("ef_construction", 200)
        M = cfg.get("M", 32)
        
        # Inicializar índice
        self.index.init_index(
            max_elements=max(self.max_elements, n_samples),
            ef_construction=ef_construction,
            M=M
        )
        
        # Añadir vectores
        internal_ids = np.arange(n_samples)
        self.index.add_items(vectors, internal_ids)
        
        # Mapear IDs
        for idx, ext_id in enumerate(ids):
            self.id_to_idx[ext_id] = idx
            self.idx_to_id[idx] = ext_id
        
        # Guardar metadatos
        if metadata:
            for ext_id, meta in zip(ids, metadata):
                self.metadata_store[ext_id] = meta
        
        self.current_count = n_samples
        self.is_initialized = True
        
        # Configurar ef para búsqueda (mayor = mejor recall)
        self.index.set_ef(cfg.get("ef_search", 50))
    
    def search(
        self, 
        query_vector: np.ndarray, 
        k: int = 10,
        filter_criteria: Optional[Dict] = None
    ) -> List[VectorSearchResult]:
        """
        Búsqueda de K vecinos más cercanos.
        """
        if not self.is_initialized:
            raise RuntimeError("Index not initialized. Call build_index() first.")
        
        # HNSW necesita vector 2D
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Búsqueda (retorna índices internos y distancias)
        # Si hay filtros, buscar más resultados y filtrar después
        k_search = k * 10 if filter_criteria else k
        k_search = min(k_search, self.current_count)
        
        internal_ids, distances = self.index.knn_query(query_vector, k=k_search)
        
        # Convertir a IDs externos
        results = []
        for int_id, distance in zip(internal_ids[0], distances[0]):
            ext_id = self.idx_to_id[int_id]
            metadata = self.metadata_store.get(ext_id, {})
            
            # Aplicar filtros si existen
            if filter_criteria and not self._matches_filter(metadata, filter_criteria):
                continue
            
            # Convertir distancia a score (para cosine: score = 1 - distance)
            score = self._distance_to_score(distance)
            
            result = VectorSearchResult(
                id=ext_id,
                score=score,
                distance=float(distance),
                metadata=metadata
            )
            results.append(result)
            
            # Detener si alcanzamos k resultados
            if len(results) >= k:
                break
        
        return results
    
    def batch_search(
        self, 
        query_vectors: np.ndarray, 
        k: int = 10
    ) -> List[List[VectorSearchResult]]:
        """Búsqueda por lotes."""
        if not self.is_initialized:
            raise RuntimeError("Index not initialized.")
        
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)
        
        # Búsqueda vectorizada
        internal_ids, distances = self.index.knn_query(query_vectors, k=k)
        
        # Convertir resultados
        all_results = []
        for row_ids, row_distances in zip(internal_ids, distances):
            row_results = []
            for int_id, distance in zip(row_ids, row_distances):
                ext_id = self.idx_to_id[int_id]
                score = self._distance_to_score(distance)
                
                result = VectorSearchResult(
                    id=ext_id,
                    score=score,
                    distance=float(distance),
                    metadata=self.metadata_store.get(ext_id, {})
                )
                row_results.append(result)
            all_results.append(row_results)
        
        return all_results
    
    def add_vectors(
        self, 
        vectors: np.ndarray, 
        ids: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """Añade vectores al índice existente (incremental)."""
        if not self.is_initialized:
            raise RuntimeError("Index not initialized.")
        
        n_new = vectors.shape[0]
        
        # Verificar capacidad
        if self.current_count + n_new > self.max_elements:
            raise RuntimeError(
                f"Index capacity exceeded. "
                f"Max: {self.max_elements}, Current: {self.current_count}, Adding: {n_new}"
            )
        
        # IDs internos para los nuevos vectores
        internal_ids = np.arange(self.current_count, self.current_count + n_new)
        
        # Añadir al índice
        self.index.add_items(vectors, internal_ids)
        
        # Actualizar mapeos
        for idx, ext_id in zip(internal_ids, ids):
            self.id_to_idx[ext_id] = int(idx)
            self.idx_to_id[int(idx)] = ext_id
        
        # Guardar metadatos
        if metadata:
            for ext_id, meta in zip(ids, metadata):
                self.metadata_store[ext_id] = meta
        
        self.current_count += n_new
    
    def remove_vectors(self, ids: List[str]) -> None:
        """
        Marca vectores como eliminados (soft delete en HNSW).
        """
        for ext_id in ids:
            if ext_id in self.id_to_idx:
                int_id = self.id_to_idx[ext_id]
                self.index.mark_deleted(int_id)
                
                # Limpiar metadatos
                self.metadata_store.pop(ext_id, None)
    
    def save_index(self, path: str) -> None:
        """Persiste el índice y metadatos."""
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar índice HNSW
        index_path = str(path_obj.with_suffix(".hnsw"))
        self.index.save_index(index_path)
        
        # Guardar metadatos y mapeos
        meta_path = str(path_obj.with_suffix(".meta"))
        metadata = {
            "id_to_idx": self.id_to_idx,
            "idx_to_id": self.idx_to_id,
            "metadata_store": self.metadata_store,
            "current_count": self.current_count,
            "dimension": self.dimension,
            "space": self.space,
            "max_elements": self.max_elements
        }
        
        with open(meta_path, "wb") as f:
            pickle.dump(metadata, f)
    
    def load_index(self, path: str) -> None:
        """Carga el índice desde disco."""
        path_obj = Path(path)
        
        # Cargar índice HNSW
        index_path = str(path_obj.with_suffix(".hnsw"))
        if not Path(index_path).exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        
        self.index.load_index(index_path)
        
        # Cargar metadatos
        meta_path = str(path_obj.with_suffix(".meta"))
        with open(meta_path, "rb") as f:
            metadata = pickle.load(f)
        
        self.id_to_idx = metadata["id_to_idx"]
        self.idx_to_id = metadata["idx_to_id"]
        self.metadata_store = metadata["metadata_store"]
        self.current_count = metadata["current_count"]
        self.dimension = metadata["dimension"]
        self.space = metadata["space"]
        self.max_elements = metadata["max_elements"]
        
        self.is_initialized = True
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Estadísticas del índice."""
        return {
            "algorithm": "HNSW",
            "dimension": self.dimension,
            "space": self.space,
            "num_vectors": self.current_count,
            "max_capacity": self.max_elements,
            "utilization": self.current_count / self.max_elements,
            "has_metadata": len(self.metadata_store) > 0,
            "index_size_mb": self._estimate_size_mb()
        }
    
    def _distance_to_score(self, distance: float) -> float:
        """Convierte distancia a score de similitud."""
        if self.space == "cosine":
            # Cosine: 0 = idéntico, 2 = opuestos
            # Score: 1 = idéntico, 0 = completamente diferente
            return 1.0 - (distance / 2.0)
        elif self.space == "ip":  # Inner product
            # IP es score directo (mayor = más similar)
            return distance
        else:  # L2
            # L2: menor distancia = más similar
            # Normalizar: score = 1 / (1 + distance)
            return 1.0 / (1.0 + distance)
    
    def _matches_filter(self, metadata: Dict, criteria: Dict) -> bool:
        """Verifica si metadata cumple criterios de filtro."""
        for key, value in criteria.items():
            if key not in metadata:
                return False
            
            meta_value = metadata[key]
            
            # Soportar operadores MongoDB-style
            if isinstance(value, dict):
                for op, op_value in value.items():
                    if op == "$eq" and meta_value != op_value:
                        return False
                    elif op == "$ne" and meta_value == op_value:
                        return False
                    elif op == "$gt" and meta_value <= op_value:
                        return False
                    elif op == "$gte" and meta_value < op_value:
                        return False
                    elif op == "$lt" and meta_value >= op_value:
                        return False
                    elif op == "$lte" and meta_value > op_value:
                        return False
                    elif op == "$in" and meta_value not in op_value:
                        return False
            else:
                # Igualdad simple
                if meta_value != value:
                    return False
        
        return True
    
    def _estimate_size_mb(self) -> float:
        """Estima tamaño del índice en MB."""
        # Aproximación: cada vector + metadata
        vector_size = self.current_count * self.dimension * 4  # float32
        metadata_size = len(str(self.metadata_store).encode())
        total_bytes = vector_size + metadata_size
        return total_bytes / (1024 * 1024)
```

---

## 8. Fase 5: Casos de Uso de Búsqueda

### 8.1 Puerto de Búsqueda Unificado

```python
# core/ports/search_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np
from ..schemas.search_query_schema import SearchQuery
from ..schemas.search_result_schema import SearchResult

class SearchPort(ABC):
    """
    Puerto unificado para búsqueda.
    Elasticsearch implementa todas las capacidades.
    """
    
    @abstractmethod
    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        config: Optional[Dict] = None
    ) -> None:
        """Indexa documentos con texto + embeddings + metadata."""
        pass
    
    @abstractmethod
    def search(
        self,
        query: SearchQuery,
        k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Búsqueda unificada.
        Tipo determinado por query.search_type:
        - "lexical": BM25
        - "semantic": kNN vectorial
        - "hybrid": Combinación nativa ES
        """
        pass
    
    @abstractmethod
    def delete_documents(self, ids: List[str]) -> None:
        """Elimina documentos del índice."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del índice."""
        pass
    
    @abstractmethod
    def explain(self, query: SearchQuery, doc_id: str) -> Dict:
        """Explica score de un documento."""
        pass
```

### 7.2 Schema de Query y Resultados

```python
# core/schemas/search_query_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class LexicalQuery(BaseModel):
    """Query léxica (keyword-based)."""
    
    text: str = Field(description="Texto de búsqueda")
    
    operator: str = Field(
        default="OR",
        description="Operador lógico: AND, OR"
    )
    
    fields: Optional[List[str]] = Field(
        default=None,
        description="Campos donde buscar (default: todos)"
    )
    
    boost_fields: Optional[Dict[str, float]] = Field(
        default=None,
        description="Boost por campo. Ej: {'title': 2.0, 'content': 1.0}"
    )
    
    fuzzy: bool = Field(
        default=False,
        description="Permitir coincidencias difusas"
    )
    
    phrase: bool = Field(
        default=False,
        description="Búsqueda de frase exacta"
    )


class SemanticQuery(BaseModel):
    """Query semántica (vector-based)."""
    
    text: str = Field(description="Texto de búsqueda semántica")
    
    embedding_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuración del embedder"
    )


class HybridQuery(BaseModel):
    """Query híbrida (combina léxica + semántica)."""
    
    text: str = Field(description="Texto de búsqueda")
    
    # Componentes opcionales
    lexical_query: Optional[LexicalQuery] = Field(
        default=None,
        description="Query léxica personalizada (si None, usa text)"
    )
    
    semantic_query: Optional[SemanticQuery] = Field(
        default=None,
        description="Query semántica personalizada (si None, usa text)"
    )
    
    # Filtros
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filtros por metadatos"
    )
    
    # Configuración de fusión
    fusion_strategy: str = Field(
        default="rrf",
        description="Estrategia de fusión: rrf, combsum, weighted"
    )
    
    alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Balance léxico vs semántico (0=léxico, 1=semántico)"
    )
    
    k: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Número de resultados"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "síntomas de infarto agudo de miocardio",
                "filters": {
                    "specialty": "cardiology",
                    "year": {"$gte": 2020}
                },
                "fusion_strategy": "rrf",
                "alpha": 0.6,
                "k": 20
            }
        }
```

```python
# core/schemas/search_result_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SearchResult(BaseModel):
    """Resultado base de búsqueda."""
    
    id: str
    score: float = Field(ge=0.0)
    metadata: Optional[Dict[str, Any]] = None


class VectorSearchResult(SearchResult):
    """Resultado de búsqueda vectorial."""
    
    distance: float
    vector_score: float = Field(alias="score")


class LexicalSearchResult(SearchResult):
    """Resultado de búsqueda léxica."""
    
    lexical_score: float = Field(alias="score")
    
    matched_terms: Optional[List[str]] = Field(
        default=None,
        description="Términos del query que coincidieron"
    )
    
    highlights: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Fragmentos resaltados del texto"
    )


class HybridSearchResult(SearchResult):
    """Resultado de búsqueda híbrida."""
    
    combined_score: float = Field(alias="score")
    
    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    
    lexical_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    
    matched_terms: Optional[List[str]] = None
    highlights: Optional[Dict[str, List[str]]] = None
    
    # Explicabilidad
    explanation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explicación del score (para auditoría)"
    )
    
    chunk_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Información del chunk si es búsqueda en chunks"
    )
```

### 7.2 Implementación: RecíprocalRankFusion (RRF)

```python
# modules/fusion/rrf_fusion.py
from typing import List, Dict, Optional
from collections import defaultdict
import math

from ...core.schemas.search_result_schema import (
    SearchResult, 
    HybridSearchResult,
    VectorSearchResult,
    LexicalSearchResult
)

class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) para combinar rankings.
    
    Paper: "Reciprocal Rank Fusion outperforms Condorcet and individual Rank 
            Learning Methods" (Cormack et al., 2009)
    
    Formula: RRF_score(doc) = Σ 1 / (k + rank(doc))
    where k es un parámetro (típicamente 60)
    """
    
    def __init__(self, k: int = 60):
        """
        Args:
            k: Parámetro de RRF (mayor k = menos peso a rankings altos)
        """
        self.k = k
    
    def fuse(
        self,
        lexical_results: List[LexicalSearchResult],
        vector_results: List[VectorSearchResult],
        top_k: int = 10,
        alpha: float = 0.5
    ) -> List[HybridSearchResult]:
        """
        Fusiona resultados léxicos y vectoriales usando RRF.
        
        Args:
            lexical_results: Resultados de búsqueda léxica
            vector_results: Resultados de búsqueda vectorial
            top_k: Número de resultados finales
            alpha: Peso de vectorial vs léxico (no usado en RRF puro, 
                   pero incluido para compatibilidad con interface)
        
        Returns:
            Resultados fusionados ordenados por RRF score
        """
        # Calcular scores RRF
        rrf_scores: Dict[str, float] = defaultdict(float)
        doc_info: Dict[str, Dict] = {}
        
        # Procesar resultados léxicos
        for rank, result in enumerate(lexical_results, start=1):
            doc_id = result.id
            rrf_score = 1.0 / (self.k + rank)
            rrf_scores[doc_id] += rrf_score * (1 - alpha)  # Ponderar por alpha
            
            if doc_id not in doc_info:
                doc_info[doc_id] = {
                    "lexical_score": result.lexical_score,
                    "lexical_rank": rank,
                    "metadata": result.metadata,
                    "matched_terms": result.matched_terms,
                    "highlights": result.highlights
                }
        
        # Procesar resultados vectoriales
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result.id
            rrf_score = 1.0 / (self.k + rank)
            rrf_scores[doc_id] += rrf_score * alpha  # Ponderar por alpha
            
            if doc_id not in doc_info:
                doc_info[doc_id] = {
                    "vector_score": result.vector_score,
                    "vector_rank": rank,
                    "metadata": result.metadata
                }
            else:
                doc_info[doc_id]["vector_score"] = result.vector_score
                doc_info[doc_id]["vector_rank"] = rank
        
        # Crear resultados híbridos
        hybrid_results = []
        for doc_id, rrf_score in rrf_scores.items():
            info = doc_info[doc_id]
            
            # Crear explicación
            explanation = self._create_explanation(
                doc_id, 
                rrf_score, 
                info, 
                alpha
            )
            
            result = HybridSearchResult(
                id=doc_id,
                combined_score=rrf_score,
                lexical_score=info.get("lexical_score"),
                vector_score=info.get("vector_score"),
                lexical_rank=info.get("lexical_rank"),
                vector_rank=info.get("vector_rank"),
                metadata=info.get("metadata"),
                matched_terms=info.get("matched_terms"),
                highlights=info.get("highlights"),
                explanation=explanation
            )
            hybrid_results.append(result)
        
        # Ordenar por RRF score descendente
        hybrid_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Retornar top_k
        return hybrid_results[:top_k]
    
    def _create_explanation(
        self, 
        doc_id: str, 
        rrf_score: float, 
        info: Dict, 
        alpha: float
    ) -> Dict:
        """
        Crea explicación detallada del score.
        Crucial para auditoría médica.
        """
        explanation = {
            "fusion_method": "Reciprocal Rank Fusion (RRF)",
            "rrf_k_parameter": self.k,
            "combined_score": rrf_score,
            "alpha_weight": {
                "lexical": 1 - alpha,
                "vector": alpha
            },
            "components": {}
        }
        
        if "lexical_rank" in info:
            lex_contribution = (1.0 / (self.k + info["lexical_rank"])) * (1 - alpha)
            explanation["components"]["lexical"] = {
                "rank": info["lexical_rank"],
                "score": info.get("lexical_score"),
                "rrf_contribution": lex_contribution,
                "matched_terms": info.get("matched_terms", [])
            }
        
        if "vector_rank" in info:
            vec_contribution = (1.0 / (self.k + info["vector_rank"])) * alpha
            explanation["components"]["vector"] = {
                "rank": info["vector_rank"],
                "score": info.get("vector_score"),
                "rrf_contribution": vec_contribution
            }
        
        return explanation
```

### 7.3 Caso de Uso: Búsqueda Híbrida

```python
# usecases/hybrid_search_usecase.py
from typing import List, Optional
from ..core.ports.embedding_port import EmbeddingPort
from ..core.ports.vector_index_port import VectorIndexPort
from ..core.ports.lexical_index_port import LexicalIndexPort
from ..core.ports.metadata_store_port import MetadataStorePort
from ..core.schemas.search_query_schema import HybridQuery
from ..core.schemas.search_result_schema import HybridSearchResult
from ..modules.fusion.rrf_fusion import ReciprocalRankFusion

class HybridSearchUseCase:
    """
    Caso de uso para búsqueda híbrida.
    
    Orquesta:
    1. Generación de embedding del query
    2. Búsqueda vectorial (ANN)
    3. Búsqueda léxica (BM25)
    4. Fusión de resultados (RRF)
    5. Filtrado por metadatos
    6. Enriquecimiento con metadata completa
    """
    
    def __init__(
        self,
        embedder: EmbeddingPort,
        vector_index: VectorIndexPort,
        lexical_index: LexicalIndexPort,
        metadata_store: MetadataStorePort,
        fusion_strategy: Optional[str] = "rrf"
    ):
        self.embedder = embedder
        self.vector_index = vector_index
        self.lexical_index = lexical_index
        self.metadata_store = metadata_store
        
        # Inicializar fusión
        if fusion_strategy == "rrf":
            self.fusion = ReciprocalRankFusion(k=60)
        else:
            raise NotImplementedError(f"Fusion strategy '{fusion_strategy}' not implemented")
    
    def execute(self, query: HybridQuery) -> List[HybridSearchResult]:
        """
        Ejecuta búsqueda híbrida.
        """
        # 1. Buscar más resultados de los solicitados (para tener pool grande)
        k_retrieve = query.k * 5  # Recuperar 5x para mejor fusión
        
        # 2. Búsqueda vectorial
        query_vector = self.embedder.encode_query(query.text)
        vector_results = self.vector_index.search(
            query_vector=query_vector,
            k=k_retrieve,
            filter_criteria=query.filters
        )
        
        # 3. Búsqueda léxica
        from ..core.schemas.search_query_schema import LexicalQuery
        lex_query = query.lexical_query or LexicalQuery(text=query.text)
        lexical_results = self.lexical_index.search(
            query=lex_query,
            k=k_retrieve,
            filter_criteria=query.filters
        )
        
        # 4. Fusión
        hybrid_results = self.fusion.fuse(
            lexical_results=lexical_results,
            vector_results=vector_results,
            top_k=query.k,
            alpha=query.alpha
        )
        
        # 5. Enriquecer con metadatos completos (si no están ya)
        doc_ids = [r.id for r in hybrid_results]
        full_metadata = self.metadata_store.enrich_results(doc_ids)
        
        for result, metadata in zip(hybrid_results, full_metadata):
            if result.metadata is None:
                result.metadata = metadata.dict()
        
        return hybrid_results
```

**Nota**: No necesitas módulo `fusion/` separado. Elasticsearch hace la fusión híbrida nativamente.

---

## 🚫 SECCIONES ELIMINADAS (Reemplazadas por Elasticsearch)

Las siguientes secciones del plan v1.0 han sido **eliminadas** porque Elasticsearch las implementa nativamente:

### ❌ Fase 6: Operaciones de Conjuntos → ✅ Bool Queries de ES

**Antes** (código Python manual):
```python
# Intersección
positive = search("diabetes")
treatment = search("treatment")
intersect = set_ops.intersect([positive, treatment])  # AND manual

# Negación
all_chest = search("chest pain")
anxiety = search("anxiety")
filtered = set_ops.negate(all_chest, anxiety)  # NOT manual
```

**Ahora** (Query DSL de Elasticsearch):
```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"content": "diabetes"}},
        {"match": {"content": "treatment"}}
      ]
    }
  }
}

{
  "query": {
    "bool": {
      "must": [{"match": {"content": "chest pain"}}],
      "must_not": [{"match": {"content": "anxiety"}}]
    }
  }
}
```

**Equivalencias**:
- `intersect(A, B)` → `bool.must: [A, B]`
- `union(A, B)` → `bool.should: [A, B]`
- `negate(A, B)` → `bool.must: A, must_not: B`
- `filter(metadata)` → `bool.filter: [...]`

### ❌ Fase 7: Sistema de Metadatos → ✅ Object/Nested Fields de ES

**Antes** (store separado):
```python
# Guardar metadata
metadata_store.save(doc_id, {
  "specialty": "cardiology",
  "year": 2024,
  "evidence_level": 3
})

# Filtrar manualmente
results = search(query)
filtered = [r for r in results if r.metadata['specialty'] == 'cardiology']
```

**Ahora** (en el mismo documento de ES):
```json
{
  "id": "doc_123",
  "content": "Patient with chest pain...",
  "embedding": [0.1, 0.2, ...],
  "metadata": {
    "specialty": "cardiology",
    "year": 2024,
    "evidence_level": 3
  }
}
```

**Filtro nativo**:
```json
{
  "query": {...},
  "post_filter": {
    "bool": {
      "filter": [
        {"term": {"metadata.specialty": "cardiology"}},
        {"range": {"metadata.year": {"gte": 2020}}}
      ]
    }
  }
}
```

### ❌ Módulos fusion/rrf_fusion.py → ✅ ES Hybrid Search

Elasticsearch 8.4+ combina kNN + BM25 en una sola query (ver sección 7.1).

---

## 9. Fase 6: Optimizaciones Específicas para Dominio Médico

**Estas SÍ se mantienen** porque son específicas del dominio y ES no las tiene built-in.
    def intersect(
        self, 
        result_sets: List[List[SearchResult]],
        merge_strategy: str = "max_score"
    ) -> List[SearchResult]:
        """
        Intersección: documentos que aparecen en TODOS los conjuntos.
        
        Args:
            result_sets: Lista de conjuntos de resultados
            merge_strategy: Cómo combinar scores:
                - "max_score": Usar el score máximo
                - "min_score": Usar el score mínimo
                - "avg_score": Promedio de scores
                - "sum_score": Suma de scores
                - "product_score": Producto de scores (normalizado)
        """
        if not result_sets:
            return []
        
        if len(result_sets) == 1:
            return result_sets[0]
        
        # Agrupar por ID
        docs_by_id: Dict[str, List[SearchResult]] = defaultdict(list)
        
        for result_set in result_sets:
            for result in result_set:
                docs_by_id[result.id].append(result)
        
        # Solo mantener documentos que aparecen en TODOS los conjuntos
        num_sets = len(result_sets)
        intersected = []
        
        for doc_id, results in docs_by_id.items():
            if len(results) == num_sets:
                # Documento está en todos los conjuntos
                merged_result = self._merge_results(results, merge_strategy)
                intersected.append(merged_result)
        
        # Ordenar por score
        intersected.sort(key=lambda x: x.score, reverse=True)
        
        return intersected
    
    def union(
        self, 
        result_sets: List[List[SearchResult]],
        dedup_strategy: str = "keep_highest"
    ) -> List[SearchResult]:
        """
        Unión: documentos que aparecen en AL MENOS UN conjunto.
        
        Args:
            dedup_strategy:
                - "keep_highest": Mantener el score más alto
                - "keep_first": Mantener el primer resultado encontrado
                - "avg_score": Promedio si aparece en múltiples
                - "sum_score": Suma de scores
        """
        if not result_sets:
            return []
        
        # Agrupar por ID
        docs_by_id: Dict[str, List[SearchResult]] = defaultdict(list)
        
        for result_set in result_sets:
            for result in result_set:
                docs_by_id[result.id].append(result)
        
        # Mergear duplicados
        unified = []
        for doc_id, results in docs_by_id.items():
            if len(results) == 1:
                unified.append(results[0])
            else:
                merged = self._merge_results(results, dedup_strategy)
                unified.append(merged)
        
        # Ordenar por score
        unified.sort(key=lambda x: x.score, reverse=True)
        
        return unified
    
    def negate(
        self,         positive_results: List[SearchResult],
        negative_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Negación: P NOT N = Documentos en P pero NO en N.
        
        Example:
            positive: "diabetes"
            negative: "type 1 diabetes"
            result: documentos con "diabetes" pero sin "type 1"
        """
        # Crear set de IDs negativos
        negative_ids = {r.id for r in negative_results}
        
        # Filtrar resultados positivos
        filtered = [
            r for r in positive_results 
            if r.id not in negative_ids
        ]
        
        return filtered
    
    def filter_by_metadata(
        self, 
        results: List[SearchResult],
        filter_fn: Callable[[Dict], bool]
    ) -> List[SearchResult]:
        """
        Filtra resultados según función de metadatos.
        
        Example:
            filter_fn = lambda m: (
                m.get("specialty") == "cardiology" and 
                m.get("year", 0) >= 2020 and
                m.get("evidence_level", 0) >= 3
            )
        """
        filtered = []
        
        for result in results:
            metadata = result.metadata or {}
            if filter_fn(metadata):
                filtered.append(result)
        
        return filtered
    
    def filter_by_score_threshold(
        self, 
        results: List[SearchResult],
        min_score: float
    ) -> List[SearchResult]:
        """Filtra por score mínimo."""
        return [r for r in results if r.score >= min_score]
    
    def _merge_results(
        self, 
        results: List[SearchResult],
        strategy: str
    ) -> SearchResult:
        """
        Combina múltiples resultados del mismo documento.
        """
        if len(results) == 1:
            return results[0]
        
        # Base result (primer resultado)
        base = results[0]
        scores = [r.score for r in results]
        
        # Calcular score según estrategia
        if strategy == "max_score" or strategy == "keep_highest":
            merged_score = max(scores)
        elif strategy == "min_score":
            merged_score = min(scores)
        elif strategy == "avg_score":
            merged_score = sum(scores) / len(scores)
        elif strategy == "sum_score":
            merged_score = sum(scores)
        elif strategy == "product_score":
            import math
            # Producto geométrico normalizado
            product = 1.0
            for s in scores:
                product *= s
            merged_score = math.pow(product, 1.0 / len(scores))
        else:
            merged_score = max(scores)  # Default
        
        # Crear nuevo resultado
        merged = SearchResult(
            id=base.id,
            score=merged_score,
            metadata=base.metadata
        )
        
        return merged
```

### 8.2 Ejemplo de Uso: Query Compleja

```python
# Ejemplo de query compleja
def complex_medical_query_example(search_usecase):
    """
    Query: "síntomas de infarto" AND "diagnóstico" 
           NOT "infarto antiguo"
           WHERE specialty='cardiology' AND year >= 2020
    """
    from ...core.schemas.search_query_schema import HybridQuery
    from ...modules.set_ops.set_operations import SetOperations
    
    set_ops = SetOperations()
    
    # 1. Buscar "síntomas de infarto"
    query1 = HybridQuery(text="síntomas de infarto", k=50)
    results1 = search_usecase.execute(query1)
    
    # 2. Buscar "diagnóstico"
    query2 = HybridQuery(text="diagnóstico", k=50)
    results2 = search_usecase.execute(query2)
    
    # 3. Buscar "infarto antiguo" (para negar)
    query3 = HybridQuery(text="infarto antiguo", k=50)
    results3 = search_usecase.execute(query3)
    
    # 4. Intersección de 1 y 2
    intersected = set_ops.intersect([results1, results2])
    
    # 5. Negar 3
    negated = set_ops.negate(intersected, results3)
    
    # 6. Filtrar por metadatos
    filtered = set_ops.filter_by_metadata(
        negated,
        lambda m: (
            m.get("specialty") == "cardiology" and
            m.get("year", 0) >= 2020
        )
    )
    
    # 7. Filtrar por score mínimo
    final_results = set_ops.filter_by_score_threshold(filtered, min_score=0.5)
    
    return final_results
```

---

## 9. Fase 7: Sistema de Metadatos

### 9.1 Schemas de Metadatos

```python
# core/schemas/metadata_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MedicalSpecialty(str, Enum):
    """Especialidades médicas (subset común)."""
    CARDIOLOGY = "cardiology"
    NEUROLOGY = "neurology"
    ONCOLOGY = "oncology"
    PEDIATRICS = "pediatrics"
    INTERNAL_MEDICINE = "internal_medicine"
    EMERGENCY = "emergency"
    SURGERY = "surgery"
    PSYCHIATRY = "psychiatry"
    RADIOLOGY = "radiology"
    OTHER = "other"


class EvidenceLevel(int, Enum):
    """Niveles de evidencia médica."""
    LEVEL_1 = 1  # Systematic reviews, meta-analyses
    LEVEL_2 = 2  # RCTs
    LEVEL_3 = 3  # Cohort studies
    LEVEL_4 = 4  # Case-control studies
    LEVEL_5 = 5  # Case series, expert opinion


class DocumentMetadata(BaseModel):
    """Metadatos completos de documento médico."""
    
    # Identificación
    doc_id: str
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    source: Optional[str] = None  # PubMed, UpToDate, journal, etc.
    
    # Clasificación médica
    specialty: Optional[MedicalSpecialty] = None
    sub_specialty: Optional[str] = None
    
    # Códigos médicos estándar
    icd10_codes: Optional[List[str]] = Field(
        default=None,
        description="Códigos ICD-10 de diagnósticos mencionados"
    )
    
    snomed_codes: Optional[List[str]] = Field(
        default=None,
        description="Códigos SNOMED CT"
    )
    
    mesh_terms: Optional[List[str]] = Field(
        default=None,
        description="Medical Subject Headings (MeSH)"
    )
    
    # Calidad y evidencia
    evidence_level: Optional[EvidenceLevel] = None
    peer_reviewed: Optional[bool] = None
    
    # Temporal
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    year: Optional[int] = None
    
    # Idioma y ubicación
    language: str = Field(default="en")
    country: Optional[str] = None
    
    # Métricas
    citation_count: Optional[int] = None
    impact_factor: Optional[float] = None
    
    # URLs y acceso
    doi: Optional[str] = None
    pmid: Optional[str] = None  # PubMed ID
    url: Optional[str] = None
    
    # Contenido
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    
    # Custom fields
    custom_fields: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class ChunkMetadata(BaseModel):
    """Metadatos específicos de chunks."""
    
    chunk_id: str
    document_id: str
    
    # Posición
    chunk_index: int
    total_chunks: int
    
    # Contenido
    section_type: Optional[str] = None
    char_start: int
    char_end: int
    token_count: int
    
    # Heredados del documento
    doc_specialty: Optional[str] = None
    doc_year: Optional[int] = None
    doc_source: Optional[str] = None
    
    # Entidades mencionadas en el chunk
    mentioned_conditions: Optional[List[str]] = None
    mentioned_medications: Optional[List[str]] = None
    mentioned_procedures: Optional[List[str]] = None
    
    # Calidad del chunk
    quality_score: Optional[float] = None
    
    # Timestamps
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
```

### 9.2 Adaptador de Metadata Store (Elasticsearch)

```python
# adapters/stores/elasticsearch_metadata_adapter.py
from typing import List, Optional, Dict, Any
from elasticsearch import Elasticsearch
from datetime import datetime

from ...core.ports.metadata_store_port import MetadataStorePort
from ...core.schemas.metadata_schema import DocumentMetadata, ChunkMetadata

class ElasticsearchMetadataAdapter(MetadataStorePort):
    """
    Adaptador para almacenar metadatos en Elasticsearch.
    
    Ventajas:
    - Búsqueda rápida de metadatos
    - Queries complejas (filtros, agregaciones)
    - Escalable
    - Soporta schema flexible
    """
    
    def __init__(
        self,
        es_client: Elasticsearch,
        doc_index: str = "sri_dx_documents",
        chunk_index: str = "sri_dx_chunks"
    ):
        self.es = es_client
        self.doc_index = doc_index
        self.chunk_index = chunk_index
        
        # Crear índices si no existen
        self._ensure_indices()
    
    def _ensure_indices(self):
        """Crea índices con mappings apropiados."""
        
        # Mapping para documentos
        doc_mapping = {
            "mappings": {
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "specialty": {"type": "keyword"},
                    "icd10_codes": {"type": "keyword"},
                    "snomed_codes": {"type": "keyword"},
                    "mesh_terms": {"type": "keyword"},
                    "evidence_level": {"type": "integer"},
                    "publication_date": {"type": "date"},
                    "year": {"type": "integer"},
                    "language": {"type": "keyword"},
                    "citation_count": {"type": "integer"},
                    "abstract": {"type": "text"},
                    "keywords": {"type": "keyword"}
                }
            }
        }
        
        if not self.es.indices.exists(index=self.doc_index):
            self.es.indices.create(index=self.doc_index, body=doc_mapping)
        
        # Mapping para chunks
        chunk_mapping = {
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "section_type": {"type": "keyword"},
                    "doc_specialty": {"type": "keyword"},
                    "doc_year": {"type": "integer"},
                    "quality_score": {"type": "float"},
                    "mentioned_conditions": {"type": "keyword"},
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        if not self.es.indices.exists(index=self.chunk_index):
            self.es.indices.create(index=self.chunk_index, body=chunk_mapping)
    
    def store_document_metadata(
        self, 
        doc_id: str, 
        metadata: DocumentMetadata
    ) -> None:
        """Almacena metadatos de documento."""
        body = metadata.dict(exclude_none=True)
        
        self.es.index(
            index=self.doc_index,
            id=doc_id,
            document=body
        )
    
    def store_chunk_metadata(
        self, 
        chunk_id: str, 
        metadata: ChunkMetadata
    ) -> None:
        """Almacena metadatos de chunk."""
        body = metadata.dict(exclude_none=True)
        
        self.es.index(
            index=self.chunk_index,
            id=chunk_id,
            document=body
        )
    
    def get_document_metadata(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Recupera metadatos de documento."""
        try:
            result = self.es.get(index=self.doc_index, id=doc_id)
            return DocumentMetadata(**result["_source"])
        except:
            return None
    
    def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Recupera metadatos de chunk."""
        try:
            result = self.es.get(index=self.chunk_index, id=chunk_id)
            return ChunkMetadata(**result["_source"])
        except:
            return None
    
    def query_by_metadata(
        self, 
        filters: Dict[str, Any]
    ) -> List[str]:
        """
        Consulta IDs que cumplen filtros.
        
        Example filters:
            {
                "specialty": "cardiology",
                "year": {"$gte": 2020},
                "evidence_level": {"$lte": 2}
            }
        """
        # Convertir filtros a Elasticsearch Query DSL
        es_query = self._build_es_query(filters)
        
        result = self.es.search(
            index=self.doc_index,
            query=es_query,
            _source=False,  # Solo IDs
            size=10000  # Ajustar según necesidad
        )
        
        return [hit["_id"] for hit in result["hits"]["hits"]]
    
    def enrich_results(
        self, 
        doc_ids: List[str]
    ) -> List[DocumentMetadata]:
        """
        Enriquece lista de IDs con metadatos.
        Usa multi-get para eficiencia.
        """
        if not doc_ids:
            return []
        
        # Multi-get request
        mget_body = {"ids": doc_ids}
        result = self.es.mget(index=self.doc_index, body=mget_body)
        
        metadata_list = []
        for doc in result["docs"]:
            if doc["found"]:
                metadata_list.append(DocumentMetadata(**doc["_source"]))
            else:
                # Documento no encontrado, placeholder
                metadata_list.append(DocumentMetadata(doc_id=doc["_id"]))
        
        return metadata_list
    
    def _build_es_query(self, filters: Dict[str, Any]) -> Dict:
        """
        Convierte filtros simples a Elasticsearch Query DSL.
        """
        must_clauses = []
        
        for key, value in filters.items():
            if isinstance(value, dict):
                # Operadores MongoDB-style
                for op, op_value in value.items():
                    if op == "$gte":
                        must_clauses.append({"range": {key: {"gte": op_value}}})
                    elif op == "$lte":
                        must_clauses.append({"range": {key: {"lte": op_value}}})
                    elif op == "$gt":
                        must_clauses.append({"range": {key: {"gt": op_value}}})
                    elif op == "$lt":
                        must_clauses.append({"range": {key: {"lt": op_value}}})
                    elif op == "$in":
                        must_clauses.append({"terms": {key: op_value}})
            else:
                # Igualdad simple
                must_clauses.append({"term": {key: value}})
        
        return {
            "bool": {
                "must": must_clauses
            }
        }
```

---

## 9. Fase 6: Optimizaciones Específicas para Dominio Médico

### 9.1 Medical Entity Recognition (NER)

```python
# modules/ner/medical_ner.py
from typing import List, Dict, Set
import re

class MedicalEntityRecognizer:
    """
    Reconocedor de entidades médicas.
    
    Identifica:
    - Códigos ICD-10
    - Términos SNOMED
    - Nombres de medicamentos
    - Procedimientos
    - Síntomas
    """
    
    # Regex para códigos ICD-10 (simplificado)
    ICD10_PATTERN = r'\b[A-Z]\d{2}(?:\.\d{1,4})?\b'
    
    # Lista de medicamentos comunes (expandir según necesidad)
    COMMON_MEDICATIONS = {
        "aspirin", "ibuprofen", "metformin", "lisinopril",
        "atorvastatin", "amlodipine", "metoprolol", "omeprazole"
        # ... agregar más
    }
    
    # Síntomas comunes
    COMMON_SYMPTOMS = {
        "pain", "chest pain", "headache", "fever", "cough",
        "shortness of breath", "fatigue", "nausea", "dizziness"
        # ... agregar más
    }
    
    def __init__(self):
        # En producción, usar modelo NER real como scispaCy o BioBERT-NER
        pass
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extrae entidades médicas del texto.
        
        Returns:
            Dict con: icd10_codes, medications, symptoms, procedures
        """
        entities = {
            "icd10_codes": self._extract_icd10(text),
            "medications": self._extract_medications(text),
            "symptoms": self._extract_symptoms(text),
            "procedures": []  # TODO: implementar
        }
        
        return entities
    
    def _extract_icd10(self, text: str) -> List[str]:
        """Extrae códigos ICD-10."""
        matches = re.findall(self.ICD10_PATTERN, text)
        return list(set(matches))  # Deduplicar
    
    def _extract_medications(self, text: str) -> List[str]:
        """Extrae nombres de medicamentos mencionados."""
        text_lower = text.lower()
        found = []
        
        for med in self.COMMON_MEDICATIONS:
            if med in text_lower:
                found.append(med)
        
        return found
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extrae síntomas mencionados."""
        text_lower = text.lower()
        found = []
        
        for symptom in self.COMMON_SYMPTOMS:
            if symptom in text_lower:
                found.append(symptom)
        
        return found
```

### 10.2 Query Expansion para Términos Médicos

```python
# modules/query_expansion/medical_query_expander.py
from typing import List, Set, Dict

class MedicalQueryExpander:
    """
    Expande queries con sinónimos médicos y términos relacionados.
    
    Example:
        "heart attack" → ["heart attack", "myocardial infarction", "MI", "AMI"]
    """
    
    # Diccionario de sinónimos médicos (simplificado)
    MEDICAL_SYNONYMS = {
        "heart attack": ["myocardial infarction", "MI", "AMI", "cardiac infarction"],
        "stroke": ["cerebrovascular accident", "CVA", "brain attack"],
        "hypertension": ["high blood pressure", "HTN", "elevated BP"],
        "diabetes": ["diabetes mellitus", "DM", "hyperglycemia"],
        "cancer": ["malignancy", "neoplasm", "tumor"],
        # ... expandir según necesidad
    }
    
    # Abreviaciones comunes
    ABBREVIATIONS = {
        "MI": "myocardial infarction",
        "CVA": "cerebrovascular accident",
        "HTN": "hypertension",
        "DM": "diabetes mellitus",
        "CHF": "congestive heart failure",
        # ... expandir
    }
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expande query con sinónimos y términos relacionados.
        
        Returns:
            Lista de variantes del query
        """
        query_lower = query.lower()
        variants = [query]  # Incluir original
        
        # Buscar sinónimos
        for term, synonyms in self.MEDICAL_SYNONYMS.items():
            if term in query_lower:
                for synonym in synonyms:
                    variant = query_lower.replace(term, synonym)
                    if variant != query_lower:
                        variants.append(variant)
        
        # Expandir abreviaciones
        for abbr, full_form in self.ABBREVIATIONS.items():
            if abbr.lower() in query_lower.split():
                variant = query_lower.replace(abbr.lower(), full_form)
                variants.append(variant)
        
        return list(set(variants))  # Deduplicar
    
    def get_related_terms(self, term: str) -> List[str]:
        """
        Retorna términos médicos relacionados.
        """
        term_lower = term.lower()
        
        # Buscar en sinónimos
        if term_lower in self.MEDICAL_SYNONYMS:
            return self.MEDICAL_SYNONYMS[term_lower]
        
        # Buscar si es sinónimo de algo
        for main_term, synonyms in self.MEDICAL_SYNONYMS.items():
            if term_lower in [s.lower() for s in synonyms]:
                return [main_term] + synonyms
        
        return []
```

### 10.3 Re-Ranker Médico

```python
# modules/ranking/medical_reranker.py
from typing import List
from ...core.schemas.search_result_schema import HybridSearchResult

class MedicalReRanker:
    """
    Re-ranker especializado en contenido médico.
    
    Ajusta scores basado en:
    - Nivel de evidencia
    - Fecha de publicación (más reciente = mejor)
    - Especialidad relevante
    - Calidad de la fuente
    """
    
    # Pesos para re-ranking
    EVIDENCE_WEIGHTS = {
        1: 1.3,  # Máxima evidencia
        2: 1.2,
        3: 1.1,
        4: 1.0,
        5: 0.9   # Evidencia más baja
    }
    
    SOURCE_WEIGHTS = {
        "cochrane": 1.3,
        "pubmed": 1.2,
        "uptodate": 1.2,
        "nejm": 1.25,
        "lancet": 1.25,
        "jama": 1.2,
        "bmj": 1.2,
        "other": 1.0
    }
    
    def rerank(
        self, 
        results: List[HybridSearchResult],
        specialty_preference: str = None,
        recency_weight: float = 0.1
    ) -> List[HybridSearchResult]:
        """
        Re-rankea resultados según criterios médicos.
        
        Args:
            results: Resultados a re-rankear
            specialty_preference: Especialidad preferida (bonus)
            recency_weight: Peso de la recencia (0-1)
        """
        import datetime
        
        for result in results:
            metadata = result.metadata or {}
            
            # Score base
            adjusted_score = result.combined_score
            
            # Bonus por nivel de evidencia
            evidence_level = metadata.get("evidence_level")
            if evidence_level in self.EVIDENCE_WEIGHTS:
                adjusted_score *= self.EVIDENCE_WEIGHTS[evidence_level]
            
            # Bonus por fuente de calidad
            source = metadata.get("source", "other").lower()
            source_key = next(
                (k for k in self.SOURCE_WEIGHTS.keys() if k in source),
                "other"
            )
            adjusted_score *= self.SOURCE_WEIGHTS[source_key]
            
            # Bonus por recencia
            year = metadata.get("year")
            if year:
                current_year = datetime.datetime.now().year
                years_old = current_year - year
                recency_factor = max(0, 1 - (years_old * recency_weight / 10))
                adjusted_score *= (1 + recency_factor * recency_weight)
            
            # Bonus por especialidad
            if specialty_preference:
                doc_specialty = metadata.get("specialty", "").lower()
                if specialty_preference.lower() in doc_specialty:
                    adjusted_score *= 1.15
            
            # Actualizar score
            result.combined_score = adjusted_score
        
        # Re-ordenar
        results.sort(key=lambda x: x.combined_score, reverse=True)
        
        return results
```

---

## 10. Cronograma de Implementación

### Sprint 1 (Semana 1-2): Fundamentos
- ✅ Definir todos los puertos (interfaces)
- ✅ Crear schemas completos (Pydantic)
- ✅ Implementar MedicalSectionChunker
- ✅ Tests unitarios de chunking

### Sprint 2 (Semana 3-4): Embeddings e Indexación
- ✅ Implementar CachedBiomedicalEmbedder
- ✅ Implementar HNSWAdapter
- ✅ Implementar ElasticsearchLexicalAdapter
- ✅ Pipeline de indexación end-to-end
- ✅ Tests de integración

### Sprint 3 (Semana 5-6): Búsqueda con Elasticsearch
- ✅ Implementar ElasticsearchAdapter completo
- ✅ Búsqueda léxica (BM25)
- ✅ Búsqueda vectorial (kNN)
- ✅ Búsqueda híbrida nativa
- ✅ Tests de búsqueda
- ✅ Benchmarks de rendimiento

### Sprint 4 (Semana 7): Queries Complejas con ES Query DSL
- ✅ Implementar QueryBuilder para ES
- ✅ Operaciones booleanas (AND, OR, NOT) nativas
- ✅ Filtros por metadata
- ✅ Tests de queries complejas

### Sprint 5 (Semana 8): Metadatos y NER
- ✅ Integrar metadatos médicos en ES
- ✅ Implementar MedicalEntityRecognizer (básico)
- ✅ Integrar NER en pipeline de indexación
- ✅ Mapping de ES para campos médicos específicos

### Sprint 6 (Semana 9-10): Optimizaciones Médicas
- ✅ Implementar MedicalQueryExpander
- ✅ Implementar MedicalReRanker
- ✅ Tuning de hiperparámetros
- ✅ Evaluación de calidad (NDCG, MAP, Recall)

### Sprint 7 (Semana 11): Integración UI
- ✅ Conectar con Streamlit UI
- ✅ Visualizaciones de explicabilidad
- ✅ Filtros interactivos

### Sprint 8 (Semana 12): Optimización y Deployment
- ✅ Profiling y optimización
- ✅ Caché inteligente
- ✅ Docker deployment completo
- ✅ Documentación final

---

## 11. Métricas de Calidad

### 11.1 Métricas de Recuperación

```python
# evaluation/metrics.py
import numpy as np
from typing import List, Set

class RetrievalMetrics:
    """Métricas estándar de Information Retrieval."""
    
    @staticmethod
    def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Precision@K: Fracción de resultados relevantes en top-K.
        """
        top_k = retrieved[:k]
        relevant_in_top_k = len([doc for doc in top_k if doc in relevant])
        return relevant_in_top_k / k if k > 0 else 0.0
    
    @staticmethod
    def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Recall@K: Fracción de documentos relevantes encontrados en top-K.
        """
        top_k = retrieved[:k]
        relevant_in_top_k = len([doc for doc in top_k if doc in relevant])
        return relevant_in_top_k / len(relevant) if relevant else 0.0
    
    @staticmethod
    def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
        """
        Average Precision (AP): Precisión promedio en cada posición relevante.
        """
        if not relevant:
            return 0.0
        
        precisions = []
        num_relevant = 0
        
        for i, doc in enumerate(retrieved, start=1):
            if doc in relevant:
                num_relevant += 1
                precision_at_i = num_relevant / i
                precisions.append(precision_at_i)
        
        return sum(precisions) / len(relevant) if relevant else 0.0
    
    @staticmethod
    def mean_average_precision(
        all_retrieved: List[List[str]], 
        all_relevant: List[Set[str]]
    ) -> float:
        """
        Mean Average Precision (MAP): AP promedio sobre múltiples queries.
        """
        aps = [
            RetrievalMetrics.average_precision(ret, rel)
            for ret, rel in zip(all_retrieved, all_relevant)
        ]
        return np.mean(aps)
    
    @staticmethod
    def ndcg_at_k(
        retrieved: List[str], 
        relevance_scores: dict, 
        k: int
    ) -> float:
        """
        Normalized Discounted Cumulative Gain@K.
        
        Args:
            retrieved: Lista de IDs recuperados (en orden)
            relevance_scores: Dict {doc_id: relevance} (0-N)
            k: Top-K
        """
        def dcg(scores: List[float]) -> float:
            """Discounted Cumulative Gain."""
            return sum(
                (2**score - 1) / np.log2(i + 2)
                for i, score in enumerate(scores)
            )
        
        # DCG de los resultados
        retrieved_scores = [
            relevance_scores.get(doc_id, 0) 
            for doc_id in retrieved[:k]
        ]
        dcg_value = dcg(retrieved_scores)
        
        # IDCG (ideal: mejor ordenamiento posible)
        ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
        idcg_value = dcg(ideal_scores)
        
        # NDCG
        return dcg_value / idcg_value if idcg_value > 0 else 0.0
```

### 12.2 Métricas Objetivo

Para SRI-DX (diagnósticos médicos), las metas son:

| Métrica | Target | Justificación |
|---------|--------|---------------|
| **Recall@10** | ≥ 0.85 | Crucial no perder diagnósticos relevantes |
| **Precision@10** | ≥ 0.70 | Minimizar falsos positivos |
| **MAP** | ≥ 0.75 | Calidad global de ranking |
| **NDCG@10** | ≥ 0.80 | Orden correcto de resultados |
| **MRR** | ≥ 0.85 | Primer resultado relevante en top 3 |
| **Latencia** | < 200ms | Búsqueda responsiva |
| **Throughput** | > 100 qps | Escalabilidad |

---

## 12. Consideraciones de Producción

### 12.1 Escalabilidad con Elasticsearch

- **Sharding de Elasticsearch**: Distribuir carga
- **FAISS GPU**: Para datasets > 10M vectores
- **Caché distribuida**: Redis para embeddings frecuentes
- **Load balancing**: Múltiples réplicas del servicio
- **Async processing**: Para indexación batch

### 13.2 Monitoreo

```python
# monitoring/metrics_tracker.py
from prometheus_client import Counter, Histogram, Gauge

class MetricsTracker:
    """Métricas para monitoreo en producción."""
    
    # Contadores
    search_requests = Counter('sri_dx_search_requests_total', 'Total search requests')
    search_errors = Counter('sri_dx_search_errors_total', 'Total search errors')
    
    # Histogramas
    search_latency = Histogram(
        'sri_dx_search_latency_seconds', 
        'Search latency',
        buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
    )
    
    embedding_latency = Histogram(
        'sri_dx_embedding_latency_seconds',
        'Embedding generation latency'
    )
    
    # Gauges
    index_size = Gauge('sri_dx_index_size_vectors', 'Number of indexed vectors')
    cache_hit_rate = Gauge('sri_dx_cache_hit_rate', 'Embedding cache hit rate')
```

### 13.3 Seguridad y Privacidad

- **HIPAA Compliance**: Encriptación en reposo y tránsito
- **Anonymization**: Eliminar PHI de documentos indexados
- **Access Control**: Autenticación y autorización robustas
- **Audit logs**: Trazabilidad completa de búsquedas
- **Data retention**: Políticas claras de retención

---

## 13. Conclusión

### 13.1 Resumen Ejecutivo

**🎯 Decisión Principal**: Elasticsearch como núcleo central del sistema SRI-DX.

Este plan de implementación (v2.0) proporciona:

✅ **Arquitectura Simplificada**: Un solo sistema (Elasticsearch) vs múltiples backends  
✅ **Genericidad**: Interfaces abstractas permiten cambiar tecnologías si es necesario  
✅ **Calidad Médica**: Optimizaciones específicas para diagnósticos (BioBERT, chunking médico)  
✅ **Rendimiento Superior**: <100ms latencia con búsqueda híbrida nativa  
✅ **Menos Código**: -60% líneas de código vs arquitectura multi-backend  
✅ **Trazabilidad Built-in**: Explain API de ES proporciona scoring transparente  
✅ **Producción-ready**: Escalabilidad, monitoreo y HA incluidos en ES  

### 13.2 Comparativa Final

| Característica | Con ES Central | Multi-Backend |
|----------------|----------------|---------------|
| **Sistemas a mantener** | 1 (Elasticsearch) | 3+ (ES + HNSW + Redis) |
| **Latencia p95** | <100ms | 150-300ms |
| **Líneas de código** | ~2,000 | ~5,000+ |
| **Complejidad deployment** | Docker Compose (2 servicios) | Docker Compose (5+ servicios) |
| **Búsqueda híbrida** | Nativa (1 request) | Manual (2+ requests + fusión Python) |
| **Filtros metadata** | Query DSL nativo | Post-procesamiento |
| **Escalabilidad** | Sharding automático | Manual por servicio |
| **Costo infraestructura** | Bajo (1 cluster) | Alto (múltiples) |
| **Debugging** | Explain API | Logging múltiple |

### 13.3 Migración desde tu `main.py`

Tu código actual ya usa Elasticsearch con kNN:

```python
# Tu main.py actual (simplificado)
es = await conectar_elastic()
await crear_indices(es)
await insertar_documentos(es, docs_con_embeddings)
results = await busqueda_kNN(es, consulta, indice)
```

**Migración a la arquitectura propuesta**:

```python
# Con la arquitectura del plan
from sri_dx.adapters.elasticsearch.es_adapter import ElasticsearchAdapter
from sri_dx.modules.embedding.biomedical_embedder import BiomedicalEmbedder
from sri_dx.usecases.search_usecase import SearchUseCase

# Setup
es_adapter = ElasticsearchAdapter(hosts=["http://localhost:9200"])
embedder = BiomedicalEmbedder(model_name="cambridgeltl/BioRedditBERT-uncased")
search_usecase = SearchUseCase(es_adapter=es_adapter, embedder=embedder)

# Indexar
await search_usecase.index_documents(documents)

# Buscar (híbrido automático)
results = await search_usecase.search(
    query="chest pain shortness of breath",
    search_type="hybrid",  # o "lexical", "semantic"
    k=10
)
```

**Beneficios**:
- ✅ Mantienes Elasticsearch (ya lo conoces)
- ✅ Código más limpio y testeable
- ✅ Fácil cambiar modelo de embeddings
- ✅ Búsqueda híbrida sin código manual de fusión

### 13.4 Próximos Pasos Concretos

**Semana 1-2** (Sprint 1):
1. ✅ Crear schemas Pydantic (chunk, embedding, query, result)
2. ✅ Implementar `MedicalSectionChunker`
3. ✅ Implementar `BiomedicalEmbedder` con caché
4. ✅ Tests unitarios

**Semana 3-4** (Sprint 2):
1. ✅ Implementar `ElasticsearchAdapter` completo
2. ✅ Configurar mappings para dense_vector
3. ✅ Pipeline indexación: docs → chunks → embeddings → ES
4. ✅ Tests de integración con ES

**Semana 5** (Sprint 3):
1. ✅ Implementar `SearchUseCase`
2. ✅ Búsqueda híbrida con parámetro alpha configurable
3. ✅ Filtros por metadata médica
4. ✅ Benchmarks de latencia y recall

**Semana 6** (Sprint 4):
1. ✅ Integrar con tu UI Streamlit existente
2. ✅ Query expansion médica
3. ✅ Re-ranking opcional
4. ✅ Evaluación de calidad (NDCG, MAP)

### 13.5 Validación con Stakeholders

Antes de implementar, validar:

1. **Tipos de queries médicas más comunes**
   - ¿Búsqueda por síntomas? → Semántica
   - ¿Búsqueda de códigos (ICD-10)? → Léxica
   - ¿Combinación? → Híbrida

2. **Metadatos críticos**
   - Especialidad médica
   - Nivel de evidencia
   - Año de publicación
   - Tipo de estudio

3. **Métricas de éxito**
   - Recall@10 mínimo aceptable
   - Latencia máxima tolerable
   - Throughput esperado

### 13.6 Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| ES insuficiente para escala | Baja | Alto | Benchmarks tempranos; fallback FAISS si >10M docs |
| Embeddings muy lentos | Media | Medio | Caché Redis; batch processing |
| Calidad médica baja | Media | Alto | Dataset evaluación médica; fine-tuning BioBERT |
| Lock-in a ES | Alta | Bajo | Puerto abstrae ES; migrar si necesario |

---

**Documento vivo**: Este plan se actualizará según avance el proyecto y feedback del equipo.

**Versión**: 2.0 (Actualizada 2026-03-02)  
**Contacto**: Para dudas técnicas, consultar documentación en `doc/dev/` o abrir issue en el repositorio.
