# Web Search Orchestrator - Resumen y Funcionamiento

El módulo de **Web Search** (`src/sri_dx/usecases/web_search/`) tiene como objetivo aumentar la robustez del sistema de recuperación de diagnósticos, consultando fuentes externas de autoridad médica (PubMed, MedlinePlus, EuropePMC) únicamente cuando la base de datos local no es capaz de satisfacer la consulta del usuario.

## Flujo de Trabajo (Pipeline)

El orquestador (`SearchWebAndEnrichUseCase`) ejecuta un flujo dividido en 7 fases:

1. **Recuperación Local Inicial (Stage 1)**
   Se ejecuta una búsqueda en dos etapas (Híbrida + Cross-Encoder) en el índice local de OpenSearch. Se obtienen los mejores documentos (candidatos locales).

2. **Evaluación de Suficiencia (Stage 2)**
   Los resultados locales son evaluados por el `LocalSufficiencyEvaluator`. Si los documentos locales cumplen con estrictos criterios de calidad, el flujo se detiene y se devuelven los resultados al usuario.
   Los criterios evaluados son:
   - `rank_confidence`: El score del modelo (Cross-Encoder) debe ser alto (> 55% de confianza).
   - `useful_document_count`: Debe haber un mínimo de documentos útiles (score positivo).
   - `source_diversity`: Los documentos útiles deben provenir de al menos 2 dominios distintos.
   - `symptom_coverage`: El texto de los documentos debe cubrir los síntomas consultados.

3. **Búsqueda en APIs Externas (Stage 3)**
   Si la evaluación de suficiencia determina que los resultados son insuficientes (falla algún criterio), se dispara la búsqueda web. El sistema extrae los síntomas de la consulta y lanza peticiones concurrentes a las APIs configuradas (MedlinePlus, PubMed, EuropePMC).

4. **Conversión y Deduplicación (Stage 4)**
   Los documentos descargados (`ExternalApiDocument`) se convierten al formato del sistema (`AcquiredDocument`). El `ApiDocumentDeduplicator` filtra aquellos documentos que ya existan en la sesión actual o que ya hayan sido indexados localmente (verificando `content_hash`, `URL`, y `PMID/DOI`).

5. **Guardado de Reportes y Deltas (Stage 5)**
   Los documentos nuevos se guardan en un archivo `.jsonl` temporal (Delta) en el disco, y se genera un reporte JSON detallado de la ejecución.

6. **Indexación Combinada (Stage 6)**
   Se ejecuta el `IndexCombinedUseCase`, el cual lee el Delta generado, trocea los documentos usando el `SemanticChunker`, genera los embeddings (usando ClinicalBERT u otro modelo) y los inserta en OpenSearch de forma persistente.

7. **Re-evaluación Final (Stage 7)**
   Una vez indexados los nuevos documentos, se vuelve a ejecutar la Recuperación Local Inicial (Stage 1) para obtener el ranking final, el cual ahora incluirá los documentos web recién asimilados si estos son más relevantes que los locales.

## Manejo de Datos y Limpieza
Para garantizar la calidad del indexado, el texto proveniente de las APIs web pasa por el módulo de limpieza (`cleaning.py`), el cual elimina caracteres anómalos, normaliza Unicode y **remueve etiquetas HTML** (`<p>`, `<span>`, etc.) asegurando que los embeddings se generen sobre texto médico puro.
