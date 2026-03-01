# Indexing Module: Adapters

Implementaciones concretas de infraestructura.

## JsonlDocumentSource

Lee archivos `.jsonl` (HTML o PDF procesado) desde el disco.

- **Ruta**: `src/sri_dx/adapters/document_sources/jsonl_source.py`

## SqliteManifestStore

Implementa la incrementalidad usando una base de datos SQLite local. Esto evita re-procesar documentos cuyo hash y versión de tubería no han cambiado.

- **Ruta**: `src/sri_dx/adapters/stores/sqlite_manifest.py`

## OpenSearchIndexSink

El adaptador principal para el motor de búsqueda.

- **Ruta**: `src/sri_dx/adapters/stores/opensearch_sink.py`
- **Responsabilidades**:
  - Crear el índice con el mapping correcto (`opensearch_schema.py`).
  - Gestionar alias (ej: apuntar `clinical_docs` al índice versionado actual).
  - Ejecutar operaciones `bulk_upsert` para máxima velocidad.
