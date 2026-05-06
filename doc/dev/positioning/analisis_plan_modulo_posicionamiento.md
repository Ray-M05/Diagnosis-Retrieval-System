# Analisis del plan de implementacion del modulo de posicionamiento

Fecha de analisis: 2026-05-04

Documento base analizado: `doc/dev/positioning/informe_modulo_posicionamiento.md`

Codigo contrastado:

- `src/sri_dx/usecases/search/two_stage_retrieval_pipeline.py`
- `src/sri_dx/usecases/search/search_hybrid.py`
- `src/sri_dx/modules/ranking/disease_aggregator.py`
- `src/sri_dx/modules/ranking/fusion.py`
- `src/sri_dx/core/schemas/search/*`
- `src/sri_dx/modules/indexing/*`
- `src/sri_dx/adapters/stores/*`
- `src/sri_dx/app/ui/ui_streamlit.py`
- `src/sri_dx/app/cli/search_cli.py`

## 1. Resumen ejecutivo

El plan propuesto para el modulo de posicionamiento esta bien orientado conceptualmente: ubica el posicionamiento despues del recuperador hibrido y del cross-encoder, transforma chunks en resultados clinicos agrupados, incorpora explicabilidad y agrega una etapa de diversificacion con MMR. Esa direccion encaja con la arquitectura real del proyecto.

Sin embargo, el plan no esta completamente ajustado al estado actual de la implementacion. El sistema ya tiene una etapa parcial que cumple una parte del objetivo: `DiseaseAggregator`, invocado desde `TwoStageRetrievalPipeline.search_diseases`. Esa etapa ya agrupa chunks por enfermedades detectadas con NER on-demand, pero hoy es mucho mas simple que el modulo propuesto: no usa scoring multicriterio, no usa autoridad de fuente, no usa frescura, no usa cobertura de sintomas, no selecciona evidencia con criterios de seccion, no genera explicaciones y no aplica MMR.

Mi recomendacion principal es no implementar el modulo como una pieza aislada ni como un segundo agregador paralelo desconectado. Lo mas sano es convertir el posicionamiento en una evolucion natural del flujo actual:

```text
SearchHybridUseCase
        ↓
TwoStageRetrievalPipeline.search()
        ↓
NER on-demand sobre chunks rerankeados
        ↓
ClinicalPositioningService
        ↓
PositionedClinicalResult
        ↓
CLI / Streamlit / futuro RAG
```

En otras palabras: el nuevo modulo debe reemplazar gradualmente la responsabilidad de `DiseaseAggregator`, o envolverla al principio, pero no duplicar indefinidamente dos formas de "ranking por enfermedad".

Las metricas abstractas se pueden construir, pero con una advertencia importante: algunas senales que el plan asume no estan siempre disponibles en los resultados actuales. En particular:

- `fetched_at` existe en el indice de chunks, pero `SearchHybridUseCase` no lo copia a la metadata que llega al reranker.
- `title` existe en documentos completos, pero no se preserva en `ChunkDocument` ni en el indice de chunks.
- `published_at` y `updated_at` existen en documentos completos, pero no en chunks.
- Los embeddings reales no llegan en los resultados de busqueda semantica, y `OpenSearchEmbeddingSink.get_by_chunk_ids()` hoy no pide el campo `vector` en `_source`, aunque despues intenta leerlo.
- `ConceptExtractor` tiene lexicon en ingles y existe un lexicon espanol, pero el extractor actual solo importa `LEXICON_EN`.
- `DiseaseAggregator` documenta un ranking ponderado por `rerank_score * ner_confidence`, pero el codigo actual realmente ordena por la mejor posicion del cross-encoder y asigna `combined_score=ner_score`.

Por tanto, el plan es viable, pero necesita una fase previa de alineacion de contratos y metadata. Esa fase es pequena y de alto valor: enriquecer los resultados recuperados con los campos que ya existen en OpenSearch, definir esquemas de salida adecuados y decidir como extraer la "condicion clinica" de cada grupo.

## 2. Como esta hoy el sistema

### 2.1 Acquisition

El modulo de adquisicion genera documentos con una estructura util para posicionamiento:

- `doc_id`
- `url`
- `source_domain`
- `fetched_at`
- `content.title`
- `content.sections`
- `content.body`
- `page_meta.published_at`
- `page_meta.updated_at`
- `page_meta.language`
- `crawl.seed_group`

Esto significa que la materia prima para autoridad, frescura, trazabilidad y agrupacion existe desde el origen. El problema no esta en adquisicion, sino en cuanto de esa informacion sobrevive hasta el resultado recuperado.

### 2.2 Indexing

El sistema usa una estrategia de doble indice:

- Indice de documentos completos: `clinical_docs`.
- Indice de chunks: `clinical_chunks`.
- Indice separado de embeddings: `clinical_embeddings_v1`.

El indice de documentos completos contiene campos utiles para frescura clinica:

- `published_at`
- `updated_at`
- `fetched_at`
- `title`
- `source_domain`
- `url`

El indice de chunks contiene:

- `chunk_id`
- `doc_id`
- `url`
- `source_domain`
- `fetched_at`
- `section_heading`
- `section_index`
- `chunk_index`
- `chunk_text`
- `language`
- `concept_ids`
- `ner_entities`
- `embedding`

El detalle clave: los chunks no tienen `title`, `published_at` ni `updated_at`. Para una primera version del posicionamiento se puede vivir sin eso, pero conviene corregirlo porque el plan propone usar el titulo como fallback de enfermedad y usar frescura del contenido, no solo frescura de adquisicion.

### 2.3 Hybrid retrieval

`SearchHybridUseCase` hace:

```text
query
  → busqueda lexical
  → busqueda semantica
  → fusion RRF o weighted_sum
  → reranking opcional
```

En el flujo usado por `TwoStageRetrievalPipeline`, el reranking se hace fuera de `SearchHybridUseCase`, asi:

```text
SearchHybridUseCase(use_reranking=False)
  → TwoStageRetrievalPipeline.search()
  → SentenceTransformersCrossEncoderAdapter.rerank()
```

Esto esta bien: evita doble reranking y deja un punto claro para insertar posicionamiento despues.

La busqueda lexical arma metadata con:

- `chunk_id`
- `doc_id`
- `url`
- `title`
- `source_domain`
- `mime_type`
- `concept_ids`
- `ner_entities`
- `chunk_text`
- `content`

Pero no incluye `fetched_at` ni `section_heading`, aunque el backend lexical si recibe `fetched_at` y el indice de chunks tiene `section_heading`.

La busqueda semantica arma metadata con:

- `chunk_id`
- `doc_id`
- `chunk_text_preview`
- `content`
- `section_heading`
- `source_domain`
- `seed_group`

Pero no incluye:

- `url`
- `title`
- `fetched_at`
- `concept_ids`
- `ner_entities`
- `chunk_text` completo

Cuando un chunk aparece tanto en lexical como en semantica, la fusion combina ambas metadata. Cuando aparece solo en semantica, llega con metadata incompleta. Esto afecta directamente autoridad, frescura, evidencias y explicabilidad.

### 2.4 Cross-encoder

`TwoStageRetrievalPipeline.search()` recibe candidatos hibridos y aplica un cross-encoder sobre el campo `content`. Luego devuelve `RetrievalResult` con:

- `doc_id`
- `rerank_score`
- `original_hybrid_score`
- `lexical_score`
- `vector_score`
- `original_position`
- `final_position`
- `metadata`
- `content`

Esto es una buena entrada para el modulo de posicionamiento. No hace falta cambiar la busqueda desde cero. El nuevo modulo puede trabajar con estos `RetrievalResult`.

### 2.5 Agregacion por enfermedad actual

`search_diseases()` hace:

```text
search()
  → _apply_ner_to_results()
  → DiseaseAggregator.aggregate()
```

`DiseaseAggregator`:

- Lee `ner_entities` desde `metadata`.
- Filtra entidades con `label == "PROBLEM"`.
- Normaliza texto de enfermedad.
- Agrupa por nombre normalizado.
- Construye `DiseaseResult`.
- Ordena por la mejor posicion en el ranking del cross-encoder.

Esto ya resuelve una parte del plan: pasar de chunks a enfermedades. Pero todavia no resuelve posicionamiento clinico multicriterio.

Ademas, hay un desajuste entre comentario y codigo: el comentario superior dice que produce un ranking ponderado por `rerank_score × ner_confidence`, pero el codigo actualmente asigna `combined_score=ner_score` y `aggregated_score=float(best_position)`. En la practica, el orden depende de la primera aparicion en el ranking, no de una suma ponderada de evidencia.

## 3. Que tan ajustado esta el plan a la implementacion real

### 3.1 Partes que encajan bien

El plan acierta en colocar el modulo despues del recuperador hibrido y del reranker profundo. Esa decision encaja con `TwoStageRetrievalPipeline.search()`, que ya devuelve una lista enriquecida de chunks rerankeados.

Tambien encaja la idea de agrupar por condicion clinica. La UI ya tiene un modo "Diagnostico por Enfermedades", y el CLI ya tiene `--diseases`. El producto ya empezo a moverse hacia resultados agrupados, asi que el posicionamiento no seria una pieza forzada.

El algoritmo propuesto, "Clinical MMR Re-ranking", tambien es defendible academicamente:

- Usa señales de recuperacion existentes.
- Agrega señales clinicas interpretables.
- Evita resultados redundantes.
- Permite explicar por que una condicion aparece arriba.

La idea de dejar pesos configurables es correcta. En este proyecto, donde todavia no hay una coleccion de juicios de relevancia clinica, los pesos iniciales deben ser heuristicas ajustables, no valores rigidos.

### 3.2 Partes que necesitan adaptacion

El plan propone crear `RetrievedChunk`, `ClinicalGroup` y `PositionedClinicalResult`. Eso tiene sentido, pero no conviene ponerlos en una estructura generica tipo `src/positioning/`, porque el repo ya sigue una arquitectura clara:

```text
src/sri_dx/
  core/
  usecases/
  modules/
  adapters/
  app/
```

La ubicacion mas natural seria:

```text
src/sri_dx/core/schemas/search/positioning_result.py
src/sri_dx/modules/positioning/config.py
src/sri_dx/modules/positioning/models.py
src/sri_dx/modules/positioning/scoring.py
src/sri_dx/modules/positioning/mmr.py
src/sri_dx/modules/positioning/explanations.py
src/sri_dx/modules/positioning/service.py
```

Otra opcion es mantener todos los modelos en `modules/positioning/models.py` para una primera version, y solo promover a `core/schemas` cuando la UI, el CLI o una API externa necesiten contratos estables. Pero si el objetivo es que la interfaz consuma estos resultados pronto, yo prefiero crear el schema estable desde el inicio.

Tambien hay que adaptar la entrada. El plan habla de `RetrievedChunk`, pero lo que hoy produce el pipeline es `RetrievalResult`. Lo mas limpio es crear un adaptador interno:

```text
RetrievalResult → PositioningCandidate
```

Ese adaptador no debe vivir en el cross-encoder ni en el recuperador. Debe vivir en posicionamiento o en el use case de busqueda, porque su responsabilidad es traducir resultados recuperados a candidatos posicionables.

### 3.3 Partes que hoy no se pueden implementar tal cual

El plan asume `disease_name` disponible por chunk. Hoy no existe de forma estable.

Opciones disponibles:

1. Usar entidades NER `PROBLEM` detectadas on-demand sobre los chunks rerankeados.
2. Usar el titulo del documento como fallback.
3. Usar `doc_id` como ultimo fallback.
4. A futuro, normalizar con UMLS si se configura `UMLS_API_KEY`.

La opcion 1 es la mejor para continuidad con `DiseaseAggregator`, pero tiene riesgos:

- No todo `PROBLEM` es una enfermedad candidata. Puede ser un signo, un sindrome mal segmentado o una mencion generica.
- Un chunk puede mencionar varias enfermedades; si se duplica el chunk en varios grupos hay que controlar que no infle artificialmente la evidencia.
- Si el NER falla, el resultado desaparece aunque el chunk sea relevante.

Por eso, la agrupacion deberia ser hibrida:

```text
1. entidades PROBLEM normalizadas de alta confianza
2. si no hay entidad confiable, titulo canonico del documento
3. si no hay titulo, slug de URL
4. si no hay nada, doc_id
```

El plan tambien asume embeddings por chunk para MMR. Hoy la busqueda semantica usa embeddings, pero no los devuelve al pipeline. Y `get_by_chunk_ids()` no recupera el campo `vector`, aunque intenta construir `EmbeddingDocument.vector` desde `_source`. Por tanto, en V1 conviene implementar MMR sin embeddings, usando similitud de conceptos y texto. En V2 se puede enriquecer con vectores.

## 4. Propuesta de ajuste arquitectonico

### 4.1 No reemplazar el retrieval

El modulo de posicionamiento no debe tocar:

- La generacion de embeddings.
- El BM25.
- La fusion RRF.
- El cross-encoder.

Debe consumir su salida.

La frontera recomendada es:

```python
chunk_results = pipeline.search(query)
pipeline._apply_ner_to_results(chunk_results)
positioned = positioning_service.position(query, chunk_results)
```

Esto permite mantener intacto el recuperador y probar posicionamiento con fixtures en memoria.

### 4.2 Agregar un metodo nuevo antes de modificar `search_diseases`

Para no romper el flujo actual, recomiendo agregar un metodo nuevo:

```python
def search_positioned(
    self,
    query: str,
    hybrid_candidates: Optional[int] = None,
    final_results: Optional[int] = None,
    positioned_results: Optional[int] = None,
) -> list[PositionedClinicalResult]:
    ...
```

Despues se puede hacer que `search_diseases()` llame internamente al nuevo servicio, o mantener ambos durante una transicion corta.

### 4.3 Mantener `DiseaseAggregator` solo como compatibilidad

`DiseaseAggregator` puede quedar como:

- fallback simple;
- herramienta de pruebas;
- etapa temporal de extraccion de grupos;
- compatibilidad con CLI/UI actuales.

Pero el ranking final deberia moverse a `ClinicalPositioningService`.

## 5. Modelo de datos recomendado

El plan propone `RetrievedChunk`. Yo lo ajustaria a algo mas explicito para no confundirlo con los resultados crudos del retrieval.

### 5.1 PositioningCandidate

```python
@dataclass
class PositioningCandidate:
    chunk_id: str
    doc_id: str
    text: str

    title: str | None = None
    disease_names: list[str] = field(default_factory=list)
    url: str | None = None
    source_domain: str | None = None
    section_heading: str | None = None
    fetched_at: datetime | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    mime_type: str | None = None
    seed_group: str | None = None

    lexical_score: float | None = None
    vector_score: float | None = None
    hybrid_score: float | None = None
    cross_encoder_score: float | None = None

    concept_ids: list[str] = field(default_factory=list)
    ner_entities: list[dict] = field(default_factory=list)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

La diferencia con el plan es `disease_names` en plural. Esto importa porque un mismo chunk puede mencionar mas de una condicion. Para V1 se puede duplicar la evidencia en varios grupos, pero con una penalizacion o un limite para evitar que un chunk general contamine demasiadas enfermedades.

### 5.2 ClinicalGroup

```python
@dataclass
class ClinicalGroup:
    disease_name: str
    display_name: str
    evidences: list[PositioningCandidate]

    relevance_score: float = 0.0
    mmr_score: float = 0.0

    cross_encoder_score: float = 0.0
    hybrid_score: float = 0.0
    symptom_coverage_score: float = 0.0
    authority_score: float = 0.0
    freshness_score: float = 0.0
    evidence_density_score: float = 0.0

    matched_symptoms: list[str] = field(default_factory=list)
    source_domains: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
```

### 5.3 PositionedClinicalResult

```python
@dataclass
class PositionedClinicalResult:
    rank: int
    disease_name: str
    disease_name_display: str
    final_score: float
    relevance_label: str

    matched_symptoms: list[str]
    evidences: list[PositioningEvidence]
    explanation: list[str]
    source_domains: list[str]

    component_scores: dict[str, float]
```

`component_scores` no tiene que mostrarse siempre en UI, pero es muy util para depurar, ajustar pesos y defender academicamente el algoritmo.

## 6. Construccion de metricas abstractas

Esta es la parte mas importante del modulo. Las metricas deben ser:

- calculables con los datos actuales o con enriquecimientos pequenos;
- robustas ante campos faltantes;
- explicables;
- testeables con fixtures;
- configurables;
- no confundibles con probabilidad diagnostica.

### 6.1 Normalizacion de scores

Tenemos varias escalas:

- BM25: no acotado y dependiente del indice/query.
- Vector score: depende de OpenSearch y de la metrica configurada.
- RRF: valores pequenos, tipicamente alrededor de `1 / (k + rank)`.
- Cross-encoder: puede devolver logits no calibrados.

Para combinar señales, no se deben usar los valores crudos. Recomiendo normalizacion por lote de candidatos de una misma query.

Regla inicial:

```text
1. Para cada señal, recolectar valores disponibles.
2. Si el score parece logit de cross-encoder, aplicar sigmoid opcional.
3. Aplicar min-max por query.
4. Si todos los valores son iguales, devolver 1.0 para todos los candidatos con valor presente.
5. Si falta una señal en un candidato, usar 0.0 para esa señal, salvo que la metrica defina neutralidad.
```

Sobre el cross-encoder: muchos modelos MS MARCO devuelven scores no calibrados como probabilidades. La sigmoid ayuda a llevarlos a `[0,1]`, pero no garantiza calibracion clinica. En ranking, min-max por query suele ser suficiente. Para etiquetas absolutas "Alta/Media/Baja", en cambio, hay que tener cuidado: un `0.80` normalizado por query no significa probabilidad clinica alta.

Recomendacion practica:

```text
cross_encoder_norm = minmax(sigmoid(raw_ce) si raw_ce fuera de [0,1], si no raw_ce)
hybrid_norm = minmax(original_hybrid_score)
lexical_norm = minmax(lexical_score)
vector_norm = minmax(vector_score)
```

En la formula principal del plan se usa `RRF(g)`, no BM25 ni vector por separado. Como `original_hybrid_score` ya representa RRF o weighted sum segun la configuracion, la señal deberia llamarse `hybrid_score`, no siempre `rrf_score`.

Si `fusion_method == "rrf"`:

```text
hybrid_score = rrf_score normalizado
```

Si `fusion_method == "weighted_sum"`:

```text
hybrid_score = weighted_sum_score normalizado
```

En el nombre academico se puede seguir hablando de "score hibrido"; en el codigo conviene evitar asumir RRF si el sistema permite otro metodo.

### 6.2 Agregacion por grupo

El plan propone:

```text
GroupScore =
    0.70 * best_chunk_score
  + 0.20 * avg_top_3_chunk_scores
  + 0.10 * evidence_density
```

La idea es buena porque evita favorecer documentos largos por suma simple. Yo mantendria esta forma, con un ajuste: la densidad no debe depender solo de cantidad de chunks, sino de evidencia no redundante.

Version recomendada:

```text
aggregate_signal(scores, evidences) =
    0.70 * best_score
  + 0.20 * avg_top_3_scores
  + 0.10 * non_redundant_evidence_density
```

Donde:

```text
non_redundant_evidence_density =
    0.50 * capped_log(unique_chunks)
  + 0.30 * capped_log(unique_sections)
  + 0.20 * capped_log(unique_domains)
```

Para V1, si queremos mantenerlo mas simple:

```text
density = min(1.0, log(1 + unique_chunk_count) / log(1 + 5))
```

Usaria `5` como saturacion inicial, no `10`, porque mostrar cinco chunks sobre la misma condicion ya suele ser evidencia abundante para esta interfaz.

### 6.3 Cobertura de sintomas

La cobertura de sintomas es la metrica mas delicada, porque el sistema no tiene hoy un `symptom_extractor` formal. El plan propone substring matching y luego sinonimos. Eso sirve para una demo, pero es fragil:

- Puede hacer match parcial accidental.
- No maneja negaciones.
- No maneja idioma si la query esta en espanol.
- No diferencia sintomas del usuario vs sintomas mencionados como ausencia.
- No aprovecha `concept_ids`, que ya existen.

Recomendacion: construir cobertura con tres capas.

#### Capa A: conceptos clinicos existentes

El repo ya tiene `ConceptExtractor` y un lexicon con conceptos como:

- `DYSPNEA`
- `CHEST_PAIN`
- `FEVER`
- `TACHYCARDIA`
- `HYPERTENSION`
- `DIABETES`
- `HYPOXEMIA`

Durante indexacion, los chunks reciben `concept_ids`. Durante busqueda lexical, la query tambien se expande con conceptos. Por tanto, la forma mas consistente de medir cobertura es:

```text
query_concepts = ConceptExtractor.extract(query)
evidence_concepts = union(candidate.concept_ids for candidate in group.evidences)
concept_coverage = |query_concepts ∩ evidence_concepts| / |query_concepts|
```

Ventaja: esto ya captura sinonimos como:

```text
shortness of breath ≈ dyspnea ≈ breathlessness
```

Problema actual: `ConceptExtractor` solo importa `LEXICON_EN`; existe `LEXICON_ES`, pero no esta conectado. Si quieren soportar consultas en espanol, hay que corregir eso antes de confiar en esta metrica.

#### Capa B: NER de sintomas en la consulta

El adaptador `BiomedicalNERAdapter` mapea `Sign_symptom` a `SYMPTOM`. Se puede aplicar NER sobre la query para extraer sintomas del usuario:

```text
query_symptoms = NER(query) filtrando label == SYMPTOM
```

Luego se compara contra:

- entidades `SYMPTOM` en evidencias, si existen;
- texto normalizado de evidencias;
- conceptos equivalentes.

Esta capa es mas costosa que el lexicon, pero la query es corta. El costo es aceptable si el NER ya se carga para `search_diseases()`.

#### Capa C: fallback lexical con aliases

Si no hay conceptos ni NER confiable, usar matching textual normalizado con boundaries:

```text
surface_coverage = matched_query_terms / query_terms
```

Pero debe usar normalizacion compatible con `TextPipelineConfig` y no un `if symptom in combined_text` crudo.

#### Formula recomendada

Si hay conceptos:

```text
Coverage(g, q) =
    0.70 * concept_coverage
  + 0.30 * surface_or_ner_coverage
```

Si no hay conceptos pero hay sintomas NER:

```text
Coverage(g, q) = ner_symptom_coverage
```

Si no hay sintomas detectados:

```text
Coverage(g, q) = neutral_value
```

Aqui hay una decision importante. El plan devuelve `0.0` si no hay sintomas. Eso puede penalizar injustamente consultas que no son listas de sintomas, por ejemplo:

```text
diabetes insulin treatment
```

Mi recomendacion es:

```text
si no hay sintomas/conceptos detectados:
    coverage_score = 0.5
    o redistribuir el peso de coverage entre CE e hybrid
```

Para una primera version, lo mas simple es `0.5` neutral. Para una version mas limpia, el servicio puede normalizar dinamicamente pesos:

```text
si Coverage no es aplicable:
    quitar peso gamma y renormalizar los demas pesos
```

#### `matched_symptoms` para UI

No conviene mostrar `concept_ids` crudos. Para UI:

- si el match viene de aliases, mostrar el texto original de la query;
- si viene de NER, mostrar la entidad de la query;
- si viene de concepto, mapear `DYSPNEA` a una etiqueta legible como `shortness of breath`.

### 6.4 Autoridad de fuente

La autoridad de fuente se puede calcular desde `source_domain`, `seed_group`, `url` y tipo de adquisicion.

El plan propone una tabla:

```python
SOURCE_RELIABILITY = {
    "medlineplus.gov": 1.00,
    "cdc.gov": 0.95,
    "who.int": 0.95,
    "mayoclinic.org": 0.95,
    "nhs.uk": 0.90,
}
```

La idea esta bien, pero hay que hacerla configurable y normalizar dominios.

#### Normalizacion de dominio

Antes de buscar en la tabla:

```text
1. lowercase
2. quitar esquema si accidentalmente viene URL
3. quitar `www.`
4. quitar slash final
5. conservar dominio registrable o dominio completo segun tabla
```

Ejemplos:

```text
https://www.mayoclinic.org/foo → mayoclinic.org
www.nhs.uk → nhs.uk
medlineplus.gov/ → medlineplus.gov
```

#### Defaults recomendados

No todos los dominios desconocidos son malos. Si el crawler ya aplica whitelist de fuentes medicas, un dominio no listado puede ser razonablemente confiable.

Valores iniciales:

```text
dominio listado confiable: 0.90-1.00
dominio whitelist pero no listado: 0.70
dominio dinamico web no validado: 0.55
sin dominio o sin URL: 0.40
```

#### Autoridad de grupo

El plan propone usar `max(scores)`. Es defendible porque basta una evidencia de fuente fuerte para respaldar el grupo. Pero usar solo maximo puede esconder que el resto de evidencias son debiles.

Recomendacion:

```text
Authority(g) =
    0.75 * max_authority
  + 0.25 * avg_top_unique_domain_authority
```

Con esto, una fuente excelente ayuda mucho, pero varias fuentes confiables ayudan un poco mas.

Para V1, si queremos simplicidad:

```text
Authority(g) = max(authority(e) for e in evidences)
```

Pero se debe guardar en `component_scores` para depurar sesgos.

### 6.5 Frescura

La frescura es otra metrica delicada en salud. El plan acierta al darle poco peso (`0.05`). En medicina, mas nuevo no siempre es mejor; muchas paginas clinicas estables siguen siendo validas durante anos.

El problema principal es que hoy los chunks solo tienen `fetched_at`. Ese campo mide cuando nuestro crawler vio la pagina, no cuando el contenido medico fue actualizado. Si re-crawleamos mañana una pagina vieja, `fetched_at` pareceria fresco aunque el contenido no lo sea.

Orden recomendado de preferencia:

```text
1. updated_at
2. published_at
3. fetched_at
4. unknown
```

Hoy para chunks solo tenemos `fetched_at`. Por tanto:

- En V1, usar `fetched_at` como señal debil y neutral.
- En V2, propagar `published_at` y `updated_at` a chunks o enriquecer desde el indice de documentos por `doc_id`.

#### Funcion recomendada

En vez de cortes bruscos, usaria una curva con piso:

```text
Freshness(age_days) =
    floor + (1 - floor) * exp(-age_days / half_life_days)
```

Parametros iniciales:

```text
floor = 0.40
half_life_days = 730
unknown = 0.60
```

Interpretacion:

- contenido muy reciente se acerca a `1.0`;
- contenido de 2 anos queda aproximadamente en `0.62`;
- contenido muy antiguo no cae a cero, porque puede seguir siendo util;
- fecha desconocida queda neutral.

Para implementacion sencilla:

```text
0-180 dias: 1.00
181-365 dias: 0.85
1-2 anos: 0.70
2-5 anos: 0.55
>5 anos: 0.40
desconocido: 0.60
```

#### Frescura de grupo

No recomiendo usar solo `max`, porque una evidencia recien adquirida podria tapar contenido viejo. Tampoco recomiendo promedio simple, porque una condicion puede tener muchas evidencias antiguas y una actualizada muy relevante.

Recomendacion:

```text
Freshness(g) =
    0.70 * freshness(best_evidence_by_ce)
  + 0.30 * max_freshness_among_top_evidences
```

Si no queremos complicarlo en V1:

```text
Freshness(g) = max(freshness(e) for e in top_3_evidences)
```

Pero hay que documentar que con solo `fetched_at` esto es "frescura de adquisicion", no "frescura clinica".

### 6.6 Densidad de evidencia

La densidad no aparece en la formula principal del plan, pero si en la agregacion de scores. Conviene tratarla como una señal interna, no como una metrica visible principal.

Riesgo: favorecer documentos largos.

Mitigacion:

```text
unique_chunks por disease_name, con maximo por doc_id
unique_sections
unique_domains
```

Regla practica:

```text
Por cada grupo, no contar mas de 2 evidencias por doc_id para densidad.
```

Esto evita que una pagina larga sobre neumonia domine por tener muchos chunks.

### 6.7 Similitud para MMR

El plan propone embeddings promedio como opcion preferida. Conceptualmente esta bien, pero hoy no es lo mas directo con la implementacion.

Estado actual:

- La busqueda semantica devuelve score vectorial, pero no devuelve el vector.
- El indice de embeddings almacena `vector`.
- `OpenSearchEmbeddingSink.get_by_chunk_ids()` no incluye `vector` en `_source`, por lo que no puede devolverlo aunque el dataclass tenga el campo.

Recomendacion por fases:

#### V1: MMR sin embeddings

Usar una similitud combinada:

```text
Sim(g1, g2) =
    0.50 * concept_jaccard(g1, g2)
  + 0.30 * lexical_jaccard(top_evidence_texts)
  + 0.20 * source_overlap(g1, g2)
```

Donde:

```text
concept_jaccard = |concepts_g1 ∩ concepts_g2| / |concepts_g1 ∪ concepts_g2|
source_overlap = |domains_g1 ∩ domains_g2| / |domains_g1 ∪ domains_g2|
```

La similitud de fuente no debe ser demasiado alta, porque dos enfermedades distintas pueden venir de la misma fuente confiable. Por eso le daria peso bajo.

Tambien se puede incorporar similitud de nombres:

```text
si disease_name normalizado igual: 1.0
si alias normalizado por UMLS igual: 1.0
```

Pero si la agrupacion ya hizo bien su trabajo, esto casi no deberia activarse.

#### V2: MMR con embeddings

Para usar embeddings:

1. Modificar `OpenSearchEmbeddingSink.get_by_chunk_ids()` para incluir `"vector"` en `_source`.
2. Enriquecer candidatos top-N con vectores.
3. Calcular embedding de grupo como promedio ponderado por score del cross-encoder:

```text
group_embedding =
    weighted_average(candidate.embedding, weight=candidate.cross_encoder_score)
```

4. Usar coseno entre grupos.

El promedio ponderado es mejor que promedio simple porque la evidencia mas relevante para la query debe representar mas al grupo.

### 6.8 Etiquetas de relevancia

El plan propone:

```text
Alta >= 0.75
Media >= 0.50
Baja < 0.50
```

Esto esta bien para una demo, pero hay una trampa: si usamos min-max por query, el mejor resultado casi siempre tendera a valores altos aunque la query sea mala. Por eso, las etiquetas deben interpretarse como relevancia relativa dentro de la busqueda, no como certeza clinica.

Recomendacion:

```text
Alta: resultado con score alto y al menos dos señales fuertes
Media: resultado con score medio o una señal fuerte
Baja: resultado informativo pero debil
```

Ejemplo de condicion:

```text
Alta si:
    final_score >= 0.75
    y cross_encoder_score >= 0.65
    y (coverage >= 0.50 o authority >= 0.90)
```

Esto evita que una condicion suba solo por autoridad o solo por frescura.

### 6.9 Explicaciones

Las explicaciones deben salir de los componentes calculados, no de un LLM. Asi son trazables y consistentes.

Formato recomendado:

```text
- Alta similitud semantica entre la consulta y las evidencias recuperadas.
- Coincide con sintomas de la consulta: fever, cough, shortness of breath.
- Evidencia procedente de fuentes clinicas confiables: cdc.gov, mayoclinic.org.
- Se selecciono manteniendo diversidad respecto a otras condiciones recuperadas.
```

No deben decir:

```text
- Es el diagnostico mas probable.
- El paciente tiene neumonia.
```

## 7. Formula final recomendada

La formula del plan es:

```text
Rel(g, q) =
    alpha * CE(g, q)
  + beta * RRF(g)
  + gamma * Coverage(g, S)
  + delta * Authority(g)
  + epsilon * Freshness(g)
```

Yo la conservaria con dos ajustes:

1. Renombrar `RRF(g)` a `Hybrid(g)`, porque el sistema permite RRF y weighted sum.
2. Hacer que `Coverage` pueda ser no aplicable sin penalizar.

Formula recomendada:

```text
Rel(g, q) =
    w_ce * CE_group(g)
  + w_hybrid * Hybrid_group(g)
  + w_coverage * Coverage(g, q)
  + w_authority * Authority(g)
  + w_freshness * Freshness(g)
```

Pesos iniciales:

```text
w_ce = 0.45
w_hybrid = 0.20
w_coverage = 0.15
w_authority = 0.15
w_freshness = 0.05
```

Si `Coverage` no es aplicable:

```text
opcion A: Coverage = 0.5
opcion B: quitar w_coverage y renormalizar pesos
```

Mi recomendacion para V1 es opcion A por simplicidad. Para V2, opcion B.

MMR:

```text
MMR(g) = lambda * Rel(g, q) - (1 - lambda) * max Sim(g, selected)
```

Parametro inicial:

```text
lambda = 0.80
```

El plan propone `0.75`, que es razonable. Yo subiria a `0.80` en esta implementacion porque ya vamos a agrupar por enfermedad, lo cual elimina gran parte de la redundancia mas obvia. Si penalizamos demasiado similitud, podriamos separar artificialmente condiciones clinicamente relacionadas que conviene mostrar juntas.

## 8. Integracion concreta con los modulos existentes

### 8.1 Cambios minimos previos en retrieval metadata

Antes o durante la implementacion del posicionamiento, conviene hacer estos ajustes pequenos:

#### En `OpenSearchSearchBackend`

Agregar a `SearchHit` campos opcionales para:

- `section_heading`
- `section_index`
- `chunk_index`

El indice de chunks ya los tiene. El backend puede leerlos de `_source`.

#### En `SearchHybridUseCase._lexical_search`

Agregar a metadata:

```python
"fetched_at": hit.fetched_at,
"section_heading": hit.section_heading,
"section_index": hit.section_index,
"chunk_index": hit.chunk_index,
```

Si no se modifica `SearchHit`, al menos se puede recuperar desde `hit.metadata`, pero hoy `SearchHit` no tiene metadata generica. Lo mas limpio es ampliar el schema.

#### En `OpenSearchEmbeddingSink.search_similar`

Agregar a `_source`:

- `url` si se desnormaliza al indice de embeddings;
- `fetched_at` si se desnormaliza;
- `concept_ids`;
- opcionalmente `chunk_hash`.

Pero hoy el indice de embeddings no almacena `url` ni `fetched_at`. Hay dos caminos:

1. Desnormalizar mas metadata al crear embeddings.
2. Enriquecer semantic-only hits leyendo `clinical_chunks` por `chunk_id`.

Para V1, recomiendo camino 2 porque evita reindexar embeddings.

#### En `OpenSearchChunkReader`

Ya existe `get_chunks_by_ids()`. Se puede usar para enriquecer candidatos semanticos con:

- `url`
- `fetched_at`
- `mime_type`
- `section_heading`
- `concept_ids`
- `chunk_text` completo

Esto tiene un costo adicional, pero solo para top-K candidatos, no para todo el corpus.

### 8.2 Integracion con NER

Hoy `TwoStageRetrievalPipeline._apply_ner_to_results()` ya aplica NER en batch y pone `ner_entities` en metadata.

El posicionamiento puede reutilizar eso. No conviene cargar otro NER dentro de `ClinicalPositioningService` si el pipeline ya lo hizo.

Recomendacion:

```text
TwoStageRetrievalPipeline:
    - responsable de ejecutar NER on-demand si el modo necesita enfermedades/posicionamiento

ClinicalPositioningService:
    - responsable de leer ner_entities y agrupar
```

Para query symptoms, el servicio podria recibir `symptoms` ya extraidos. Si no se le pasan, puede usar `ConceptExtractor` como fallback ligero. Pero la carga pesada del NER sobre la query deberia ser opcional/configurable.

### 8.3 Integracion con `DiseaseAggregator`

Opciones:

#### Opcion A: reemplazo gradual

Crear `ClinicalPositioningService` y hacer:

```python
def search_positioned(...):
    results = self.search(...)
    self._apply_ner_to_results(results)
    return self.positioning_service.position(query, results)
```

Mantener `search_diseases()` sin cambios por ahora.

Ventaja: cero ruptura.

#### Opcion B: `DiseaseAggregator` como helper

Modificar `DiseaseAggregator` para devolver grupos intermedios en vez de resultados finales, y que `ClinicalPositioningService` calcule scores.

Ventaja: reutiliza normalizacion de enfermedades.

Desventaja: `DiseaseAggregator` actual esta acoplado a `DiseaseResult`, que no tiene suficientes campos.

#### Opcion C: reemplazar `DiseaseAggregator`

Implementar todo en posicionamiento y cambiar `search_diseases()` para devolver resultados posicionados.

Ventaja: arquitectura limpia.

Desventaja: rompe UI/CLI actuales si esperan `DiseaseResult`.

Recomiendo Opcion A para empezar.

### 8.4 Integracion con CLI

El CLI ya tiene:

```text
--diseases
--max-diseases
--min-ner-score
```

Agregar:

```text
--positioned
--lambda-mmr
--authority-config
--show-component-scores
```

O mas simple:

```text
--diseases --positioning clinical-mmr
```

Para una primera version, `--diseases` puede seguir usando el agregador actual y `--positioned` usar el nuevo modulo. Cuando el nuevo flujo este validado, `--diseases` puede apuntar al posicionamiento.

### 8.5 Integracion con Streamlit

La UI Streamlit ya tiene dos modos:

- "Hibrido + Reranking"
- "Diagnostico por Enfermedades"

Se puede agregar un tercer modo o reemplazar el segundo:

```text
Condiciones posicionadas
```

Campos a mostrar:

- ranking;
- nombre de condicion;
- etiqueta de relevancia;
- score final opcional;
- sintomas coincidentes;
- explicacion;
- fuentes;
- evidencias principales;
- scores por componente en un expander de debug.

Importante: mantener el texto de seguridad medica. El resultado no debe llamarse "diagnostico", sino "condiciones clinicas asociadas" o "resultados para diagnostico diferencial".

### 8.6 Integracion con RAG

El modulo `modules/rag` esta practicamente vacio. Cuando se implemente RAG, el posicionamiento deberia ser la entrada natural del constructor de contexto:

```text
top N PositionedClinicalResult
  → top M evidencias por condicion
  → contexto estructurado
  → respuesta generada
```

Esto evita que el generador reciba diez chunks de la misma enfermedad y mejora la trazabilidad.

Formato de contexto sugerido:

```text
Condition: Pneumonia
Relevance: Alta
Matched symptoms: fever, cough, shortness of breath
Source: https://...
Evidence: ...

Condition: COVID-19
...
```

El RAG debe citar fuentes por evidencia, no solo por condicion.

### 8.7 Integracion con busqueda web

`modules/web_search` esta vacio. El plan menciona busqueda web dinamica, pero eso no existe aun.

Cuando exista, recomiendo no mezclar resultados web dinamicos sin pasar por contratos de adquisicion/indexacion. Deben convertirse en el mismo formato:

- `doc_id`
- `chunk_id`
- `url`
- `source_domain`
- `fetched_at`
- `source_type`
- `chunk_text`
- `section_heading`
- `concept_ids`
- `ner_entities`

Entonces el posicionamiento no necesita saber si la evidencia viene del corpus local o de busqueda web. Solo puede ajustar autoridad y frescura usando:

```text
source_type = "indexed_corpus" | "web_dynamic"
```

Para `web_dynamic`, usaria menor autoridad por defecto hasta validar dominio.

## 9. Orden de implementacion recomendado

### Fase 0: Preparar contratos de metadata

Objetivo: que los candidatos tengan suficiente informacion para posicionamiento.

Tareas:

1. Agregar `fetched_at` a metadata lexical en `SearchHybridUseCase._lexical_search`.
2. Agregar `section_heading` a `SearchHit` y `OpenSearchSearchBackend`, o resolverlo por enriquecimiento desde chunks.
3. Crear un helper para enriquecer resultados por `chunk_id` usando `OpenSearchChunkReader.get_chunks_by_ids()`.
4. Decidir si `title`, `published_at` y `updated_at` se propagan a chunks o se consultan desde docs por `doc_id`.

Resultado esperado:

```text
RetrievalResult.metadata contiene lo suficiente para:
  - autoridad
  - frescura basica
  - seccion
  - conceptos
  - URL
  - fuente
```

### Fase 1: Crear modelos y servicio de posicionamiento

Archivos sugeridos:

```text
src/sri_dx/modules/positioning/__init__.py
src/sri_dx/modules/positioning/models.py
src/sri_dx/modules/positioning/config.py
src/sri_dx/modules/positioning/scoring.py
src/sri_dx/modules/positioning/mmr.py
src/sri_dx/modules/positioning/explanations.py
src/sri_dx/modules/positioning/service.py
```

Si quieren contratos de salida estables:

```text
src/sri_dx/core/schemas/search/positioning_result.py
```

### Fase 2: Adaptador `RetrievalResult → PositioningCandidate`

Implementar una funcion pura:

```python
def candidates_from_retrieval_results(results: list[RetrievalResult]) -> list[PositioningCandidate]:
    ...
```

Reglas:

- `text = result.content or metadata["content"] or metadata["chunk_text"] or metadata["chunk_text_preview"]`
- `chunk_id = metadata["chunk_id"] or result.doc_id`
- `doc_id = result.doc_id`
- `cross_encoder_score = result.rerank_score`
- `hybrid_score = result.original_hybrid_score`
- `lexical_score = result.lexical_score`
- `vector_score = result.vector_score`
- `source_domain = metadata["source_domain"]`
- `url = metadata["url"]`
- `section_heading = metadata["section_heading"]`
- `fetched_at = metadata["fetched_at"]`
- `concept_ids = metadata["concept_ids"]`
- `ner_entities = metadata["ner_entities"]`

### Fase 3: Agrupacion clinica

Implementar:

```python
def group_candidates(candidates, normalizer=None) -> list[ClinicalGroup]:
    ...
```

Reglas:

1. Extraer disease candidates desde `ner_entities` con `label == "PROBLEM"` y score >= umbral.
2. Normalizar nombre con logica local de `DiseaseAggregator._normalize`.
3. Si existe normalizer UMLS, aplicarlo.
4. Si no hay enfermedad, fallback a titulo/slug/doc_id.
5. Evitar que un mismo chunk aparezca en demasiados grupos. Limite sugerido: maximo 3 enfermedades por chunk, priorizadas por score NER.

### Fase 4: Scoring multicriterio

Implementar funciones puras:

```python
normalize_scores(candidates)
aggregate_group_signal(scores, evidences)
compute_symptom_coverage(query, group)
compute_authority(group)
compute_freshness(group, reference_date)
compute_relevance(group, weights)
```

Cada una debe tener tests unitarios.

### Fase 5: MMR

Implementar MMR sobre `ClinicalGroup`.

En V1:

```text
group_similarity = concept_jaccard + lexical_jaccard + source_overlap
```

En V2:

```text
group_similarity = cosine(group_embedding)
```

### Fase 6: Seleccion de evidencias

Reglas iniciales:

```text
1. Ordenar evidencias por display_score.
2. Limitar a top 3.
3. Evitar textos casi duplicados.
4. Preferir secciones utiles.
5. Preferir URL presente y fuente confiable.
```

Secciones preferidas:

```text
symptoms: 1.00
signs and symptoms: 1.00
overview: 0.95
causes: 0.90
diagnosis: 0.90
treatment: 0.75
main: 0.70
```

`section_heading` debe normalizarse porque las fuentes pueden usar variantes.

### Fase 7: Explicaciones y etiquetas

Generar explicaciones deterministicas desde thresholds.

Guardar:

```text
component_scores
matched_symptoms
source_domains
selected_evidences
```

### Fase 8: Integracion CLI/UI

Agregar `search_positioned()` al pipeline.

CLI:

```text
uv run python -m sri_dx.app.cli.search_cli --type hybrid --positioned --q "fever cough shortness of breath"
```

Streamlit:

- Agregar modo "Condiciones posicionadas".
- Mostrar evidencias y explicaciones.

### Fase 9: Pruebas y calibracion

Crear pruebas unitarias antes de ajustar pesos.

## 10. Pruebas recomendadas

### 10.1 Unitarias de scoring

Casos:

- `minmax_normalize([])`.
- `minmax_normalize([5, 5, 5])`.
- cross-encoder con logits negativos y positivos.
- scores faltantes.
- agregacion con un solo chunk.
- agregacion con muchos chunks del mismo doc.
- densidad no crece indefinidamente.

### 10.2 Unitarias de cobertura

Casos:

- query `shortness of breath fever`.
- evidencia con `dyspnea` y `pyrexia`.
- evidencia sin sintomas.
- query sin sintomas detectables.
- query en espanol si se conecta `LEXICON_ES`.

### 10.3 Unitarias de autoridad

Casos:

- `www.mayoclinic.org`.
- dominio desconocido whitelist.
- sin dominio.
- multiples evidencias de dominios diferentes.

### 10.4 Unitarias de frescura

Casos:

- fecha reciente.
- fecha de hace 2 anos.
- fecha desconocida.
- `updated_at` presente.
- solo `fetched_at` presente.

El calculo debe recibir `reference_date` inyectable para que las pruebas no dependan del dia actual.

### 10.5 Unitarias de MMR

Construir tres grupos:

- A muy relevante sobre neumonia.
- B casi duplicado de A.
- C algo menos relevante pero diferente.

Con `lambda=0.75` o `0.80`, el segundo seleccionado deberia ser C si la redundancia de B es alta.

### 10.6 Integracion con pipeline

Usar fixtures de `RetrievalResult` sin cargar OpenSearch ni modelos:

- resultados con metadata lexical completa;
- resultados semantic-only con metadata incompleta;
- resultados sin NER;
- resultados con multiples entidades PROBLEM.

El objetivo es asegurar que el servicio degrade bien y no falle por campos faltantes.

## 11. Riesgos tecnicos y clinicos

### 11.1 Riesgo: agrupar sintomas como enfermedades

El NER puede clasificar entidades de forma imperfecta. Algunas condiciones o sintomas pueden aparecer como `PROBLEM`.

Mitigacion:

- Usar umbral NER configurable.
- Usar normalizador de enfermedades cuando este disponible.
- Penalizar nombres demasiado genericos.
- Excluir entidades que coinciden exactamente con sintomas de la query si no parecen enfermedad.

### 11.2 Riesgo: frescura mal interpretada

`fetched_at` no es fecha de actualizacion clinica.

Mitigacion:

- Peso bajo.
- Preferir `updated_at/published_at` cuando existan.
- Nombrar internamente `content_date` vs `acquisition_date`.
- Explicar que frescura no implica mayor validez clinica.

### 11.3 Riesgo: autoridad como sesgo de fuente

Si autoridad pesa mucho, puede esconder resultados relevantes de fuentes menos conocidas.

Mitigacion:

- Peso moderado.
- Configuracion externa.
- Auditoria de `component_scores`.
- Default razonable para whitelist.

### 11.4 Riesgo: etiquetas absolutas engañosas

Por normalizacion min-max, una etiqueta "Alta" puede significar "alta dentro de esta busqueda", no certeza diagnostica.

Mitigacion:

- Texto UI claro: "relevancia informativa".
- Nunca "probabilidad diagnostica".
- Thresholds con multiples condiciones, no solo score final.

### 11.5 Riesgo: MMR o diversidad excesiva

Si MMR penaliza demasiado condiciones relacionadas, puede esconder diagnosticos diferenciales relevantes de la misma familia clinica.

Mitigacion:

- `lambda` inicial 0.80.
- Similitud moderada por conceptos.
- No penalizar en exceso solo por compartir fuente.

### 11.6 Riesgo: idioma

La UI sugiere consultas en ingles y el cross-encoder por defecto es MS MARCO en ingles. El repo tiene lexicon espanol, pero el extractor actual no lo usa.

Mitigacion:

- Documentar V1 como mejor soportado en ingles.
- Conectar `LEXICON_ES`.
- Considerar cross-encoder multilingue si se prioriza espanol.

## 12. Decision sobre pesos iniciales

Mantendria los pesos del plan para empezar:

```text
cross_encoder: 0.45
hybrid: 0.20
symptom_coverage: 0.15
authority: 0.15
freshness: 0.05
```

Razonamiento:

- El cross-encoder debe dominar porque evalua query y evidencia conjuntamente.
- El score hibrido preserva señales de recuperacion y evita que el reranker sea la unica fuente.
- La cobertura de sintomas aporta interpretabilidad clinica.
- La autoridad ayuda a ordenar fuentes medicas, pero no debe decidir sola.
- La frescura solo desempata.

Para consultas sin sintomas detectados:

```text
coverage = 0.5
```

O en V2:

```text
renormalizar pesos quitando coverage
```

## 13. Configuracion recomendada

Usar una clase Pydantic o dataclass:

```python
class PositioningConfig(BaseModel):
    top_k: int = 10
    top_evidences: int = 3
    lambda_mmr: float = 0.80
    min_ner_score: float = 0.50
    max_diseases_per_chunk: int = 3
    unknown_freshness_score: float = 0.60
    unknown_authority_score: float = 0.70
    dynamic_web_authority_score: float = 0.55

    weights: dict[str, float] = {
        "cross_encoder": 0.45,
        "hybrid": 0.20,
        "symptom_coverage": 0.15,
        "authority": 0.15,
        "freshness": 0.05,
    }
```

La tabla de autoridad deberia vivir en config:

```python
SOURCE_RELIABILITY = {
    "medlineplus.gov": 1.00,
    "cdc.gov": 0.95,
    "who.int": 0.95,
    "mayoclinic.org": 0.95,
    "nhs.uk": 0.90,
    "msdmanuals.com": 0.90,
}
```

## 14. Recomendacion final de implementacion

Implementaria el modulo de posicionamiento en este orden:

1. Crear `modules/positioning` con modelos, config y funciones puras.
2. Crear adaptador desde `RetrievalResult` a candidatos posicionables.
3. Reutilizar NER on-demand actual.
4. Implementar agrupacion por enfermedad basada en NER, con fallback a titulo/URL/doc_id.
5. Implementar scoring multicriterio con metadata disponible.
6. Implementar MMR V1 con conceptos/texto, sin embeddings.
7. Agregar `search_positioned()` al pipeline.
8. Agregar salida CLI.
9. Agregar render Streamlit.
10. Luego enriquecer metadata y usar embeddings para MMR V2.

Esta estrategia permite tener una primera version funcional sin reindexar todo el corpus, y deja claro que mejoras requieren cambios de metadata.

## 15. Veredicto sobre el plan original

El plan es adecuado como diseno de alto nivel y es defendible para el proyecto. Su mayor fortaleza es que no intenta reemplazar la recuperacion, sino convertir resultados recuperados en una presentacion clinica mas util.

Los ajustes necesarios son:

- Adaptar la estructura de archivos a `src/sri_dx`.
- Reutilizar `TwoStageRetrievalPipeline` y no crear un pipeline paralelo.
- Reconocer que ya existe `DiseaseAggregator` y decidir su transicion.
- No asumir `disease_name`, `title`, `updated_at`, `published_at` ni embeddings en cada candidato.
- Construir cobertura de sintomas sobre `ConceptExtractor`/NER, no solo substring.
- Tratar frescura como señal debil y distinguir `fetched_at` de actualizacion clinica.
- Guardar `component_scores` para trazabilidad y calibracion.
- Implementar MMR V1 con conceptos/texto y dejar embeddings para V2.

Con esos ajustes, el modulo puede integrarse de forma limpia con el trabajo ya hecho y aportar una mejora real: pasar de "top chunks" a "condiciones clinicas posicionadas, explicables, diversas y trazables".

