# Testing de expansion y feedback

## Prueba manual

1. Levantar backend y frontend.
2. Buscar una query, por ejemplo `fever cough`.
3. Marcar una o mas cards como relevantes y alguna como no relevante.
4. Presionar `Refinar`.
5. Verificar:
   - aparece `Consulta refinada` si se agregaron terminos;
   - los resultados cambian;
   - los botones no conservan marcas por posicion;
   - los chunks no relevantes no vuelven en el refinamiento.

Para probar PRF automatico:

```powershell
$env:SRI_ENABLE_PRF="true"
# reiniciar backend
```

Luego repetir la busqueda y comparar ranking/expansion contra el modo normal. Para volver al comportamiento base:

```powershell
Remove-Item Env:SRI_ENABLE_PRF
# reiniciar backend
```

## Prueba por API

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/feedback/relevance `
  -ContentType "application/json" `
  -Body '{"session_id":"manual-1","query":"fever cough","chunk_id":"CHUNK_ID","doc_id":"DOC_ID","relevant":true}'

Invoke-RestMethod -Method Post http://127.0.0.1:8000/feedback/search/refine `
  -ContentType "application/json" `
  -Body '{"session_id":"manual-1","query":"fever cough","k":10}'
```

Usar IDs reales devueltos por `/pipeline`.

## Tests automatizados

Unitarios principales:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/modules/test_expansion_feedback.py
.\.venv\Scripts\python.exe -m pytest tests/unit/usecases/test_two_stage_expansion.py
```

Si pytest falla por permisos de cache/temp en Windows:

```powershell
$env:TMP="C:\tmp"
$env:TEMP="C:\tmp"
.\.venv\Scripts\python.exe -m pytest tests/unit/modules/test_expansion_feedback.py -o cache_dir=C:\tmp\pytest-cache
```

## Casos esperados

- Sinonimos: `shortness of breath` agrega `dyspnea`.
- PRF: agrega terminos frecuentes de los top docs solo si `SRI_ENABLE_PRF=true`.
- Feedback textual: agrega terminos de chunks relevantes.
- Feedback negativo: excluye `chunk_id` marcados como no relevantes durante refine.

