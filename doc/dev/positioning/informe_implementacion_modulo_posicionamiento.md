# Informe de implementacion del modulo de posicionamiento clinico

Fecha: 2026-05-06

## 1. Resumen

Se implemento una primera version funcional del modulo de posicionamiento clinico para SRI-DX.

El objetivo fue convertir la salida tecnica del recuperador hibrido y del cross-encoder en una lista final de condiciones clinicas posicionadas, explicables, diversas y trazables.

El nuevo flujo queda asi:

```text
SearchHybridUseCase
        ↓
TwoStageRetrievalPipeline.search()
        ↓
NER on-demand
        ↓
ClinicalPositioningService
        ↓
PositionedClinicalResult[]
        ↓
CLI / API / Streamlit
```

La implementacion se hizo sin romper el comportamiento existente de:

- `search()`
- `search_diseases()`
- `DiseaseAggregator`
- busqueda hibrida actual
- reranking con cross-encoder actual

## 2. Archivos principales creados

Se creo el paquete:

```text
src/sri_dx/modules/positioning/
```

Con estos archivos:

```text
__init__.py
adapters.py
authority.py
config.py
evidence.py
explanations.py
freshness.py
grouping.py
mmr.py
models.py
scoring.py
service.py
symptoms.py
```

Tambien se agregaron pruebas unitarias en:

```text
tests/unit/modules/positioning/
```

Y se creo el plan operativo:

```text
doc/dev/positioning/plan_trabajo_modulo_posicionamiento.md
```

## 3. Que hace el modulo nuevo

El modulo recibe resultados ya recuperados y re-rankeados, y devuelve condiciones clinicas posicionadas.

La clase principal es:

```python
ClinicalPositioningService
```

Su metodo principal es:

```python
ClinicalPositioningService.position(
    query: str,
    retrieval_results: list,
    top_k: int | None = None,
) -> list[PositionedClinicalResult]
```

Cada resultado final incluye:

```text
rank
disease_name
disease_name_display
final_score
relevance_label
matched_symptoms
evidences
explanation
source_domains
component_scores
```

Esto permite que la interfaz muestre no solo una condicion, sino tambien:

- por que aparecio en el ranking;
- que sintomas o conceptos coincidieron;
- que evidencias la respaldan;
- de que fuentes vienen esas evidencias;
- que peso tuvo cada metrica.

## 4. Modelos internos implementados

### PositioningCandidate

Representa un chunk recuperado y re-rankeado, traducido a una estructura util para posicionamiento.

Incluye:

- `chunk_id`
- `doc_id`
- `text`
- `title`
- `url`
- `source_domain`
- `section_heading`
- `fetched_at`
- `published_at`
- `updated_at`
- scores lexical, vectorial, hibrido y cross-encoder
- `concept_ids`
- `ner_entities`
- metadata original
- scores normalizados

### ClinicalGroup

Representa un grupo de evidencias asociado a una condicion clinica.

Incluye:

- nombre normalizado;
- nombre para mostrar;
- evidencias;
- score de relevancia;
- score MMR;
- scores por componente;
- sintomas coincidentes;
- fuentes;
- explicaciones.

### PositioningEvidence

Representa una evidencia seleccionada para mostrar.

Incluye:

- `chunk_id`
- `doc_id`
- texto;
- preview;
- URL;
- fuente;
- seccion;
- scores;
- autoridad de fuente.

### PositionedClinicalResult

Es el contrato final que se devuelve desde el servicio de posicionamiento.

## 5. Algoritmo implementado

La implementacion sigue una estrategia de:

```text
Re-ranking clinico multicriterio + diversificacion MMR
```

El servicio ejecuta estos pasos:

1. Convertir `RetrievalResult` en `PositioningCandidate`.
2. Normalizar scores por lote de resultados.
3. Agrupar candidatos por enfermedad o condicion clinica.
4. Calcular relevancia multicriterio por grupo.
5. Aplicar MMR para diversificar.
6. Seleccionar evidencias principales.
7. Generar explicaciones deterministicas.
8. Devolver `PositionedClinicalResult[]`.

## 6. Scoring multicriterio

La formula general usada es:

```text
Rel(g, q) =
    w_ce        * CE_group(g)
  + w_hybrid    * Hybrid_group(g)
  + w_coverage  * Coverage(g, q)
  + w_authority * Authority(g)
  + w_freshness * Freshness(g)
```

Pesos por defecto:

```text
cross_encoder:     0.45
hybrid:            0.20
symptom_coverage:  0.15
authority:         0.15
freshness:         0.05
```

Estos pesos estan definidos en:

```text
src/sri_dx/modules/positioning/config.py
```

## 7. Agrupacion clinica

La agrupacion usa entidades NER con:

```text
label == "PROBLEM"
```

Y respeta:

```text
min_ner_score
max_diseases_per_chunk
```

Si un chunk no tiene entidades `PROBLEM` validas, usa fallback:

```text
title -> slug de URL -> doc_id
```

Esto evita perder resultados cuando NER no detecta una condicion.

## 8. MMR implementado

Se implemento MMR V1 sin embeddings reales.

La formula usada es:

```text
MMR(g) = lambda * Rel(g, q) - (1 - lambda) * max Sim(g, selected)
```

Parametro por defecto:

```text
lambda_mmr = 0.80
```

La similitud entre grupos usa:

- Jaccard de `concept_ids`;
- Jaccard lexical sobre textos de evidencias;
- overlap bajo de dominios fuente.

Los embeddings quedan como mejora posterior.

## 9. Explicaciones

Las explicaciones son deterministicas y salen de los scores calculados.

Ejemplos de razones generadas:

```text
Alta relevancia semantica entre la consulta y las evidencias recuperadas.
Coincide con sintomas o conceptos de la consulta: fever, shortness of breath.
Incluye evidencia procedente de fuentes clinicas confiables: cdc.gov.
Fue seleccionado considerando relevancia y diversidad frente a otros resultados.
```

Se evito usar lenguaje diagnostico definitivo.

El modulo no dice:

```text
Diagnostico mas probable
El paciente tiene X
```

Sino que presenta:

```text
condiciones clinicas asociadas
resultados informativos
apoyo al analisis diferencial
```

## 10. Integracion con el pipeline

Se modifico:

```text
src/sri_dx/usecases/search/tow_stage_retrieval_pipeline.py
```

Se agrego:

```python
search_positioned(
    query: str,
    hybrid_candidates: int | None = None,
    final_results: int | None = None,
    positioned_results: int | None = None,
)
```

El flujo interno es:

```text
1. self.search(...)
2. self._apply_ner_to_results(...)
3. ClinicalPositioningService.position(...)
4. devolver PositionedClinicalResult[]
```

Esto no cambia el flujo anterior de `search_diseases()`.

## 11. Metadata enriquecida

Para que el posicionamiento tenga mas contexto, se enriquecio la metadata que llega desde la busqueda.

Archivos modificados:

```text
src/sri_dx/core/schemas/search/search_response.py
src/sri_dx/adapters/stores/opensearch_search_backend.py
src/sri_dx/usecases/search/search_hybrid.py
src/sri_dx/adapters/stores/opensearch_embedding_sink.py
```

Campos agregados o propagados:

```text
fetched_at
section_heading
section_index
chunk_index
concept_ids
```

Esto ayuda a calcular:

- frescura;
- seleccion de evidencias;
- cobertura de conceptos;
- explicabilidad;
- trazabilidad.

## 12. Integracion con CLI

Se modifico:

```text
src/sri_dx/app/cli/search_cli.py
```

Se agregaron flags:

```text
--positioned
--positioned-results
--show-component-scores
```

Ejemplo:

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10 \
  --positioned \
  --positioned-results 5 \
  --show-component-scores
```

## 13. Integracion con API

Se modifico:

```text
src/sri_dx/app/api/main.py
```

Se agrego endpoint:

```text
POST /api/positioned
```

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/positioned \
  -H "Content-Type: application/json" \
  -d '{
    "query": "fever cough shortness of breath",
    "k": 5,
    "min_ner_score": 0.5,
    "hybrid_candidates": 100,
    "final_results": 10
  }'
```

## 14. Integracion con Streamlit

Se modifico:

```text
src/sri_dx/app/ui/ui_streamlit.py
```

Se agrego un nuevo modo:

```text
Condiciones posicionadas
```

En ese modo se muestran:

- condicion;
- etiqueta de relevancia;
- score final;
- sintomas o conceptos coincidentes;
- fuentes;
- explicacion;
- evidencias principales;
- scores por componente.

## 15. Integracion con frontend React

Se modifico:

```text
frontend/src/services/api.ts
```

Se agrego:

```typescript
searchPositioned(params)
```

Esto deja listo el servicio para consumir:

```text
/api/positioned
```

La pantalla React aun no fue redisenada para mostrar el nuevo contrato; la visualizacion principal del nuevo flujo quedo en Streamlit.

## 16. Pruebas agregadas

Se agregaron pruebas unitarias en:

```text
tests/unit/modules/positioning/
```

Cubren:

- adaptador desde `RetrievalResult`;
- metadata completa, parcial y ausente;
- agrupacion por NER;
- multiples enfermedades por chunk;
- umbral de NER;
- fallbacks por titulo, URL y `doc_id`;
- normalizacion de scores;
- parsing de fechas;
- cobertura de sintomas y conceptos;
- autoridad de dominios;
- frescura;
- scoring multicriterio;
- MMR;
- servicio completo con fixtures fake.

## 17. Validacion realizada

El comando con `uv` fallo por un problema local de `snap-confine`/AppArmor:

```text
snap-confine has elevated permissions and is not confined
```

Por eso se valido usando directamente el Python del `.venv`.

### Suite nueva del modulo

```bash
.venv/bin/python -m pytest tests/unit/modules/positioning
```

Resultado:

```text
23 passed
```

### Suite enfocada del plan

```bash
.venv/bin/python -m pytest \
  tests/unit/modules/positioning \
  tests/unit/modules/indexing/test_concept_extractor.py \
  tests/unit/usecases
```

Resultado:

```text
30 passed
```

### Build frontend

```bash
cd frontend
npm run build
```

Resultado:

```text
build correcto
```

### Validacion de sintaxis

```bash
.venv/bin/python -m compileall \
  src/sri_dx/modules/positioning \
  src/sri_dx/usecases/search/tow_stage_retrieval_pipeline.py \
  src/sri_dx/app/cli/search_cli.py \
  src/sri_dx/app/api/main.py \
  src/sri_dx/app/ui/ui_streamlit.py
```

Resultado:

```text
sin errores
```

### Diff check

```bash
git diff --check
```

Resultado:

```text
sin errores de whitespace
```

## 18. Nota sobre test preexistente

Al ejecutar toda la suite:

```bash
.venv/bin/python -m pytest tests/unit
```

Aparece un error preexistente en:

```text
tests/unit/modules/indexing/test_chunking.py
```

El test intenta parchear:

```text
sri_dx.modules.indexing.chunking.SemanticChunker
```

Pero ese simbolo no existe actualmente en el modulo `chunking.py`.

No se corrigio dentro de este trabajo para no mezclar cambios de chunking con el modulo de posicionamiento.

## 19. Como correr el proyecto localmente

### Opcion A: Docker Compose completo

Desde la raiz del repo:

```bash
docker compose up --build
```

Servicios esperados:

```text
OpenSearch: http://localhost:9200
Streamlit:  http://localhost:8501
API:        http://localhost:8000
```

Verificar OpenSearch:

```bash
curl http://localhost:9200/_cluster/health
```

Detener:

```bash
docker compose down
```

Detener y borrar volumenes:

```bash
docker compose down -v
```

### Opcion B: desarrollo local

Levantar solo OpenSearch:

```bash
docker compose up -d opensearch
```

Ejecutar Streamlit:

```bash
.venv/bin/python -m streamlit run src/sri_dx/app/ui/ui_streamlit.py
```

Ejecutar API:

```bash
.venv/bin/python -m uvicorn sri_dx.app.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

Ejecutar frontend React:

```bash
cd frontend
npm install
npm run dev
```

## 20. Preparar indices para probar posicionamiento

La funcionalidad nueva necesita datos en:

```text
clinical_chunks
clinical_embeddings_v1
```

### Indexar chunks

```bash
.venv/bin/python src/sri_dx/app/cli/index_chunks_cli.py --refresh
```

Por defecto usa:

```text
data/processed/docs_html.jsonl
data/processed/docs_pdf.jsonl
```

### Generar embeddings

```bash
.venv/bin/python src/sri_dx/app/cli/embed_cli.py \
  --chunks-index clinical_chunks_v1 \
  --embeddings-index clinical_embeddings_v1 \
  --device cpu
```

### Indexar documentos completos, opcional

```bash
.venv/bin/python src/sri_dx/app/cli/index_opensearch.py --refresh
```

Esto no es estrictamente lo mas importante para `search_positioned()`, pero mantiene el indice documental completo actualizado.

## 21. Como probar la nueva funcionalidad

### Probar por CLI

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10 \
  --positioned \
  --positioned-results 5 \
  --show-component-scores
```

Salida esperada:

```text
TOP N CONDICIONES POSICIONADAS
--------------------------------------------------------------------------------
#1) Pneumonia [Alta] score=...
   coincidencias=fever, shortness of breath
   fuentes=cdc.gov, ...
   component_scores={...}
   - Alta relevancia semantica...
   evidencia chunk=...
```

### Probar por API

Con la API levantada:

```bash
curl -X POST http://localhost:8000/api/positioned \
  -H "Content-Type: application/json" \
  -d '{
    "query": "fever cough shortness of breath",
    "k": 5,
    "min_ner_score": 0.5,
    "hybrid_candidates": 100,
    "final_results": 10
  }'
```

### Probar por Streamlit

1. Abrir:

```text
http://localhost:8501
```

2. En modo de busqueda elegir:

```text
Condiciones posicionadas
```

3. Probar una consulta:

```text
fever cough shortness of breath
```

4. Revisar cada resultado expandido.

Debe mostrar:

- condicion;
- score;
- etiqueta de relevancia;
- coincidencias;
- fuentes;
- explicacion;
- evidencias;
- scores por componente.

## 22. Consultas sugeridas

```text
fever cough shortness of breath
```

```text
chest pain shortness of breath fatigue
```

```text
diabetes insulin treatment hyperglycemia
```

```text
seizures epilepsy anticonvulsant medication
```

```text
multiple sclerosis neurological symptoms
```

## 23. Limitaciones actuales

- MMR V1 no usa embeddings reales todavia.
- La frescura usa `updated_at -> published_at -> fetched_at`, pero en chunks normalmente solo llega `fetched_at`.
- `title`, `published_at` y `updated_at` no estan completamente propagados a chunks.
- La visualizacion nueva esta integrada en Streamlit; React solo tiene preparado el servicio API.
- La extraccion de conceptos sigue centrada principalmente en ingles; `LEXICON_ES` queda como mejora posterior.

## 24. Mejoras recomendadas siguientes

1. Corregir el test preexistente de chunking o ajustar el contrato esperado.
2. Propagar `title`, `published_at` y `updated_at` a chunks en una fase controlada.
3. Recuperar embeddings reales para usar similitud coseno en MMR.
4. Conectar `LEXICON_ES` al extractor de conceptos.
5. Agregar vista completa de resultados posicionados en el frontend React.
6. Crear tests de integracion con OpenSearch poblado.
7. Documentar ejemplos de salida reales con un corpus ya indexado.

