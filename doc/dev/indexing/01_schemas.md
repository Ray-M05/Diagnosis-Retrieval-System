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

## ManifestEntry

Entrada mínima para el seguimiento de la incrementalidad.

- **Ruta**: `src/sri_dx/core/ports/manifest_store.py`
- **Campos**: `doc_id`, `content_hash`, `pipeline_version`.
