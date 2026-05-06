# Plan por fases pequenas para implementar el modulo de posicionamiento

Fecha: 2026-05-04

Documento base: `doc/dev/positioning/analisis_plan_modulo_posicionamiento.md`

Objetivo de este documento: dividir la implementacion del modulo de posicionamiento clinico en pasos pequenos, revisables y con prompts especificos para pedirle trabajo a Codex sin meter demasiados cambios de una sola vez.

La idea es avanzar con una regla simple:

```text
Una fase = un cambio acotado + pruebas/revision + decision antes de seguir.
```

## Reglas generales para usar estos prompts

1. No mandar dos fases juntas.
2. Revisar el diff despues de cada fase.
3. Pedir pruebas unitarias en cada fase donde aplique.
4. No tocar UI ni CLI hasta que el nucleo del modulo este estable.
5. No cambiar el comportamiento existente de `search_diseases()` hasta tener `search_positioned()` funcionando.
6. Preferir funciones puras y tests pequenos antes de integrar con OpenSearch/modelos.
7. Mantener los cambios dentro de `src/sri_dx/modules/positioning`, `src/sri_dx/core/schemas/search` y tests, salvo fases explicitas de integracion.

## Fase 0: Auditoria corta antes de tocar codigo

### Objetivo

Confirmar el estado exacto de los contratos actuales de busqueda, ranking y metadata antes de crear el modulo.

### Alcance

Solo lectura. No modificar archivos.

### Resultado esperado

Un resumen breve con:

- que campos llegan hoy en `RetrievalResult`;
- que campos faltan para posicionamiento;
- que archivos se tocarian en las siguientes fases;
- riesgos detectados antes de empezar.

### Prompt para Codex

```text
Revisa el estado actual del flujo de busqueda y ranking sin modificar archivos.

Quiero que inspecciones:
- src/sri_dx/usecases/search/two_stage_retrieval_pipeline.py
- src/sri_dx/usecases/search/search_hybrid.py
- src/sri_dx/modules/ranking/disease_aggregator.py
- src/sri_dx/core/schemas/search/*
- src/sri_dx/adapters/stores/opensearch_search_backend.py
- src/sri_dx/adapters/stores/opensearch_chunk_reader.py
- src/sri_dx/adapters/stores/opensearch_embedding_sink.py

Necesito una respuesta corta que diga:
1. Que metadata llega hoy a un RetrievalResult.
2. Que metadata falta para el modulo de posicionamiento.
3. Que archivos conviene tocar primero.
4. Que riesgos ves antes de implementar.

No hagas cambios de codigo todavia.
```

### Criterio de revision

Aceptar solo si no hay cambios en `git diff`.

## Fase 1: Crear estructura vacia del modulo y modelos internos

### Objetivo

Crear el paquete `modules/positioning` con modelos internos, sin integrarlo todavia al pipeline.

### Alcance

Crear:

```text
src/sri_dx/modules/positioning/__init__.py
src/sri_dx/modules/positioning/models.py
src/sri_dx/modules/positioning/config.py
```

No tocar:

- `TwoStageRetrievalPipeline`
- `DiseaseAggregator`
- UI
- CLI

### Contenido esperado

Modelos:

- `PositioningCandidate`
- `ClinicalGroup`
- `PositioningEvidence`
- `PositionedClinicalResult`

Config:

- `PositioningConfig`
- pesos por defecto
- tabla de autoridad por defecto
- secciones preferidas

### Prompt para Codex

```text
Implementa solo la estructura inicial del modulo de posicionamiento.

Crea:
- src/sri_dx/modules/positioning/__init__.py
- src/sri_dx/modules/positioning/models.py
- src/sri_dx/modules/positioning/config.py

Necesito dataclasses o modelos simples para:
- PositioningCandidate
- ClinicalGroup
- PositioningEvidence
- PositionedClinicalResult

Y una configuracion PositioningConfig con:
- top_k
- top_evidences
- lambda_mmr
- min_ner_score
- max_diseases_per_chunk
- unknown_freshness_score
- unknown_authority_score
- weights por defecto: cross_encoder, hybrid, symptom_coverage, authority, freshness
- tabla default de autoridad de fuentes
- pesos de secciones preferidas

No integres nada con el pipeline todavia.
No modifiques SearchHybridUseCase, TwoStageRetrievalPipeline, DiseaseAggregator, CLI ni UI.
Agrega tests unitarios basicos solo si hace falta validar defaults.
```

### Criterio de revision

El diff debe mostrar solo archivos nuevos del modulo y, opcionalmente, tests muy pequenos.

## Fase 2: Adaptador desde RetrievalResult a PositioningCandidate

### Objetivo

Traducir la salida actual del pipeline a candidatos posicionables.

### Alcance

Crear:

```text
src/sri_dx/modules/positioning/adapters.py
tests/unit/modules/positioning/test_adapters.py
```

No integrar todavia al pipeline.

### Reglas de conversion

```text
text = result.content
    or metadata["content"]
    or metadata["chunk_text"]
    or metadata["chunk_text_preview"]
    or ""

chunk_id = metadata["chunk_id"] or result.doc_id
doc_id = result.doc_id
cross_encoder_score = result.rerank_score
hybrid_score = result.original_hybrid_score
lexical_score = result.lexical_score
vector_score = result.vector_score
```

Copiar desde metadata si existe:

- `title`
- `url`
- `source_domain`
- `section_heading`
- `fetched_at`
- `published_at`
- `updated_at`
- `mime_type`
- `seed_group`
- `concept_ids`
- `ner_entities`

### Prompt para Codex

```text
Implementa el adaptador del modulo de posicionamiento desde RetrievalResult hacia PositioningCandidate.

Crea:
- src/sri_dx/modules/positioning/adapters.py
- tests/unit/modules/positioning/test_adapters.py

La funcion principal debe aceptar una lista de objetos compatibles con RetrievalResult y devolver list[PositioningCandidate].

Reglas:
- text debe salir de result.content, metadata["content"], metadata["chunk_text"], metadata["chunk_text_preview"], en ese orden.
- chunk_id debe salir de metadata["chunk_id"] o caer a result.doc_id.
- doc_id debe ser result.doc_id.
- cross_encoder_score debe ser result.rerank_score.
- hybrid_score debe ser result.original_hybrid_score.
- lexical_score y vector_score deben conservarse.
- Debe copiar metadata clinica si existe: title, url, source_domain, section_heading, fetched_at, published_at, updated_at, mime_type, seed_group, concept_ids, ner_entities.
- Debe tolerar metadata faltante sin romper.

No integres esto todavia con TwoStageRetrievalPipeline.
Agrega tests unitarios con objetos fake simples, sin cargar modelos ni OpenSearch.
```

### Criterio de revision

Los tests deben cubrir:

- metadata completa;
- metadata parcial;
- resultado sin contenido;
- fallback de `chunk_id`;
- preservacion de scores.

## Fase 3: Utilidades de normalizacion de scores y fechas

### Objetivo

Crear funciones puras para normalizar scores heterogeneos y parsear fechas.

### Alcance

Crear o actualizar:

```text
src/sri_dx/modules/positioning/scoring.py
tests/unit/modules/positioning/test_scoring.py
```

### Funciones esperadas

- `minmax_normalize`
- `sigmoid`
- `normalize_candidate_scores`
- `parse_optional_datetime`
- `days_since`

### Prompt para Codex

```text
Implementa utilidades puras de scoring para el modulo de posicionamiento.

Crea o actualiza:
- src/sri_dx/modules/positioning/scoring.py
- tests/unit/modules/positioning/test_scoring.py

Necesito:
1. minmax_normalize(values)
2. sigmoid(value)
3. normalize_candidate_scores(candidates)
4. parse_optional_datetime(value)
5. days_since(date_value, reference_date)

Requisitos:
- minmax_normalize([]) debe devolver [].
- Si todos los valores son iguales, devolver 1.0 para los valores presentes.
- Debe tolerar None sin romper.
- normalize_candidate_scores debe producir candidatos o estructuras con scores normalizados sin perder los scores originales.
- parse_optional_datetime debe aceptar strings ISO comunes y None.
- Las pruebas no deben depender de la fecha actual; usa reference_date inyectable.

No integres todavia con el pipeline.
No toques UI ni CLI.
```

### Criterio de revision

Aceptar si los tests prueban casos vacios, valores iguales, valores mixtos y fechas invalidas.

## Fase 4: Agrupacion clinica por enfermedad/condicion

### Objetivo

Agrupar candidatos en `ClinicalGroup` usando NER y fallbacks.

### Alcance

Crear:

```text
src/sri_dx/modules/positioning/grouping.py
tests/unit/modules/positioning/test_grouping.py
```

### Reglas

1. Usar entidades con `label == "PROBLEM"`.
2. Aplicar `min_ner_score`.
3. Normalizar nombres:
   - lowercase;
   - quitar espacios repetidos;
   - quitar sufijos genericos como `symptoms`, `signs`, `disease`, `disorder`, `syndrome`;
   - expandir acronimos locales si conviene reutilizar el mapa de `DiseaseAggregator`.
4. Limitar maximo de enfermedades por chunk.
5. Si no hay entidades validas:
   - usar `title`;
   - si no hay `title`, usar slug de URL;
   - si no hay URL, usar `doc_id`.

### Prompt para Codex

```text
Implementa la agrupacion clinica del modulo de posicionamiento.

Crea:
- src/sri_dx/modules/positioning/grouping.py
- tests/unit/modules/positioning/test_grouping.py

La funcion principal debe agrupar list[PositioningCandidate] en list[ClinicalGroup].

Reglas:
- Usar ner_entities con label == "PROBLEM" y score >= config.min_ner_score.
- Normalizar nombres de enfermedad en lowercase, quitando espacios repetidos y sufijos genericos como symptoms, signs, disease, disorder, syndrome.
- Reutilizar o replicar de forma pequena el mapa local de acronimos de DiseaseAggregator si es razonable.
- Respetar config.max_diseases_per_chunk.
- Si un candidato no tiene entidades PROBLEM validas, usar fallback title -> slug de URL -> doc_id.
- No perder evidencias al agrupar.
- No modificar DiseaseAggregator todavia.

Agrega tests unitarios para:
- agrupacion por una enfermedad;
- multiples enfermedades en un chunk;
- filtrado por min_ner_score;
- fallback por title;
- fallback por URL/doc_id;
- normalizacion de nombres.
```

### Criterio de revision

Aceptar si se puede revisar la agrupacion sin depender del NER real.

## Fase 5: Cobertura de sintomas y conceptos

### Objetivo

Implementar `Coverage(g, q)` de forma robusta y testeable.

### Alcance

Actualizar:

```text
src/sri_dx/modules/positioning/scoring.py
tests/unit/modules/positioning/test_scoring.py
```

Opcional:

```text
src/sri_dx/modules/positioning/symptoms.py
tests/unit/modules/positioning/test_symptoms.py
```

### Reglas

Usar capas:

1. `concept_ids` si estan disponibles.
2. Sinonimos/aliases simples para sintomas comunes.
3. Matching textual normalizado como fallback.

Si no se detectan sintomas o conceptos en la consulta, devolver valor neutral `0.5`.

### Prompt para Codex

```text
Implementa la metrica de cobertura de sintomas/conceptos para el modulo de posicionamiento.

Puedes crear:
- src/sri_dx/modules/positioning/symptoms.py
- tests/unit/modules/positioning/test_symptoms.py

O integrarlo en scoring.py si queda pequeno.

Requisitos:
- La funcion debe recibir query y ClinicalGroup.
- Debe usar concept_ids de las evidencias cuando sea posible.
- Debe detectar conceptos/sintomas simples en la query usando ConceptExtractor si se puede importar sin cargar modelos pesados.
- Debe tener fallback por aliases/sinonimos y texto normalizado.
- Debe devolver un score entre 0 y 1 y la lista de sintomas/conceptos coincidentes para mostrar en UI.
- Si no hay sintomas/conceptos detectables en la query, devolver score neutral 0.5 y matched vacio.
- No usar modelos pesados ni BiomedicalNERAdapter en esta fase.

Agrega tests para:
- shortness of breath vs dyspnea;
- fever vs pyrexia;
- chest pain;
- query sin sintomas;
- evidencias sin concept_ids.
```

### Criterio de revision

Aceptar si no carga modelos externos y los tests son deterministas.

## Fase 6: Autoridad de fuente

### Objetivo

Implementar `Authority(g)` usando dominios normalizados y tabla configurable.

### Alcance

Actualizar:

```text
src/sri_dx/modules/positioning/scoring.py
tests/unit/modules/positioning/test_scoring.py
```

O crear:

```text
src/sri_dx/modules/positioning/authority.py
tests/unit/modules/positioning/test_authority.py
```

### Prompt para Codex

```text
Implementa la metrica de autoridad de fuente para el modulo de posicionamiento.

Requisitos:
- Normalizar dominios: lowercase, quitar esquema, quitar www., quitar slash final.
- Usar config.source_reliability.
- Usar config.unknown_authority_score para dominios desconocidos.
- Usar un score menor para evidencias sin dominio.
- Para un ClinicalGroup, calcular autoridad usando maximo y promedio de dominios unicos de forma simple.
- Debe devolver un valor entre 0 y 1.

Agrega tests para:
- www.mayoclinic.org -> mayoclinic.org.
- dominio listado.
- dominio desconocido.
- evidencia sin dominio.
- grupo con varias fuentes.

No integres todavia con el pipeline.
```

### Criterio de revision

Aceptar si la funcion no depende de red ni de OpenSearch.

## Fase 7: Frescura

### Objetivo

Implementar `Freshness(g)` distinguiendo fecha clinica y fecha de adquisicion cuando existan.

### Alcance

Actualizar:

```text
src/sri_dx/modules/positioning/scoring.py
tests/unit/modules/positioning/test_scoring.py
```

O crear:

```text
src/sri_dx/modules/positioning/freshness.py
tests/unit/modules/positioning/test_freshness.py
```

### Reglas

Orden de preferencia:

```text
updated_at -> published_at -> fetched_at -> unknown
```

### Prompt para Codex

```text
Implementa la metrica de frescura para el modulo de posicionamiento.

Requisitos:
- Para cada evidencia, preferir updated_at, luego published_at, luego fetched_at.
- Si no hay fecha valida, usar config.unknown_freshness_score.
- La funcion debe aceptar reference_date para tests deterministas.
- El score debe quedar entre 0 y 1.
- Usa una funcion por tramos simple:
  - <= 180 dias: 1.00
  - <= 365 dias: 0.85
  - <= 730 dias: 0.70
  - <= 1825 dias: 0.55
  - mas antiguo: 0.40
  - desconocido: config.unknown_freshness_score
- Para grupo, usa las top evidencias disponibles y no una suma simple.

Agrega tests para:
- updated_at reciente;
- published_at cuando no hay updated_at;
- fetched_at cuando no hay las anteriores;
- fecha desconocida;
- fecha invalida;
- grupo con varias evidencias.

No integres todavia con el pipeline.
```

### Criterio de revision

Aceptar si los tests no dependen de `datetime.now()`.

## Fase 8: Scoring multicriterio del grupo

### Objetivo

Combinar cross-encoder, score hibrido, cobertura, autoridad y frescura.

### Alcance

Actualizar:

```text
src/sri_dx/modules/positioning/scoring.py
tests/unit/modules/positioning/test_scoring.py
```

### Prompt para Codex

```text
Implementa el scoring multicriterio de grupos clinicos.

Requisitos:
- Agregar funciones para:
  - aggregate_group_signal
  - score_clinical_group
  - score_clinical_groups
- CE_group debe agregarse desde cross_encoder_score normalizado de evidencias.
- Hybrid_group debe agregarse desde hybrid_score normalizado.
- Coverage debe usar la funcion ya implementada.
- Authority debe usar la funcion ya implementada.
- Freshness debe usar la funcion ya implementada.
- Relevance debe usar config.weights:
  cross_encoder, hybrid, symptom_coverage, authority, freshness.
- Guardar component_scores en el grupo o en una estructura asociada.
- Mantener todos los scores entre 0 y 1.

Agrega tests para:
- grupo con una evidencia;
- grupo con varias evidencias;
- scores faltantes;
- pesos custom;
- cobertura neutral cuando no aplica.

No integres todavia con TwoStageRetrievalPipeline.
```

### Criterio de revision

Aceptar si se puede entender en tests por que un grupo queda arriba de otro.

## Fase 9: MMR sin embeddings

### Objetivo

Implementar diversificacion con MMR usando similitud por conceptos/texto/fuentes.

### Alcance

Crear:

```text
src/sri_dx/modules/positioning/mmr.py
tests/unit/modules/positioning/test_mmr.py
```

### Prompt para Codex

```text
Implementa MMR para ClinicalGroup sin usar embeddings todavia.

Crea:
- src/sri_dx/modules/positioning/mmr.py
- tests/unit/modules/positioning/test_mmr.py

Requisitos:
- Implementar group_similarity(group_a, group_b) usando:
  - Jaccard de concept_ids de evidencias.
  - Jaccard lexical simple sobre textos de top evidencias.
  - overlap bajo de source_domains.
- Implementar mmr_rerank(groups, top_k, lambda_mmr).
- Si no hay grupos seleccionados, elegir por relevance_score.
- Guardar mmr_score en los grupos seleccionados o devolver una estructura con score.
- No usar embeddings en esta fase.

Agrega tests para:
- primer resultado por relevancia.
- segundo resultado diverso cuando hay un duplicado muy parecido.
- lambda alto prioriza relevancia.
- top_k mayor que cantidad de grupos.
```

### Criterio de revision

Aceptar si el test demuestra que MMR evita duplicados.

## Fase 10: Seleccion de evidencias y explicaciones

### Objetivo

Elegir top evidencias por condicion y generar explicaciones deterministicas.

### Alcance

Crear:

```text
src/sri_dx/modules/positioning/evidence.py
src/sri_dx/modules/positioning/explanations.py
tests/unit/modules/positioning/test_evidence.py
tests/unit/modules/positioning/test_explanations.py
```

### Prompt para Codex

```text
Implementa seleccion de evidencias y explicaciones para el modulo de posicionamiento.

Crea:
- src/sri_dx/modules/positioning/evidence.py
- src/sri_dx/modules/positioning/explanations.py
- tests correspondientes.

Seleccion de evidencias:
- Ordenar por cross_encoder_score, autoridad de fuente y seccion preferida.
- Preferir secciones como symptoms, signs and symptoms, overview, causes, diagnosis.
- Evitar evidencias con texto casi duplicado.
- Limitar por config.top_evidences.

Explicaciones:
- Generar frases deterministicas segun component_scores.
- Mencionar relevancia semantica si CE es alto.
- Mencionar sintomas coincidentes si hay matched_symptoms.
- Mencionar fuentes confiables si authority es alto.
- Mencionar diversidad/MMR si aplica.
- No usar lenguaje diagnostico definitivo.

Agrega tests para:
- ranking de evidencias por seccion y score.
- deduplicacion simple.
- explicacion con CE alto.
- explicacion con sintomas.
- explicacion con autoridad.
```

### Criterio de revision

Aceptar si las explicaciones son sobrias y no dicen "diagnostico probable".

## Fase 11: Servicio principal ClinicalPositioningService

### Objetivo

Orquestar todo el modulo sin integrarlo aun con el pipeline.

### Alcance

Crear:

```text
src/sri_dx/modules/positioning/service.py
tests/unit/modules/positioning/test_service.py
```

### Flujo esperado

```text
RetrievalResult[]
  -> PositioningCandidate[]
  -> normalizacion
  -> agrupacion
  -> scoring
  -> MMR
  -> evidencias
  -> explicaciones
  -> PositionedClinicalResult[]
```

### Prompt para Codex

```text
Implementa ClinicalPositioningService como orquestador del modulo de posicionamiento.

Crea:
- src/sri_dx/modules/positioning/service.py
- tests/unit/modules/positioning/test_service.py

El servicio debe exponer:
- position(query: str, retrieval_results: list, top_k: int | None = None) -> list[PositionedClinicalResult]

Debe usar las piezas ya implementadas:
- adaptador RetrievalResult -> PositioningCandidate.
- normalizacion de scores.
- agrupacion clinica.
- scoring multicriterio.
- MMR.
- seleccion de evidencias.
- explicaciones.

Requisitos:
- Si no hay resultados, devolver [].
- No cargar modelos.
- No llamar OpenSearch.
- No modificar los objetos originales si se puede evitar.
- Devolver resultados con rank 1-based.
- Incluir component_scores en la salida.

Agrega tests end-to-end con fixtures fake:
- dos enfermedades diferentes;
- enfermedad duplicada en varios chunks;
- resultado sin NER que cae a fallback;
- top_k.

No integres todavia con TwoStageRetrievalPipeline.
```

### Criterio de revision

Aceptar si el servicio completo funciona con fixtures sin infraestructura externa.

## Fase 12: Integracion no disruptiva con TwoStageRetrievalPipeline

### Objetivo

Agregar `search_positioned()` sin cambiar `search()` ni romper `search_diseases()`.

### Alcance

Modificar:

```text
src/sri_dx/usecases/search/two_stage_retrieval_pipeline.py
```

Agregar tests si ya existe una forma limpia de mockear el pipeline. Si no, mantener el cambio pequeno y revisable.

### Prompt para Codex

```text
Integra el modulo de posicionamiento de forma no disruptiva en TwoStageRetrievalPipeline.

Modifica:
- src/sri_dx/usecases/search/two_stage_retrieval_pipeline.py

Agrega un metodo nuevo:
- search_positioned(query, hybrid_candidates=None, final_results=None, positioned_results=None)

Flujo:
1. Llamar self.search(query, hybrid_candidates, final_results).
2. Si no hay chunks, devolver [].
3. Reutilizar _apply_ner_to_results(chunk_results).
4. Crear ClinicalPositioningService si no existe o usar uno inyectable.
5. Devolver PositionedClinicalResult[].

Requisitos:
- No cambiar comportamiento de search().
- No cambiar comportamiento de search_diseases().
- No tocar CLI ni UI en esta fase.
- Mantener compatibilidad con tests existentes.
```

### Criterio de revision

Aceptar si `search()` y `search_diseases()` quedan intactos.

## Fase 13: Enriquecer metadata minima para frescura y seccion

### Objetivo

Hacer que lleguen mas campos utiles al posicionamiento.

### Alcance

Modificar con mucho cuidado:

```text
src/sri_dx/core/schemas/search/search_response.py
src/sri_dx/adapters/stores/opensearch_search_backend.py
src/sri_dx/usecases/search/search_hybrid.py
```

### Campos deseados

- `fetched_at`
- `section_heading`
- `section_index`
- `chunk_index`

### Prompt para Codex

```text
Enriquece la metadata que llega desde la busqueda lexical/hibrida para soportar posicionamiento.

Modifica solo lo necesario:
- src/sri_dx/core/schemas/search/search_response.py
- src/sri_dx/adapters/stores/opensearch_search_backend.py
- src/sri_dx/usecases/search/search_hybrid.py

Objetivo:
- Que los resultados lexicales sobre clinical_chunks propaguen fetched_at, section_heading, section_index y chunk_index cuando existan.
- Que SearchHybridUseCase._lexical_search copie esos campos en metadata.

Requisitos:
- Mantener compatibilidad con documentos que no tienen esos campos.
- No romper busqueda lexical sobre indice de documentos completos.
- No tocar posicionamiento salvo que sea necesario por imports.
- Agregar o ajustar tests si hay tests existentes adecuados.
```

### Criterio de revision

Aceptar si los campos nuevos son opcionales y no rompen busqueda existente.

## Fase 14: CLI para resultados posicionados

### Objetivo

Exponer el nuevo flujo por CLI para probarlo sin tocar la UI.

### Alcance

Modificar:

```text
src/sri_dx/app/cli/search_cli.py
```

### Prompt para Codex

```text
Agrega soporte CLI para el nuevo flujo de posicionamiento.

Modifica:
- src/sri_dx/app/cli/search_cli.py

Requisitos:
- Agregar flag --positioned para type hybrid.
- Cuando --positioned este activo, usar TwoStageRetrievalPipeline.search_positioned().
- Imprimir:
  - rank
  - disease_name_display
  - final_score
  - relevance_label
  - matched_symptoms
  - fuentes
  - top evidencias
  - component_scores opcional si agregas --show-component-scores.
- No cambiar el comportamiento actual de --diseases.
- No tocar Streamlit en esta fase.
```

### Criterio de revision

Aceptar si el CLI conserva `--diseases` y agrega una ruta separada para `--positioned`.

## Fase 15: UI Streamlit para condiciones posicionadas

### Objetivo

Mostrar resultados posicionados en la interfaz.

### Alcance

Modificar:

```text
src/sri_dx/app/ui/ui_streamlit.py
```

### Prompt para Codex

```text
Integra el modo de condiciones posicionadas en Streamlit.

Modifica:
- src/sri_dx/app/ui/ui_streamlit.py

Requisitos:
- Agregar un modo nuevo o reemplazar de forma cuidadosa el modo "Diagnostico por Enfermedades" por "Condiciones posicionadas".
- Usar pipeline.search_positioned().
- Mostrar:
  - rank
  - nombre de condicion
  - etiqueta de relevancia
  - sintomas coincidentes
  - explicacion
  - fuentes
  - evidencias principales
  - component_scores en un expander de debug.
- Mantener advertencia medica.
- Evitar lenguaje de diagnostico automatico.
- No tocar frontend React en esta fase.
```

### Criterio de revision

Aceptar si la UI sigue permitiendo busqueda por chunks y el nuevo modo no rompe la carga del pipeline.

## Fase 16: Correcciones de calidad y tests integrados

### Objetivo

Ejecutar pruebas, corregir fallos y limpiar inconsistencias.

### Alcance

No agregar funcionalidades nuevas.

### Prompt para Codex

```text
Haz una pasada de verificacion del modulo de posicionamiento.

Quiero que:
1. Ejecutes los tests unitarios relevantes.
2. Corrijas errores encontrados.
3. Revises imports, tipos, nombres y compatibilidad con el estilo del repo.
4. No agregues nuevas funcionalidades.
5. No cambies pesos ni comportamiento salvo que sea necesario para pasar tests o corregir bugs claros.

Al final, resume:
- comandos ejecutados;
- tests que pasaron/fallaron;
- archivos modificados;
- riesgos pendientes.
```

### Criterio de revision

Aceptar solo si no hay cambios funcionales nuevos mezclados con limpieza.

## Fase 17: Mejora posterior con embeddings para MMR

### Objetivo

Usar embeddings reales para similitud entre grupos.

### Importante

Esta fase debe hacerse despues de tener V1 funcionando. No es necesaria para la primera version.

### Alcance probable

Modificar:

```text
src/sri_dx/adapters/stores/opensearch_embedding_sink.py
src/sri_dx/modules/positioning/mmr.py
```

### Prompt para Codex

```text
Mejora MMR del modulo de posicionamiento para usar embeddings cuando esten disponibles.

Antes de modificar, revisa:
- src/sri_dx/adapters/stores/opensearch_embedding_sink.py
- src/sri_dx/modules/positioning/mmr.py
- src/sri_dx/modules/positioning/models.py

Objetivo:
- Hacer que get_by_chunk_ids pueda recuperar el vector real si OpenSearch lo devuelve.
- Permitir que PositioningCandidate tenga embedding.
- Calcular embedding de grupo como promedio ponderado por cross_encoder_score.
- Usar similitud coseno entre grupos si ambos tienen embeddings.
- Mantener fallback actual por conceptos/texto si no hay embeddings.

No rompas MMR V1.
Agrega tests unitarios con embeddings fake.
No dependas de OpenSearch real.
```

### Criterio de revision

Aceptar si los embeddings son opcionales y el fallback sigue funcionando.

## Fase 18: Mejor soporte multilingue de conceptos

### Objetivo

Conectar `LEXICON_ES` al extractor o al modulo de cobertura.

### Importante

Hacer despues de V1. No bloquear la primera version.

### Prompt para Codex

```text
Mejora la cobertura de sintomas para soportar mejor consultas en espanol.

Revisa:
- src/sri_dx/modules/indexing/concepts/extractor.py
- src/sri_dx/modules/indexing/concepts/lexicon_en.py
- src/sri_dx/modules/indexing/concepts/lexicon_es.py
- src/sri_dx/modules/positioning/symptoms.py

Objetivo:
- Permitir extraer conceptos desde aliases en ingles y espanol.
- Mantener compatibilidad con el comportamiento actual.
- Agregar tests para disnea, falta de aire, dolor toracico, fiebre.

No toques el cross-encoder ni cambies modelos.
No reindexes nada en esta fase.
```

### Criterio de revision

Aceptar si no rompe extraccion en ingles.

## Orden recomendado de ejecucion

Orden minimo para una V1 funcional:

```text
0. Auditoria
1. Modelos/config
2. Adaptador
3. Normalizacion
4. Agrupacion
5. Cobertura
6. Autoridad
7. Frescura
8. Scoring multicriterio
9. MMR
10. Evidencias/explicaciones
11. Servicio principal
12. Integracion pipeline
14. CLI
16. Verificacion
```

Fases que pueden esperar:

```text
13. Metadata adicional
15. Streamlit
17. Embeddings para MMR
18. Multilingue
```

Aunque la fase 13 mejora mucho el resultado, se puede implementar antes o despues de la integracion inicial. Si se quiere una primera version mas fiel a frescura/secciones, hacer fase 13 antes de la 12.

## Recomendacion practica para reducir riesgo

La ruta mas segura es:

```text
0 -> 1 -> 2 -> 3 -> 4 -> 8 parcial -> 11
```

Con eso se puede tener un servicio minimo que agrupe y rankee por CE/hybrid sin frescura ni autoridad. Despues se agregan:

```text
5 -> 6 -> 7 -> 9 -> 10
```

Finalmente:

```text
12 -> 14 -> 15
```

Asi, si algo falla, se sabe exactamente en que capa ocurrio.

