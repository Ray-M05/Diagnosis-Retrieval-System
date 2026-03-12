# Módulo de Adquisición: Schemas

Modelos de datos del Core que definen las estructuras compartidas entre el scraper, los adaptadores y el módulo de indexación.

---

## FetchResult

Resultado crudo de una petición HTTP, antes de cualquier extracción.

- **Ruta**: `src/sri_dx/core/schemas/acquisition/fetch_result.py`
- **Campos**:
  - `url`: URL final (tras redirecciones).
  - `status_code`: Código HTTP de la respuesta.
  - `mime_type`: MIME detectado (`text/html`, `application/pdf`, etc.).
  - `content: bytes`: Cuerpo binario de la respuesta.
  - `fetched_at: datetime`: Timestamp UTC de la descarga.
  - `headers: dict`: Cabeceras de respuesta.

---

## Section

Fragmento estructurado de contenido, asociado a un encabezado de sección.

- **Parte de**: `acquired_document.py`
- **Campos**:
  - `heading: str`: Título de la sección (e.g. `"Diagnóstico"`, `"Tratamiento"`).
  - `text: str`: Cuerpo de texto de la sección.

---

## AcquiredDocument

Documento procesado y limpio listo para ser indexado. Es la **salida del módulo de adquisición** y la **entrada del módulo de indexación**.

- **Ruta**: `src/sri_dx/core/schemas/acquisition/acquired_document.py`

### Sub-estructuras

| Dataclass | Campos destacados |
|---|---|
| `CrawlMeta` | `depth`, `parent_url`, `seed_id`, `seed_group` |
| `PageMeta` | `published_at`, `updated_at`, `author`, `language` |
| `Content` | `mime_type`, `title`, `sections: list[Section]`, `body: str` |

### Campos del documento raíz

| Campo | Tipo | Descripción |
|---|---|---|
| `doc_id` | `str` | SHA-1 de la URL normalizada |
| `url` | `str` | URL canónica del documento |
| `source_domain` | `str` | Dominio de origen |
| `fetched_at` | `datetime` | Timestamp UTC de la descarga |
| `crawl` | `CrawlMeta` | Metadatos del grafo de crawl |
| `content` | `Content` | Contenido extraído y limpio |
| `page_meta` | `PageMeta?` | Metadatos de página (opcionales) |
| `content_hash` | `str?` | SHA-256 del body limpio (deduplicación) |

---

## CrawlTask

Unidad de trabajo interna del scheduler.

- **Ruta**: `src/sri_dx/modules/acquisition/models.py`
- **Campos**: `url`, `depth`, `parent_url`, `seed_id`, `seed_group`.
- Es **frozen** (inmutable). Se crea en `_seed_tasks()` y se encola en el frontier.

---

## AcquisitionConfig

Configuración completa de un run de adquisición, cargada desde `acquisition.yaml`.

- **Ruta**: `src/sri_dx/modules/acquisition/schemas/acquisition_config.py`

### Grupos de parámetros

| Grupo | Campos |
|---|---|
| HTTP | `user_agent`, `timeout_s`, `verify_ssl` |
| Crawl | `per_domain_delay_s`, `max_depth`, `max_docs`, `max_workers` |
| Alcance | `whitelist_domains: list[str]`, `seeds: list[Seed]` |
| Salida | `out_dir`, `out_html_name`, `out_pdf_name` |
| Persistencia | `min_words_html/pdf`, `max_out_links_html`, `skip_persist_url_substrings`, `detect_az_index` |
