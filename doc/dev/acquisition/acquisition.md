# Módulo de Adquisición (Acquisition)

## Índice
- [Introducción](#introducción)
- [Arquitectura General](#arquitectura-general)
- [Modelos de Datos](#modelos-de-datos)
- [Puertos e Interfaces](#puertos-e-interfaces)
- [Adaptadores de Scraping](#adaptadores-de-scraping)
- [Servicio de Adquisición](#servicio-de-adquisición)
- [Configuración](#configuración)
- [Formato de Exportación JSONL](#formato-de-exportación-jsonl)
- [Políticas y Heurísticas](#políticas-y-heurísticas)
- [Flujo de Ejecución](#flujo-de-ejecución)

---

## Introducción

El **módulo de adquisición** (`src/sri_dx/modules/acquisition`) es responsable del **web scraping** y **crawling** de fuentes médicas estructuradas (HTML y PDF). Su objetivo es:

1. Descargar contenido médico desde URLs semilla (*seeds*)
2. Extraer texto, metadatos y estructura
3. Aplicar políticas de persistencia (filtrar índices, páginas cortas, etc.)
4. Exportar documentos en formato **JSONL** para procesamiento posterior

El módulo sigue los principios de **Hexagonal Architecture** (Ports & Adapters), separando la lógica del dominio de las implementaciones técnicas.

---

## Arquitectura General

```
┌──────────────────────────────────────────┐
│      AcquisitionService (Orquestador)    │
│  - Gestiona frontier (BFS crawler)       │
│  - Aplica filtros y políticas            │
│  - Coordina adaptadores                  │
└───────────────┬──────────────────────────┘
                │
    ┌───────────┴────────────────┐
    │                            │
    v                            v
┌─────────────┐          ┌──────────────┐
│   Ports     │          │  Adaptadores │
│  (Interfaces)│         │ (Implementación)│
└─────────────┘          └──────────────┘
    │                            │
    ├─ HttpClient ───────────────┼─ HttpxClient
    ├─ RobotsPolicy ─────────────┼─ RobotsTxtPolicy
    ├─ HtmlExtractor ────────────┼─ SimpleHtmlExtractor
    ├─ PdfExtractor ─────────────┼─ SimplePdfExtractor
    └─ JsonlSink ────────────────┼─ JsonlFileSink
```

### Componentes clave:

- **AcquisitionService**: Orquestador principal que implementa el crawler BFS.
- **Ports**: Interfaces abstractas que definen contratos funcionales.
- **Adapters**: Implementaciones concretas (pueden ser reemplazadas sin afectar el core).

---

## Modelos de Datos

### `CrawlTask`
**Ubicación**: `src/sri_dx/modules/acquisition/models.py`

```python
@dataclass(frozen=True)
class CrawlTask:
    url: str                      # URL a procesar
    depth: int                    # Profundidad en el árbol de crawling
    parent_url: Optional[str]     # URL padre (para trazabilidad)
    seed_id: str                  # Identificador de la seed original
    seed_group: str               # Grupo temático de la seed
```

**Propósito**: Representar una unidad de trabajo en la frontier del crawler.

---

### `FetchResult`
```python
@dataclass(frozen=True)
class FetchResult:
    url: str                      # URL final (tras redirects)
    status_code: int              # Código HTTP
    mime_type: str                # MIME type del contenido
    content: bytes                # Contenido crudo (HTML/PDF)
    fetched_at: datetime          # Timestamp de descarga (UTC)
    headers: dict[str, str]       # Headers HTTP
```

**Propósito**: Encapsular la respuesta HTTP de una descarga.

---

### `Section`
```python
@dataclass(frozen=True)
class Section:
    heading: str                  # Título de la sección (ej: "Etiology", "Treatment")
    text: str                     # Texto de la sección (limpio)
```

**Propósito**: Representar una sección estructurada de un documento (usada por los extractores).

---

## Puertos e Interfaces

**Ubicación**: `src/sri_dx/modules/acquisition/ports.py`

Los **puertos** son interfaces (`Protocol`) que definen contratos sin implementación. Esto permite:
- **Testing**: Mocks fáciles de crear.
- **Intercambio**: Cambiar implementaciones sin tocar el core.

### `HttpClient`
```python
class HttpClient(Protocol):
    def get(self, url: str, *, timeout_s: float) -> FetchResult: ...
```
**Responsabilidad**: Descargar recursos HTTP (sigue redirects, maneja SSL, etc.).

---

### `RobotsPolicy`
```python
class RobotsPolicy(Protocol):
    def allowed(self, url: str, user_agent: str) -> bool: ...
```
**Responsabilidad**: Validar si una URL es permitida según `robots.txt`.

---

### `HtmlExtractor`
```python
class HtmlExtractor(Protocol):
    def extract(self, url: str, html: bytes) -> tuple[
        Optional[str],        # title
        list[Section],        # sections
        str,                  # body (texto principal)
        list[str],            # out_links (hrefs descubiertos)
        dict                  # page_meta_partial (author, lang, etc.)
    ]: ...
```
**Responsabilidad**: Parsear HTML y extraer:
- Título (desde `og:title`, `<title>`, o `<h1>`)
- Secciones (agrupadas por headings `<h1>`, `<h2>`, `<h3>`)
- Enlaces descubiertos (para crawling)
- Metadatos explícitos (idioma, autor, fechas)

---

### `PdfExtractor`
```python
class PdfExtractor(Protocol):
    def extract(self, url: str, pdf: bytes) -> tuple[
        Optional[str],        # title
        list[Section],        # sections (mínimo una "main")
        str,                  # body
        dict                  # page_meta_partial
    ]: ...
```
**Responsabilidad**: Extraer texto de PDFs y metadatos si están disponibles.

---

### `JsonlSink`
```python
class JsonlSink(Protocol):
    def write(self, doc: dict) -> None: ...
```
**Responsabilidad**: Persistir documentos en formato JSONL (1 doc = 1 línea JSON).

---

## Adaptadores de Scraping

**Ubicación**: `src/sri_dx/adapters/scraping/`

### `HttpxClient`
**Archivo**: `http_client.py`

```python
class HttpxClient(HttpClient):
    def __init__(self, user_agent: str, verify_ssl: bool = True):
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            follow_redirects=True,
            verify=(certifi.where() if verify_ssl else False)
        )
    
    def get(self, url: str, *, timeout_s: float) -> FetchResult:
        # Descarga, normaliza mime_type, retorna FetchResult
```

**Características**:
- Usa `httpx` (cliente HTTP moderno, async-ready)
- Sigue redirects automáticamente
- Soporta verificación SSL (con `certifi`)
- Normaliza `Content-Type` (quita charset, convierte a lowercase)

---

### `RobotsTxtPolicy`
**Archivo**: `robots_policy.py`

```python
class RobotsTxtPolicy(RobotsPolicy):
    def __init__(self):
        self._cache: dict[str, RobotFileParser] = {}
    
    def allowed(self, url: str, user_agent: str) -> bool:
        # Cachea robots.txt por dominio
        # Si falla lectura, permite acceso (política práctica)
```

**Características**:
- **Caché por dominio**: No descarga `robots.txt` repetidamente.
- **Política tolerante**: Si falla la lectura, permite acceso (para no bloquear el crawler).

---

### `SimpleHtmlExtractor`
**Archivo**: `html_extractor.py`

```python
class SimpleHtmlExtractor:
    def extract(self, url: str, html: bytes) -> tuple[...]:
        soup = BeautifulSoup(html, "lxml")
        container = _pick_main_container(soup)  # Prioriza <article>, <main>
        
        # 1. Extrae título (og:title > <title> > <h1>)
        # 2. Extrae secciones (h1/h2/h3 + p/li)
        # 3. Construye body estable
        # 4. Extrae out_links (hrefs)
        # 5. Extrae metadatos (lang, author, published_at, updated_at)
```

**Heurísticas de extracción**:

#### 1. **Selección de contenedor principal**
```python
def _pick_main_container(soup):
    for tag in ("article", "main"):
        found = soup.find(tag)
        if found:
            return found
    return soup.body or soup
```
Reduce ruido enfocándose en el contenido principal.

#### 2. **Extracción de título (best-effort)**
```
Prioridad:
1. <meta property="og:title">
2. <title>
3. Primer <h1>
```

#### 3. **Extracción de secciones**
- Recorre headings (`<h1>`, `<h2>`, `<h3>`)
- Agrupa texto bajo cada heading (desde `<p>`, `<li>`)
- Si no hay headings, crea una sección "main"

#### 4. **Metadatos extraídos**
```python
page_meta = {
    "language": <html lang="...">[:2],  # Primeros 2 chars (ej: "en", "es")
    "author": <meta name="author">,
    "published_at": <meta property="article:published_time">,
    "updated_at": <meta property="article:modified_time">
}
```

---

### `SimplePdfExtractor`
**Archivo**: `pdf_extractor.py`

```python
class SimplePdfExtractor:
    def extract(self, url: str, pdf: bytes) -> tuple[...]:
        reader = PdfReader(BytesIO(pdf))
        
        # 1. Extrae texto de todas las páginas
        # 2. Lee metadata (title, author)
        # 3. Crea una sección "main" con todo el texto
```

**Características**:
- Usa `pypdf` (sin OCR, solo texto extraíble)
- Metadata best-effort (title, author desde PDF metadata)
- No hace segmentación (todo en una sección "main")

---

### `JsonlFileSink`
**Archivo**: `jsonl_sink.py`

```python
class JsonlFileSink(JsonlSink):
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def write(self, doc: dict[str, Any]) -> None:
        line = json.dumps(doc, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
```

**Características**:
- Append-only (cada doc es 1 línea JSON)
- UTF-8 sin escape (caracteres Unicode preservados)
- Crea directorios automáticamente

---

## Servicio de Adquisición

**Ubicación**: `src/sri_dx/modules/acquisition/service.py`

### `AcquisitionService`

El orquestador principal que implementa el crawler.

```python
class AcquisitionService:
    def __init__(self, cfg, http, robots, html_extractor, pdf_extractor, sink_html, sink_pdf):
        # Inyección de dependencias (Ports)
    
    def run(self) -> dict:
        # Retorna estadísticas: written_html, written_pdf, visited_total, etc.
```

### Algoritmo de Crawling (BFS)

```
1. Inicializar frontier con seeds (depth=0)
2. Mientras frontier tenga URLs y no se alcance max_docs:
   a. Pop URL de frontier
   b. Filtros:
      - Ya visitada → skip
      - Denylist (login, search, etc.) → skip
      - Fuera de whitelist_domains → skip
      - Bloqueada por robots.txt → skip
   c. Aplicar politeness delay (per_domain_delay_s)
   d. Descargar (http.get)
   e. Extraer contenido (html_extractor / pdf_extractor)
   f. Construir documento (build_document)
   g. Aplicar política de persistencia (should_persist)
   h. Si persist=True:
      - Dedupe por content_hash
      - Escribir a sink (HTML o PDF)
   i. Si HTML y depth < max_depth:
      - Expandir out_links a frontier (depth+1)
```

### Deduplicación

- **Por URL**: `_visited` (set de URLs normalizadas)
- **Por contenido**: `_seen_hashes` (set de SHA256 de body)

---

## Configuración

**Ubicación**: `configs/acquisition.yaml`

### Estructura del YAML

```yaml
# === HTTP / Crawling ===
user_agent: "sri-dx-acquisition/0.1"
timeout_s: 20                      # Timeout por request (segundos)
per_domain_delay_s: 5              # Delay entre requests al mismo dominio
max_depth: 2                       # Profundidad máxima del crawler (0 = solo seeds)
max_docs: 20                       # Límite total de documentos a guardar
verify_ssl: false                  # Verificar certificados SSL (dev: false, prod: true)

# === Whitelist de dominios ===
whitelist_domains:
  - msdmanuals.com                 # Acepta msdmanuals.com y *.msdmanuals.com
  - www.nhs.uk
  - www.cdc.gov

# === Seeds (URLs iniciales) ===
seeds:
  - seed_id: seed_001              # ID único
    seed_group: msd_guides_en      # Grupo temático (para organización)
    url: https://www.msdmanuals.com/professional/...
  
  - seed_id: seed_002
    seed_group: nhs_conditions_en
    url: https://www.nhs.uk/conditions/asthma/

# === Salida ===
out:
  dir: data/processed              # Directorio de salida
  html_name: docs_html.jsonl       # Archivo para docs HTML
  pdf_name: docs_pdf.jsonl         # Archivo para docs PDF

# === Políticas de persistencia ===
persist:
  min_words_html: 200              # Mínimo de palabras para guardar HTML
  min_words_pdf: 200               # Mínimo de palabras para guardar PDF
  max_out_links_html: 120          # Si tiene >120 links y poco texto, se considera índice
  
  # Substrings de URL que se ignoran (índices, páginas admin, etc.)
  skip_url_substrings:
    - "/about"
    - "/contact"
    - "/privacy"
    - "/terms"
    - "/cookie"
    - "/site-map"
    - "/sitemap"
    - "/index"
    - "/all_"
    - "/search"
  
  detect_az_index: true            # Detecta índices A-Z (ej: MedlinePlus)
```

### Carga de configuración

**Archivo**: `config_loader.py`

```python
def load_acquisition_config(path: Path) -> AcquisitionConfig:
    # 1. Lee YAML
    # 2. Valida estructura
    # 3. Convierte a dataclass AcquisitionConfig
    # 4. Usa defaults si faltan campos
```

**Validaciones**:
- `seeds` debe ser lista de dicts con `seed_id`, `seed_group`, `url`
- `whitelist_domains` debe ser lista de strings
- Campos numéricos se convierten a `int`/`float`

---

## Formato de Exportación JSONL

**Ubicación salida**: `data/processed/docs_html.jsonl` y `data/processed/docs_pdf.jsonl`

### Estructura del documento

Cada línea del archivo JSONL es un objeto JSON con el siguiente esquema:

```json
{
  "doc_id": "dd3f2d1a8befa0fe",
  "url": "https://www.msdmanuals.com/professional/...",
  "source_domain": "www.msdmanuals.com",
  "fetched_at": "2026-03-03T05:52:34Z",
  
  "crawl": {
    "depth": 0,
    "parent_url": null,
    "seed_id": "seed_001",
    "seed_group": "msd_guides_en"
  },
  
  "content": {
    "mime_type": "text/html",
    "title": "Type 1 Diabetes Mellitus - Endocrinology - MSD Manual",
    
    "sections": [
      {
        "heading": "Etiology of Type 1 Diabetes Mellitus",
        "text": "The hallmark of type 1 diabetes is..."
      },
      {
        "heading": "Symptoms and Signs",
        "text": "Islet cell destruction generally precedes..."
      }
    ],
    
    "body": "Type 1 Diabetes Mellitus\n\nThe hallmark of type 1 diabetes..."
  },
  
  "page_meta": {
    "published_at": null,
    "updated_at": null,
    "author": null,
    "language": "en"
  },
  
  "content_hash": "e54f6147506e06c9c12e6160533b2ba02a2fc6a667d40c429545fbe66ac6fb93"
}
```

### Campos del documento

#### **Nivel raíz**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `doc_id` | `str` | SHA1 truncado (16 chars) de la URL normalizada |
| `url` | `str` | URL normalizada (sin fragments, sin tracking params) |
| `source_domain` | `str` | Dominio extraído de la URL |
| `fetched_at` | `str` | Timestamp ISO 8601 (UTC, formato: `YYYY-MM-DDTHH:MM:SSZ`) |
| `content_hash` | `str` | SHA256 del `body` (para deduplicación por contenido) |

#### **Sección `crawl`**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `depth` | `int` | Profundidad en el árbol de crawling (0 = seed) |
| `parent_url` | `str \| null` | URL padre (null si es seed) |
| `seed_id` | `str` | Identificador de la seed original |
| `seed_group` | `str` | Grupo temático de la seed |

#### **Sección `content`**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `mime_type` | `str` | MIME type normalizado (`text/html` o `application/pdf`) |
| `title` | `str \| null` | Título del documento (null si no se detecta) |
| `sections` | `list[dict]` | Lista de secciones (`heading`, `text`) |
| `body` | `str` | Texto completo del documento (concatenación estable de secciones) |

#### **Sección `page_meta`**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `language` | `str \| null` | Código de idioma (2 chars: "en", "es", etc.) |
| `author` | `str \| null` | Autor (si está en `<meta name="author">` o PDF metadata) |
| `published_at` | `str \| null` | Fecha de publicación (ISO 8601) |
| `updated_at` | `str \| null` | Fecha de última actualización (ISO 8601) |

### Normalización del contenido

**Archivo**: `cleaning.py`

```python
def clean_text(text: str) -> str:
    # 1. Unicode NFKC normalization
    # 2. Normaliza saltos de línea (\r\n → \n)
    # 3. Colapsa espacios repetidos ( \t+ → " ")
    # 4. Colapsa bloques de saltos de línea (\n{3,} → \n\n)
```

**Archivo**: `document_factory.py`

```python
def build_document(...) -> dict:
    # 1. Normaliza URL
    # 2. Limpia secciones (clean_sections)
    # 3. Genera body estable desde secciones
    # 4. Calcula doc_id (SHA1 de URL)
    # 5. Calcula content_hash (SHA256 de body)
    # 6. Ensambla el documento final
```

---

## Políticas y Heurísticas

**Ubicación**: `persist_policy.py`, `urls.py`

### `should_persist`

Decide si un documento debe guardarse o solo usarse para descubrir enlaces.

```python
def should_persist(url, mime_type, body, out_links_count, cfg) -> bool:
    # REGLA 1: Skip por patrón de URL
    if any(substring in url.lower() for substring in cfg.skip_persist_url_substrings):
        return False
    
    # REGLA 2: HTML
    if mime_type.startswith("text/html"):
        # 2.1: Mínimo de palabras
        if word_count < cfg.min_words_html:
            return False
        
        # 2.2: Índice A-Z (heurística regex)
        if cfg.detect_az_index and re.search(r"\bA\s+B\s+C\s+D\s+E\b", body):
            return False
        
        # 2.3: Muchos links + poco texto = directorio
        if out_links_count >= cfg.max_out_links_html and word_count < min_words_html * 3:
            return False
        
        # 2.4: Listado (muchas líneas cortas)
        lines = body.splitlines()
        short_lines = sum(1 for ln in lines if len(ln.split()) <= 3)
        if (short_lines / len(lines)) > 0.60 and word_count < min_words_html * 4:
            return False
        
        return True
    
    # REGLA 3: PDF
    if mime_type == "application/pdf":
        return word_count >= cfg.min_words_pdf
    
    return False
```

### `normalize_url`

**Archivo**: `urls.py`

```python
def normalize_url(url: str) -> str:
    # 1. Quita fragment (#...)
    # 2. Elimina query params de tracking (utm_*, gclid, fbclid)
    # 3. Retorna URL canónica
```

### `is_denied`

```python
_DENY_SUBSTRINGS = ("/login", "/signin", "/search", "/cookie", "/privacy", "/terms")
_DENY_SCHEMES = ("mailto", "javascript", "tel")

def is_denied(url: str) -> bool:
    # Bloquea esquemas y substrings de utilidad (páginas no informativas)
```

### `within_whitelist`

```python
def within_whitelist(url: str, whitelist: tuple[str, ...]) -> bool:
    # Acepta:
    # - Dominio exacto (cdc.gov)
    # - Subdominios (www.cdc.gov) si la whitelist contiene cdc.gov
```

---

## Flujo de Ejecución

### 1. **Inicialización**

**Archivo**: `src/sri_dx/scripts/run_acquisition.py`

```python
# 1. Cargar configuración
cfg = load_acquisition_config(Path("configs/acquisition.yaml"))

# 2. Instanciar adaptadores
http = HttpxClient(user_agent=cfg.user_agent, verify_ssl=cfg.verify_ssl)
robots = RobotsTxtPolicy()
html_extractor = SimpleHtmlExtractor()
pdf_extractor = SimplePdfExtractor()
sink_html = JsonlFileSink(cfg.out_dir / cfg.out_html_name)
sink_pdf = JsonlFileSink(cfg.out_dir / cfg.out_pdf_name)

# 3. Crear servicio
service = AcquisitionService(
    cfg=cfg, http=http, robots=robots,
    html_extractor=html_extractor, pdf_extractor=pdf_extractor,
    sink_html=sink_html, sink_pdf=sink_pdf
)

# 4. Ejecutar
stats = service.run()
```

### 2. **Crawling Loop**

```
INICIO
  ↓
[Frontier] ← seeds (depth=0)
  ↓
┌─────────────────────┐
│ Pop URL de frontier │
└──────────┬──────────┘
           ↓
    ┌──────────────┐
    │   Filtros:   │
    │ - Visited?   │
    │ - Denylist?  │
    │ - Whitelist? │
    │ - Robots?    │
    └──────┬───────┘
           ↓
     [HTTP GET]
           ↓
    ┌──────────────┐
    │  Extractor   │
    │ (HTML / PDF) │
    └──────┬───────┘
           ↓
   [build_document]
           ↓
  ┌─────────────────┐
  │ should_persist? │
  └────┬────────┬───┘
       │        │
     YES       NO
       │        │
       ↓        └─→ (solo crawl)
  [Dedupe hash]
       ↓
   [JSONL sink]
       ↓
  ┌─────────────────┐
  │ Expand links?   │
  │ (HTML, depth<max)│
  └────────┬────────┘
           ↓
    [Add to frontier]
           ↓
    ┌──────────────┐
    │ max_docs     │
    │ alcanzado?   │
    └──┬───────┬───┘
       │       │
      SÍ      NO
       │       │
       ↓       └─→ [Loop]
      FIN
```

### 3. **Salida**

Al finalizar, `service.run()` retorna estadísticas:

```python
{
    "written_html": 15,
    "written_pdf": 2,
    "visited_total": 120,
    "unique_hashes": 17,
    "skipped_not_persisted": 98,
    "skipped_duplicates": 5
}
```

---

## Notas Importantes

### **1. Arquitectura Hexagonal**

El módulo sigue estrictamente **Ports & Adapters**:
- **Core** (`models.py`, `service.py`, `config.py`): Sin dependencias externas.
- **Ports** (`ports.py`): Interfaces abstractas.
- **Adapters** (`adapters/scraping/`): Implementaciones concretas (httpx, BeautifulSoup, pypdf).

**Ventajas**:
- Testable (puedes mockear todos los puertos).
- Intercambiable (cambiar de BS4 a Scrapy sin tocar `AcquisitionService`).

### **2. Politeness**

- `per_domain_delay_s`: Delay entre requests al mismo dominio (evita sobrecarga).
- `robots.txt`: Respeta las políticas del servidor.
- `user_agent`: Identificación clara del crawler.

**Configuración recomendada para producción**:
```yaml
per_domain_delay_s: 2-5
verify_ssl: true
max_depth: 2-3
```

### **3. Deduplicación**

**Dos niveles**:
1. **Por URL**: Evita visitar la misma URL dos veces dentro de una ejecución (`_visited` set).
2. **Por contenido**: Evita guardar documentos con `body` idéntico, usando `content_hash` (SHA256).

**⚠️ IMPORTANTE - Deduplicación entre ejecuciones**:

El sistema **carga automáticamente** los hashes existentes de los archivos JSONL al iniciar, previniendo duplicados entre múltiples ejecuciones del crawler.

```python
def _load_existing_hashes(self) -> None:
    """
    Carga los content_hash de documentos ya guardados en los archivos JSONL.
    Esto previene duplicados entre múltiples ejecuciones del crawler.
    """
    # Lee docs_html.jsonl y docs_pdf.jsonl
    # Agrega todos los content_hash al set _seen_hashes
```

**Flujo de deduplicación**:
1. **Inicialización**: Carga hashes de archivos JSONL existentes → `_seen_hashes`
2. **Durante crawl**: Compara nuevo `content_hash` con `_seen_hashes`
3. **Si duplicado**: Incrementa contador, NO escribe documento
4. **Si nuevo**: Agrega hash al set, escribe documento en JSONL (modo append)

**Ventaja**: Puedes ejecutar el crawler múltiples veces acumulando datos sin duplicar contenido, incluso si las URLs son diferentes.

### **4. Manejo de errores**

El servicio es **tolerante a fallos**:
- Si falla la descarga → skip (continúa con la siguiente URL).
- Si falla la extracción → skip.
- Si falla `should_persist` → guarda por defecto (safe).

**No se interrumpe el crawler** por errores individuales.

### **5. Normalización de texto**

Toda normalización es **determinista** y **estable**:
- Unicode NFKC (compatibilidad).
- Colapsar espacios y saltos de línea.
- No depende del extractor (se aplica en `cleaning.py`).

**Esto garantiza**:
- `content_hash` reproducible.
- `body` uniforme para indexación.

### **6. Extensibilidad**

Para agregar soporte a nuevos formatos (ej: Word, XML):
1. Crear `WordExtractor` implementando `ports.ExtractorProtocol`.
2. Inyectar en `AcquisitionService.__init__`.
3. Agregar lógica de dispatch en `service.run()`.

**No es necesario modificar el core** del crawler.

---

## Ejemplos de Uso

### Ejecutar el crawler

```bash
# Desde la raíz del proyecto
python -m sri_dx.scripts.run_acquisition
```

### Inspeccionar JSONL

```bash
# Ver primeros 5 documentos
head -n 5 data/processed/docs_html.jsonl | jq .

# Contar documentos
wc -l data/processed/docs_html.jsonl
wc -l data/processed/docs_pdf.jsonl

# Filtrar por seed_group
cat data/processed/docs_html.jsonl | jq 'select(.crawl.seed_group == "msd_guides_en")'
```

### Validar configuración

```python
from pathlib import Path
from sri_dx.modules.acquisition.config_loader import load_acquisition_config

cfg = load_acquisition_config(Path("configs/acquisition.yaml"))
print(f"Seeds: {len(cfg.seeds)}")
print(f"Whitelist: {cfg.whitelist_domains}")
```

---


