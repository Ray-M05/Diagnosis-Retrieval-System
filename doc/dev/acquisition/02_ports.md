# Módulo de Adquisición: Ports

Interfaces abstractas (Protocols/ABCs) del Core que desacoplan el `AcquisitionService` de cualquier infraestructura concreta.

Todos están en `src/sri_dx/core/ports/acquisition/`.

---

## HttpClientPort

Contrato para realizar peticiones HTTP.

- **Archivo**: `http_client_port.py`
- **Método**: `get(url: str, *, timeout_s: float) -> FetchResult`
- **Implementación actual**: `HttpxClient` — usa `httpx` con seguimiento de redirecciones y SSL opcional.

---

## RobotsPolicyPort

Contrato para verificar si el crawler tiene permiso de acceder a una URL.

- **Archivo**: `robots_policy_port.py`
- **Método**: `allowed(url: str, user_agent: str) -> bool`
- **Implementación actual**: `RobotsTxtPolicy` — descarga y cachea `robots.txt` por dominio. **Falla abierto** (devuelve `True`) si hay errores de red.

---

## HtmlExtractorPort

Contrato para extraer contenido estructurado de HTML crudo.

- **Archivo**: `html_extractor_port.py`
- **Método**: `extract(url, html) -> (title?, sections, body, out_links, page_meta_partial)`
- **Implementación actual**: `SimpleHtmlExtractor` — BeautifulSoup + lxml. Detecta título por `og:title` → `<title>` → primer `<h1>`.

---

## PdfExtractorPort

Contrato para extraer texto de documentos PDF.

- **Archivo**: `pdf_extractor_port.py`
- **Método**: `extract(url, pdf_bytes) -> (title?, sections, body, page_meta_partial)`
- **Implementación actual**: `SimplePdfExtractor` — `pypdf`. Produce una sola sección con `heading="main"`.

---

## JsonlSinkPort

Contrato para escribir documentos en el sink de salida.

- **Archivo**: `jsonl_sink_port.py`
- **Método**: `write(doc: dict) -> None`
- **Implementación actual**: `JsonlFileSink` — escritura append-only thread-safe con `threading.Lock`.

---

## DocumentSourcePort

Contrato para leer documentos ya adquiridos (usados por el módulo de indexación, no por el scraper).

- **Archivo**: `document_source.py`
- **Método**: `iter_documents() -> Iterable[AcquiredDocument]`
- **Implementación actual**: `JsonlDocumentSource` — deserializa líneas JSONL a `AcquiredDocument`.

---

## ManifestStorePort

Contrato para persistir el estado de indexación de cada documento (incrementalidad).

- **Archivo**: `manifest_store.py`
- **Métodos**: `get(doc_id)`, `get_many(doc_ids)`, `upsert_many(entries)`
- **Nota**: Usado por el módulo de **indexación**, no directamente por el scraper.

---

## Resumen de dependencias

```
AcquisitionService
    ├── HttpClientPort        → HttpxClient
    ├── RobotsPolicyPort      → RobotsTxtPolicy
    ├── HtmlExtractorPort     → SimpleHtmlExtractor
    ├── PdfExtractorPort      → SimplePdfExtractor
    ├── JsonlSinkPort (html)  → JsonlFileSink(docs_html.jsonl)
    └── JsonlSinkPort (pdf)   → JsonlFileSink(docs_pdf.jsonl)
```

Cada dependencia puede sustituirse por una implementación alternativa (mock, otro motor, etc.) sin tocar `AcquisitionService`.
