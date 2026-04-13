# Cross-Encoder Reranking

## Descripción

El cross-encoder es un componente de reranking que mejora la precisión de los resultados de búsqueda híbrida evaluando directamente la relevancia entre la query y cada documento candidato.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Búsqueda Híbrida                         │
│  (Léxica BM25 + Semántica kNN) → Top-100 candidatos        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Cross-Encoder Reranking                      │
│  Evalúa cada par (query, documento) → Top-10 finales       │
└─────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. Schemas (`modules/ranking/schemas/`)

- **`cross_encoder_config.py`**: Configuración del modelo
  - `model_name`: Modelo de HuggingFace
  - `device`: cpu/cuda/mps
  - `batch_size`: Tamaño de lote para inferencia
  - `top_k`: Número de resultados a retornar
  - `score_threshold`: Filtro opcional de score mínimo

- **`rerank_schemas.py`**: Estructuras de datos
  - `RerankRequest`: Input con query y resultados híbridos
  - `RerankResponse`: Output con resultados rerankeados
  - `RerankResult`: Resultado individual con scores
  - Excepciones: `RerankingError`, `EmptyResultsError`, `MissingContentError`

### 2. Port (`core/ports/search/cross_encoder_port.py`)

Interface abstracta que define el contrato:
- `rerank(request: RerankRequest) -> RerankResponse`
- `is_available() -> bool`

### 3. Adapter (`adapters/embeddings/sentences_transformers_cross_encoder_adapter.py`)

Implementación usando `sentence-transformers`:
- Extrae contenido de metadata de `HybridSearchResult`
- Crea pares (query, contenido)
- Ejecuta inferencia del cross-encoder
- Ordena por score y aplica top_k

## Uso

### Configuración

```python
from sri_dx.modules.ranking.schemas import CrossEncoderConfig
from sri_dx.adapters.embeddings import SentenceTransformersCrossEncoderAdapter

config = CrossEncoderConfig(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
    device="cuda",  # o "cpu"
    batch_size=32,
    top_k=10,
    score_threshold=0.5,  # opcional
)

cross_encoder = SentenceTransformersCrossEncoderAdapter(config)
```

### Integración con Búsqueda Híbrida

```python
from sri_dx.modules.ranking.schemas import RerankRequest
from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase

# 1. Búsqueda híbrida (top-100 candidatos)
hybrid_results = hybrid_search.search(
    query="tratamiento diabetes tipo 2",
    k=100
)

# 2. Reranking (top-10 finales)
rerank_request = RerankRequest(
    query="tratamiento diabetes tipo 2",
    results=hybrid_results,
    top_k=10,
    content_field="content"  # campo en metadata con el texto
)

rerank_response = cross_encoder.rerank(rerank_request)

# 3. Usar resultados
for result in rerank_response.ranked_results:
    print(f"{result.doc_id}: {result.rerank_score:.3f}")
```

## Modelos Recomendados

### Inglés
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (rápido, 80M params)
- `cross-encoder/ms-marco-MiniLM-L-12-v2` (más preciso, 33M params)
- `cross-encoder/ms-marco-electra-base` (muy preciso, 110M params)

### Multilingüe
- `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (incluye español)
- `cross-encoder/msmarco-MiniLM-L6-en-de-v1` (inglés-alemán)

### Dominio Médico
Actualmente no hay cross-encoders específicos para medicina en español.
Alternativas:
1. Fine-tuning de modelo multilingüe sobre datos médicos
2. Usar modelo general en inglés si documentos están en inglés
3. Traducir a inglés, rerankear, y mapear resultados

## Consideraciones de Performance

### Velocidad
- Búsqueda híbrida: ~50-100ms (100 candidatos)
- Cross-encoder: ~200-500ms (100 pares) en CPU
- **Recomendación**: Usar GPU si es posible

### Estrategia de Candidatos
```
Top-K Candidatos    Cross-Encoder Tiempo    Precisión
     20                   ~50ms              Media
     50                  ~150ms              Buena
    100                  ~300ms              Muy buena
    500                 ~1500ms              Excelente
```

**Recomendación**: 100 candidatos para balance entre velocidad y precisión.

## Estructura de Archivos

```
src/sri_dx/
├── core/ports/search/
│   └── cross_encoder_port.py          # Interface abstracta
├── adapters/embeddings/
│   └── sentences_transformers_cross_encoder_adapter.py  # Implementación
└── modules/ranking/
    ├── schemas/
    │   ├── __init__.py
    │   ├── cross_encoder_config.py    # Configuración
    │   └── rerank_schemas.py          # Estructuras de datos
    ├── __init__.py                     # Exports del módulo
    ├── fusion.py                       # RRF, weighted sum, etc.
    ├── reranking_example.py           # Ejemplo de uso
    └── README.md                       # Esta documentación
```

## Testing

Ver ejemplo completo en `reranking_example.py`:
```bash
python -m sri_dx.modules.ranking.reranking_example
```

## Próximos Pasos

1. **Integración en CLI**: Añadir flag `--rerank` en `search_cli.py`
2. **Caché**: Implementar caché de scores para queries frecuentes
3. **Fine-tuning**: Entrenar modelo específico para dominio médico español
4. **Evaluación**: Medir mejora en precisión (P@10, MRR, NDCG)
5. **Optimización**: Batch processing y async para múltiples queries

## Referencias

- [MS MARCO Cross-Encoders](https://github.com/microsoft/MS-MARCO-Cross-Encoders)
- [Sentence-Transformers Documentation](https://www.sbert.net/docs/pretrained_cross-encoders.html)
- Paper: "Passage Re-ranking with BERT" (Nogueira & Cho, 2019)
