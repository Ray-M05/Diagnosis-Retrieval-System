# Indexing Module: Schemas

Modelos de datos compartidos que definen la estructura del sistema en el Core.

## AcquiredDocument

Representa el documento crudo tal como viene del módulo de adquisición/crawling.

- **Ruta**: `src/sri_dx/core/schemas/acquired_document.py`
- **Uso**: Entrada principal al proceso de indexación.

## IndexDocument

El documento listo para ser insertado en OpenSearch. Contiene campos normalizados y enriquecidos.

- **Ruta**: `src/sri_dx/core/schemas/index_document.py`
- **Campos Clave**:
  - `doc_id`: ID estable (slug o hash).
  - `content_hash`: Hash SHA256 del contenido para detectar duplicados.
  - `sections_text`: Texto plano de todas las secciones colapsado.
  - `word_count`, `char_len`: Estadísticas de texto.
  - `concept_ids`: Lista de conceptos médicos detectados (Fase D).

## ChunkDocument

Representa un fragmento (chunk) de un documento. Diseñado para trazabilidad y búsqueda vectorial.

- **Ruta**: `src/sri_dx/core/schemas/chunk_document.py`
- **Campos Clave**:
  - `chunk_id`: ID compuesto (`{doc_id}:{section_index}:{chunk_index}`).
  - `doc_id`: Referencia al documento padre.
  - `section_heading`: Título de la sección clínica de origen.
  - `chunk_text`: Contenido textual del fragmento.
  - `start_char`, `end_char`: Offsets dentro de la sección original.
  - `embedding`: Vector numérico (768 dimensiones por defecto) para búsqueda kNN.

## ManifestEntry

Entrada mínima para el seguimiento de la incrementalidad.

- **Ruta**: `src/sri_dx/core/ports/manifest_store.py`
- **Campos**: `doc_id`, `content_hash`, `pipeline_version`.
