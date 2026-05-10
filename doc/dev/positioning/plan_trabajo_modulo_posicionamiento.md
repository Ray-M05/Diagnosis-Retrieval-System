# Plan de trabajo del modulo de posicionamiento clinico

## Resumen

Este plan implementa el modulo de posicionamiento como una etapa posterior al recuperador hibrido y al cross-encoder existentes. El objetivo es transformar chunks re-rankeados en condiciones clinicas posicionadas, diversas, explicables y trazables, sin presentar los resultados como diagnosticos automaticos.

Flujo objetivo:

```text
SearchHybridUseCase
-> TwoStageRetrievalPipeline.search()
-> NER on-demand
-> ClinicalPositioningService
-> resultados clinicos posicionados
-> CLI / API / UI
```

El archivo real del pipeline se mantiene como `src/sri_dx/usecases/search/tow_stage_retrieval_pipeline.py` para no romper imports existentes.

## Cambios principales

- Crear `src/sri_dx/modules/positioning` con modelos, configuracion, adaptadores, agrupacion, scoring, MMR, seleccion de evidencias, explicaciones y servicio principal.
- Exponer `ClinicalPositioningService.position(query, retrieval_results, top_k=None)`.
- Agregar `TwoStageRetrievalPipeline.search_positioned(...)` sin cambiar `search()` ni `search_diseases()`.
- Propagar metadata minima desde busqueda: `fetched_at`, `section_heading`, `section_index`, `chunk_index`.
- Agregar CLI/API/UI para consultar condiciones posicionadas despues de validar el nucleo.

## Fases de implementacion

1. Crear modelos y configuracion con pesos por defecto: cross-encoder `0.45`, hybrid `0.20`, cobertura `0.15`, autoridad `0.15`, frescura `0.05`, `lambda_mmr=0.80` y `top_evidences=3`.
2. Adaptar `RetrievalResult` a `PositioningCandidate`, tolerando metadata incompleta y preservando scores originales.
3. Agrupar por condicion clinica usando entidades NER `PROBLEM`, con fallback `title -> slug de URL -> doc_id`.
4. Calcular scoring multicriterio con normalizacion por lote, cobertura de sintomas/conceptos, autoridad de fuente y frescura.
5. Aplicar MMR V1 sin embeddings, usando similitud por conceptos, texto y dominios.
6. Seleccionar evidencias principales y generar explicaciones deterministicas sin lenguaje diagnostico definitivo.
7. Integrar `ClinicalPositioningService` en el pipeline mediante `search_positioned()`.
8. Enriquecer metadata minima en busqueda hibrida.
9. Exponer el nuevo flujo por CLI, API y Streamlit.

## Pruebas

Validar con fixtures puros, sin OpenSearch ni modelos reales:

- adaptador con metadata completa/parcial/ausente;
- normalizacion de scores y fechas;
- agrupacion por NER y fallbacks;
- cobertura por conceptos y aliases;
- autoridad por dominios;
- frescura por `updated_at -> published_at -> fetched_at`;
- scoring multicriterio con pesos custom;
- MMR contra resultados redundantes;
- servicio completo end-to-end.

Comandos:

```bash
uv run pytest tests/unit/modules/positioning
uv run pytest tests/unit/modules/indexing/test_concept_extractor.py
uv run pytest tests/unit/usecases
```

## Supuestos

- V1 no reindexa documentos.
- V1 usa MMR sin embeddings reales.
- El modulo muestra condiciones clinicas asociadas, no diagnosticos automaticos.
- `DiseaseAggregator` queda como compatibilidad.
