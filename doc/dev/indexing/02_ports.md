# Indexing Module: Ports

Interfaces abstractas que definen el contrato entre la lógica de negocio y la infraestructura.

## DocumentSourcePort

Define cómo iterar sobre documentos adquiridos de una fuente externa.

- **Ruta**: `src/sri_dx/core/ports/document_source.py`
- **Método**: `iter_documents() -> Iterable[AcquiredDocument]`

## ManifestStorePort

Define cómo persistir y consultar el estado de indexación de un documento para lograr incrementalidad (Fase E).

- **Ruta**: `src/sri_dx/core/ports/manifest_store.py`
- **Métodos**:
  - `get(doc_id) -> Optional[ManifestEntry]`
  - `upsert_many(entries: Iterable[ManifestEntry])`

## DocumentSinkPort (Conceptual)

Aunque `OpenSearchIndexSink` actúa como tal, en implementaciones futuras podría generalizarse para otros motores. Actualmente, el UseCase interactúa directamente con el adaptador especializado de OpenSearch por conveniencia de los métodos de `bulk_upsert`.
