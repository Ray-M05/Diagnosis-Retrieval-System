# Indexing Module: Use Cases

La lógica de negocio que orquesta todo el proceso.

## IndexOpenSearchUseCase

Es el cerebro del proceso de indexación.

- **Ruta**: `src/sri_dx/usecases/index_opensearch.py`

### Algoritmo de Ejecución

1.  **Asegurar Infraestructura**: Llama a `sink.ensure_index()` para verificar que el índice y alias existan.
2.  **Iteración**: Recorre cada documento de la fuente (`source.iter_documents()`).
3.  **Filtrado Incremental**: Consulta el `manifest` para ver si el documento ya existe y si su `content_hash` es idéntico. Si coincide, se salta (`skipped`).
4.  **Preparación**:
    - Genera `IndexDocument` normalizando texto y extrayendo metadatos.
    - **Enriquecimiento**: Extrae conceptos médicos mediante `ConceptExtractor` (basado en Aho-Corasick y un lexicón local).
5.  **Batching**: Agrupa documentos en lotes (`batch_size`) para mayor eficiencia de red.
6.  **Persistencia**: Envía el lote a OpenSearch (`bulk_upsert`).
7.  **Actualización de Estado**: Si la carga fue exitosa, actualiza el `manifest` con el nuevo hash.
8.  **Reporte**: Al finalizar, genera un JSON en `data/index/reports/` con estadísticas globales.
