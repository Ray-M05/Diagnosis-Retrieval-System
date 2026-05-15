# Busqueda web y enriquecimiento

## Objetivo

El modulo decide si la busqueda local es insuficiente y, si hace falta, consulta fuentes externas, indexa documentos nuevos y vuelve a rankear contra el indice enriquecido.

Fuentes actuales:

- MedlinePlus
- Europe PMC
- PubMed

## En que consiste

La busqueda web no reemplaza la busqueda local. Es un paso de enriquecimiento:

- Evalua si el ranking local tiene evidencia suficiente.
- Si no alcanza, consulta APIs medicas externas.
- Convierte esos documentos al formato interno de adquisicion.
- Deduplica contra lo ya indexado.
- Indexa solo documentos nuevos.
- Ejecuta nuevamente el retrieval sobre el indice actualizado.

La decision de insuficiencia se calcula sobre los resultados que el buscador local recupera, no sobre todos los documentos del indice. Eso mide si el sistema puede traer evidencia util para esa query.

## Suficiencia local

`LocalSufficiencyEvaluator` usa cuatro criterios:

- `rank_confidence`: score normalizado del primer resultado.
- `useful_count`: cantidad de documentos distintos con score util.
- `symptom_coverage`: sintomas de la query presentes en los textos recuperados.
- `source_diversity`: cantidad de dominios distintos entre documentos utiles.

Si fallan criterios y el score compuesto supera el umbral, se recomienda busqueda web.

## Deduplicado e indexado

El deduplicador filtra documentos repetidos por:

- PMID, PMCID o DOI;
- URL canonica;
- `doc_id`;
- `content_hash` del cuerpo limpio.

Tambien consulta OpenSearch antes de indexar. Por eso puede pasar que las APIs recuperen documentos, pero `docs_added=0`: eran duplicados o ya estaban en la base.

## Componentes backend

- `src/sri_dx/modules/web_search/sufficiency.py`: evalua suficiencia local.
- `src/sri_dx/usecases/web_search/search_web_and_enrich.py`: orquesta busqueda web, deduplicado, delta, indexado y re-ranking.
- `src/sri_dx/modules/web_search/converters.py`: convierte documentos externos a formato adquirido.
- `src/sri_dx/modules/web_search/deduplicator.py`: deduplica por PMID/PMCID/DOI, URL, `doc_id` y `content_hash`.
- `src/sri_dx/modules/web_search/delta_writer.py`: escribe JSONL incremental.
- `src/sri_dx/app/api/main.py`: activa el caso de uso desde `POST /pipeline` con `stages.web_enrichment=true`.

## Flujo

1. Ejecuta busqueda local con al menos 20 resultados para evaluar suficiencia.
2. Calcula:
   - confianza del ranking;
   - cantidad de documentos utiles;
   - cobertura de sintomas;
   - diversidad de fuentes.
3. Si es suficiente, no consulta APIs.
4. Si es insuficiente, consulta APIs medicas.
5. Convierte y limpia documentos.
6. Deduplica contra la sesion y contra OpenSearch.
7. Escribe delta JSONL e indexa docs/chunks nuevos.
8. Vuelve a ejecutar retrieval y devuelve ranking con titulos, enlaces y fuente.

Importante: que el modulo recomiende busqueda web no garantiza documentos nuevos. Puede ocurrir que las APIs devuelvan documentos ya indexados o ningun candidato util.

## Configuracion

`src/sri_dx/core/config.py` define:

- `web_search.enabled`
- `retmax_medlineplus`
- `retmax_europe_pmc`
- `retmax_pubmed`
- `delta_dir`
- `report_dir`
- umbrales de `sufficiency`

El endpoint usa indices desde variables `SRI_*` u `OPENSEARCH_*`.

## Integracion frontend

- `frontend/src/api/client.ts`: `runPipeline` envia `stages.web_enrichment`.
- `frontend/src/components/SearchBar.tsx`: modo visual web.
- `frontend/src/components/InsufficiencyBanner.tsx`: aparece cuando la busqueda normal es insuficiente.
- `frontend/src/views/SymptomSearchView.tsx`: al activar modo web llama `/pipeline` con `web_enrichment=true` y muestra resumen.
- `frontend/src/views/ResearchView/index.tsx` y `ClinicalRAGView.tsx`: tambien consumen `sufficiency` y `web_enriched`.

Flujo visual:

1. Busqueda normal muestra resultados.
2. Si `sufficiency.sufficient=false`, aparece banner sugiriendo busqueda web.
3. El usuario activa web.
4. Se muestra estado de carga `Buscando en fuentes web...`.
5. Se renderiza ranking final y banner con recuperados/indexados.
