# Testing de busqueda web

## Prueba manual desde frontend

1. Levantar OpenSearch, backend y frontend.
2. Buscar una query normal, por ejemplo `cough`.
3. Si aparece banner de insuficiencia, activar busqueda web.
4. Verificar:
   - no hay error `501`;
   - aparece el resumen de busqueda web;
   - los resultados muestran titulo, fuente y enlace cuando existen;
   - si no hay nuevos docs, el resumen distingue recuperados vs indexados.

## Prueba manual por API

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/pipeline `
  -ContentType "application/json" `
  -Body '{"query":"cough","k":10,"stages":{"web_enrichment":true,"positioning":false,"generation":false}}'
```

Campos clave en la respuesta:

- `web_enriched.triggered`
- `web_enriched.api_retrieved`
- `web_enriched.api_new_documents`
- `web_enriched.docs_added`
- `web_enriched.chunks_added`
- `hybrid[].name`
- `hybrid[].sourceUrl`

## Tests automatizados

Unitarios:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/modules/web_search
.\.venv\Scripts\python.exe -m pytest tests/unit/usecases/web_search/test_search_web_and_enrich.py
```

Integracion:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/web_search/test_web_search_flow.py
```

Si pytest falla por permisos de temp/cache en Windows:

```powershell
$env:TMP="C:\tmp"
$env:TEMP="C:\tmp"
.\.venv\Scripts\python.exe -m pytest tests/unit/modules/web_search -o cache_dir=C:\tmp\pytest-cache
```

## Casos esperados

- Resultados suficientes: `web_search_triggered=false`, no consulta APIs.
- Resultados insuficientes con docs nuevos: consulta APIs, escribe delta, indexa y re-rankea.
- Resultados insuficientes sin docs nuevos: consulta APIs, deduplica todo, re-rankea local y reporta `docs_added=0`.
- Duplicados: se filtran por identidad bibliografica, URL, `doc_id` o `content_hash`.
- Limpieza HTML: MedlinePlus no debe dejar tags como `<span>` en textos/titulos nuevos.

