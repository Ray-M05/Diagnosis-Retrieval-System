# Expansion y retroalimentacion

## Objetivo

El modulo mejora la busqueda local usando dos senales:

- Expansion automatica de query: agrega sinonimos clinicos locales y, opcionalmente, terminos por pseudo-relevance feedback.
- Retroalimentacion explicita: el usuario marca cards como relevantes/no relevantes y luego presiona `Refinar`.

## En que consiste

La expansion no cambia los documentos indexados; cambia la consulta que entra al retrieval.

- Sinonimos: `SynonymExpander` busca terminos clinicos conocidos en la query y agrega variantes locales. Ejemplo: `shortness of breath` puede agregar `dyspnea`.
- PRF: `SimplePseudoRelevanceFeedback` toma los primeros resultados recuperados, extrae terminos frecuentes de sus textos y agrega los mejores a la query. La idea es que los top docs iniciales dan pistas de vocabulario clinico relacionado.
- Feedback textual: `FeedbackTextualExpander` usa solo chunks marcados como relevantes por el usuario, extrae terminos frecuentes y los agrega a la query refinada.
- Feedback negativo: los chunks marcados como no relevantes se pasan como `excluded_chunk_ids` para que no vuelvan en la busqueda refinada.

El PRF es automatico y experimental. La retroalimentacion explicita es manual y mas controlada porque usa votos del usuario.

## Componentes backend

- `src/sri_dx/modules/expansion/`: expansion por sinonimos y PRF simple.
- `src/sri_dx/modules/feedback/`: servicio de feedback y expansion textual desde chunks relevantes.
- `src/sri_dx/adapters/stores/sqlite_feedback_store.py`: persiste feedback y expansiones en SQLite.
- `src/sri_dx/app/api/feedback.py`: endpoints `POST /feedback/relevance` y `POST /feedback/search/refine`.
- `src/sri_dx/usecases/search/two_stage_retrieval_pipeline.py`: aplica expansion y filtra chunks marcados como no relevantes.

## Persistencia y sesion

La retroalimentacion se guarda en SQLite mediante `SqliteFeedbackStore`. Por defecto el backend crea la base en:

```text
data/feedback/feedback.sqlite
```

Se puede cambiar con:

```powershell
$env:SRI_FEEDBACK_DB="data/feedback/otro_feedback.sqlite"
```

El frontend crea un `session_id` por navegador usando `sessionStorage` en `useFeedback.ts`. Ese valor se manda en cada voto y en cada refinamiento. No es una sesion autenticada; es un identificador local para agrupar la interaccion del usuario mientras usa la UI.

Tablas:

- `relevance_feedback`: guarda cada voto.
  - `session_id`: sesion del navegador.
  - `query`: query exacta que produjo el resultado.
  - `chunk_id`: chunk votado.
  - `doc_id`: documento padre.
  - `relevant`: `1` para relevante, `0` para no relevante.
  - `created_at`: timestamp de insercion.
- `query_expansions`: guarda trazas de expansiones aplicadas.
  - `session_id`
  - `original_query`
  - `expanded_query`
  - `strategy`, por ejemplo `feedback_textual`.
  - `created_at`

Al refinar, el backend llama `get_feedback_for_session(session_id)` y luego filtra por `item["query"] == req.query`. Esto es importante: no mezcla votos de otra busqueda aunque pertenezcan a la misma sesion.

Uso de los datos durante refine:

- votos relevantes: se leen sus chunks desde OpenSearch y sus textos alimentan `FeedbackTextualExpander`;
- votos no relevantes: sus `chunk_id` pasan como `excluded_chunk_ids`;
- si la query refinada cambia, se guarda una fila en `query_expansions`;
- el ranking final se recalcula con `pipeline.search_diseases`.

## Configuracion

PRF esta desactivado por defecto:

```powershell
$env:SRI_ENABLE_PRF="true"
```

Reinicia el backend para activarlo. Para desactivarlo:

```powershell
Remove-Item Env:SRI_ENABLE_PRF
# o
$env:SRI_ENABLE_PRF="false"
```

La retroalimentacion explicita no depende de `SRI_ENABLE_PRF`; funciona mediante los endpoints `/feedback/*`.

## Flujo

1. El usuario busca sintomas en `/pipeline`.
2. Cada resultado trae `feedback_doc_id` y `feedback_chunk_id`.
3. El frontend envia cada voto a `/feedback/relevance`.
4. Al presionar `Refinar`, el frontend llama `/feedback/search/refine`.
5. El backend:
   - carga solo feedback de la misma `session_id` y misma query;
   - usa chunks relevantes para expandir texto;
   - excluye chunks no relevantes;
   - ejecuta `pipeline.search_diseases`;
   - devuelve un `PipelineResponse`.

En busqueda normal, el pipeline puede aplicar sinonimos y PRF antes del hybrid search. En `Refinar`, el endpoint de feedback construye una query nueva desde los votos y llama de nuevo a `search_diseases`.

## Integracion frontend

- `frontend/src/hooks/useFeedback.ts`: crea `session_id` en `sessionStorage`, envia votos y ejecuta refine.
- `frontend/src/components/feedback/RelevanceFeedbackButtons.tsx`: botones relevante/no relevante.
- `frontend/src/components/DiseaseCard.tsx`: muestra botones solo si hay IDs de feedback.
- `frontend/src/views/SymptomSearchView.tsx`: muestra el boton `Refinar` cuando hay feedback.

El estado visual de los botones se resetea por `targetId`, compuesto por query/doc/chunk. Esto evita que, al refinar, quede marcada la misma posicion visual aunque el documento haya cambiado.
