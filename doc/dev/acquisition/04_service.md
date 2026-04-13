# Módulo de Adquisición: Service y Use Cases

---

## AcquisitionService

El orquestador principal del crawl. Vive en `src/sri_dx/modules/acquisition/service.py`.

### Constructor

Recibe todas las dependencias por inyección (Ports):

```python
AcquisitionService(
    cfg: AcquisitionConfig,
    http: HttpClientPort,
    robots: RobotsPolicyPort,
    html_extractor: HtmlExtractorPort,
    pdf_extractor: PdfExtractorPort,
    sink_html: JsonlSinkPort,
    sink_pdf: JsonlSinkPort,
)
```

### Algoritmo de `run()`

1. **Cargar hashes existentes**: `_load_existing_hashes()` lee los archivos JSONL de salida y construye un `set` de `content_hash` ya vistos. Previene duplicados entre runs.
2. **Inicializar frontier**: `_seed_tasks()` convierte `cfg.seeds` en `CrawlTask` iniciales (`depth=0`).
3. **Scheduler con cooldown por dominio**: El método `_submit_from_frontier()` selecciona tareas del frontier cuyos dominios hayan superado `per_domain_delay_s`. Las tareas prematuras se reencolan sin bloquear los workers.
4. **Workers en paralelo**: `ThreadPoolExecutor(max_workers=cfg.max_workers)` procesa tareas concurrentemente.
5. **`_process_task(task)`**:
   - Verifica `robots.txt`.
   - Llama a `http.get(url)`.
   - Según `mime_type`, delega a `html_extractor` o `pdf_extractor`.
   - Limpia texto con `cleaning.py`.
   - Evalúa `should_persist()` — descarta si no supera los umbrales de calidad.
   - Verifica deduplicación por `content_hash`.
   - Llama a `build_document()` y escribe con el sink correspondiente.
   - Extrae URLs candidatas → filtra con `urls.py` → encola en frontier (si `depth < max_depth`).
6. **Condición de parada**: Loop termina cuando no hay tareas pendientes (`pending`) ni en el frontier.
7. **Retorno**: Diccionario de estadísticas: `written_html`, `written_pdf`, `visited_total`, `unique_hashes`, `skipped_not_persisted`, `skipped_duplicates`.

### Módulos de soporte en `modules/acquisition/`

| Archivo | Función |
|---|---|
| `cleaning.py` | `clean_text`, `clean_sections`, `build_body_from_sections` — normalización NFKC y colapso de espacios |
| `urls.py` | `normalize_url` (quita UTM params), `is_denied`, `within_whitelist`, `absolutize` |
| `persist_policy.py` | `should_persist` — filtra por conteo de palabras, ratio de líneas cortas, índices A–Z, out-links |
| `document_factory.py` | `build_document` — construye el dict final con `doc_id` (SHA-1), timestamps, bloques `crawl/content/page_meta` |
| `config_loader.py` | `load_acquisition_config` — parsea y valida `acquisition.yaml` |

---

## Sobre los Use Cases

### ¿Para qué sirven los Use Cases en este proyecto?

Los **Use Cases** (en `src/sri_dx/usecases/`) son la capa de **orquestación de aplicación** en la arquitectura hexagonal. Su propósito es:

- **Componer** ports y módulos del core para ejecutar un flujo de negocio concreto.
- **Ser el punto de entrada** para cualquier interfaz de usuario (CLI, API REST, tests de integración) sin que esa interfaz sepa nada de infraestructura.
- **Facilitar tests de integración** — se puede inyectar mocks de los ports sin montar infraestructura real.

Los use cases de indexación existentes (`IndexOpenSearchUseCase`, `EmbedChunksUseCase`, etc.) son buenos ejemplos: reciben ports por constructor y orquestan el flujo completo.

---

### ¿Hace falta un `RunAcquisitionUseCase`?

**Actualmente no existe**. El script `run_acquisition.py` instancia directamente `AcquisitionService` y lo ejecuta.

**Se recomienda crear uno** si se cumplen estas condiciones:

| Condición | Motivo |
|---|---|
| Se quiere exponer la adquisición desde una CLI unificada | El CLI de indexación ya usa Use Cases |
| Se necesitan tests de integración del flujo completo | Un UC permite inyectar mocks fácilmente |
| Se añade lógica extra (logging estructurado, notificaciones, métricas) | El UC evita contaminar `AcquisitionService` |

**Esqueleto propuesto** — `src/sri_dx/usecases/acquisition/run_acquisition.py`:

```python
from dataclasses import dataclass
from sri_dx.modules.acquisition import AcquisitionService, AcquisitionConfig
from sri_dx.core.ports.acquisition import (
    HttpClientPort, RobotsPolicyPort,
    HtmlExtractorPort, PdfExtractorPort, JsonlSinkPort,
)

@dataclass
class RunAcquisitionUseCase:
    cfg: AcquisitionConfig
    http: HttpClientPort
    robots: RobotsPolicyPort
    html_extractor: HtmlExtractorPort
    pdf_extractor: PdfExtractorPort
    sink_html: JsonlSinkPort
    sink_pdf: JsonlSinkPort

    def execute(self) -> dict:
        svc = AcquisitionService(
            cfg=self.cfg,
            http=self.http,
            robots=self.robots,
            html_extractor=self.html_extractor,
            pdf_extractor=self.pdf_extractor,
            sink_html=self.sink_html,
            sink_pdf=self.sink_pdf,
        )
        return svc.run()
```

Con esto, el script `run_acquisition.py` reduce a ensamblar dependencias y llamar `use_case.execute()`, igual que el patrón de indexación.
