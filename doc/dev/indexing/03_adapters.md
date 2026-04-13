# Indexing Module: Adapters

Implementaciones concretas de infraestructura.

## JsonlDocumentSource

Lee archivos `.jsonl` (HTML o PDF procesado) desde el disco.

- **Ruta**: `src/sri_dx/adapters/document_sources/jsonl_source.py`

## SqliteManifestStore

Implementa la incrementalidad usando una base de datos SQLite local. Esto evita re-procesar documentos cuyo hash y versión de tubería no han cambiado.

- **Ruta**: `src/sri_dx/adapters/stores/sqlite_manifest.py`

## OpenSearchIndexSink

Adaptador para el índice de documentos completos (`clinical_docs`).

- **Ruta**: `src/sri_dx/adapters/stores/opensearch_sink.py`
- **Mapping**: `opensearch_schema.py`.

## OpenSearchChunksSink

Adaptador especializado en el índice de fragmentos (`clinical_chunks`).

- **Ruta**: `src/sri_dx/adapters/stores/opensearch_chunk_sink.py`
- **Mapping**: `opensearch_chunks_schema.py`.
- **Características**: Soporte para **kNN** (búsqueda por proximidad vectorial).
