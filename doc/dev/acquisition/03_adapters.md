# Módulo de Adquisición: Adapters

Implementaciones concretas de infraestructura que viven en `src/sri_dx/adapters/scraping/`.

---

## HttpxClient

- **Archivo**: `http_client.py`
- **Port que implementa**: `HttpClientPort`
- **Tecnología**: [`httpx`](https://www.python-httpx.org/) — cliente HTTP moderno y async-compatible.
- **Comportamiento**:
  - Sigue redirecciones automáticamente.
  - Verificación SSL configurable (`certifi` si `verify_ssl=True`).
  - Devuelve `FetchResult` con `content: bytes`, `status_code`, `mime_type`, `fetched_at` y cabeceras.

---

## RobotsTxtPolicy

- **Archivo**: `robots_policy.py`
- **Port que implementa**: `RobotsPolicyPort`
- **Comportamiento**:
  - Descarga `robots.txt` una sola vez por dominio (caché en memoria, thread-safe).
  - Usa `RobotFileParser` de la stdlib de Python.
  - **Falla abierto**: si el servidor no devuelve `robots.txt` o hay un error de red, el acceso se considera permitido.

---

## SimpleHtmlExtractor

- **Archivo**: `html_extractor.py`
- **Port que implementa**: `HtmlExtractorPort`
- **Tecnología**: `BeautifulSoup` con parser `lxml`.
- **Extracción de título** (prioridad descendente):
  1. Meta tag `og:title`
  2. Tag `<title>`
  3. Primer `<h1>` del documento
- **Extracción de secciones**: Recorre `h1/h2/h3` y agrupa el contenido (`p`, `li`) bajo cada encabezado para producir `list[Section]`.
- **out_links**: Todos los `href` de tags `<a>`.
- **page_meta_partial**: `lang` (del tag `<html>`), `author`, `article:published_time`, `article:modified_time`.

---

## SimplePdfExtractor

- **Archivo**: `pdf_extractor.py`
- **Port que implementa**: `PdfExtractorPort`
- **Tecnología**: `pypdf`.
- **Comportamiento**: Extrae el texto de todas las páginas en una única `Section(heading="main", text=...)`. Lee `title` y `author` de los metadatos del PDF.
- **Limitación**: Sin detección de estructura (columnas, encabezados de sección). Apto para documentos de texto lineal.

---

## JsonlFileSink

- **Archivo**: `jsonl_sink.py`
- **Port que implementa**: `JsonlSinkPort`
- **Comportamiento**:
  - Modo `append` — nunca sobreescribe el archivo existente.
  - Thread-safe mediante `threading.Lock` (compatible con el pool de workers de `AcquisitionService`).
  - Cada documento se serializa como una línea JSON (`json.dumps` + `\n`).

---

## JsonlDocumentSource

- **Archivo**: `adapters/document_sources/jsonl_source.py`
- **Port que implementa**: `DocumentSourcePort`
- **Uso**: Lectura de los archivos JSONL producidos por el scraper para alimentar el módulo de indexación.
- **Comportamiento**: Streams de `AcquiredDocument` deserializado desde múltiples archivos `.jsonl`.
