# Indexing Module: Use Cases

La lógica de negocio que orquesta todo el proceso.

## IndexOpenSearchUseCase

Es el cerebro del proceso de indexación de documentos completos.

- **Ruta**: `src/sri_dx/usecases/index_opensearch.py`

### Algoritmo de Ejecución

1.  **Asegurar Infraestructura**: Llama a `sink.ensure_index()` para verificar que el índice y alias existan.
2.  **Iteración**: Recorre cada documento de la fuente (`source.iter_documents()`).
3.  **Filtrado Incremental**: Consulta el `manifest` para ver si el documento ya existe.
4.  **Preparación**: Genera `IndexDocument` normalizando texto y extrayendo metadatos.
5.  **Enriquecimiento**: Extrae conceptos médicos mediante `ConceptExtractor`.
6.  **Persistencia**: Envía el lote a OpenSearch en bloques (`bulk_upsert`).

## IndexChunksOpenSearchUseCase

Orquesta el proceso de fragmentación (chunking) y carga de trozos para búsqueda vectorial.

- **Ruta**: `src/sri_dx/usecases/index_chunks_opensearch.py`

### Algoritmo de Ejecución

1.  **Asegurar Infraestructura**: Verifica el índice `clinical_chunks_v1` y activa el soporte kNN.
2.  **Iteración**: Recorre documentos de la fuente.
3.  **Fragmentación (Chunking)**:
    - Divide el documento por secciones clínicas originales.
    - Para cada sección, aplica una ventana de caracteres con solapamiento ajustable.
    - Preserva trazabilidad: `doc_id`, `section_heading`, offsets.
4.  **Enriquecimiento**: Extrae conceptos sobre cada fragmento de forma individual.
5.  **Batching & Sink**: Envía los `ChunkDocument` al `OpenSearchChunksSink`.
