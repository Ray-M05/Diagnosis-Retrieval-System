# Módulo de Adquisición: Configuración

El comportamiento completo del crawler se controla desde `configs/acquisition.yaml`.

---

## Referencia de parámetros

### HTTP

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `user_agent` | `str` | — | User-Agent enviado en cada petición. |
| `timeout_s` | `int` | 20 | Timeout por petición en segundos. |
| `verify_ssl` | `bool` | `false` | Si `false`, deshabilita la verificación de certificados SSL. Útil en entornos de desarrollo. |

### Crawl

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `per_domain_delay_s` | `int` | 5 | Delay mínimo entre peticiones al mismo dominio (cortesía). |
| `max_depth` | `int` | 4 | Profundidad máxima del grafo de crawl desde cada seed. |
| `max_docs` | `int` | 300 | Límite total de documentos escritos en el run. |
| `max_workers` | `int` | 15 | Número de workers concurrentes (`ThreadPoolExecutor`). |

### Alcance

```yaml
whitelist_domains:
  - msdmanuals.com
  - mayoclinic.org
  - www.nhs.uk

seeds:
  - seed_id: seed_0012
    seed_group: msd_topics_en
    url: https://www.msdmanuals.com/professional/health-topics
```

- Solo se rastrean URLs dentro de los dominios en `whitelist_domains` (subdomains incluidos).
- Cada seed genera una `CrawlTask` inicial con `depth=0`.
- `seed_group` se propaga a todos los documentos adquiridos por esa semilla (útil para filtrar en la indexación).

### Salida

```yaml
out:
  dir: data/processed
  html_name: docs_html.jsonl
  pdf_name: docs_pdf.jsonl
```

- `out_dir` es relativo a la raíz del proyecto.
- Los dos archivos JSONL son la salida que consume el módulo de indexación.

### Política de persistencia

| Parámetro | Tipo | Descripción |
|---|---|---|
| `min_words_html` | `int` | Documentos HTML con menos palabras se descartan. |
| `min_words_pdf` | `int` | Documentos PDF con menos palabras se descartan. |
| `max_out_links_html` | `int` | Páginas con demasiados links salientes se consideran índices y se descartan. |
| `skip_url_substrings` | `list[str]` | URLs que contienen alguno de estos strings se omiten (e.g. `/about`, `/search`). |
| `detect_az_index` | `bool` | Si `true`, descarta páginas que parecen índices A–Z por ratio de líneas cortas. |

---

## Ejecución

```powershell
# Desde la raíz del proyecto
uv run python -m sri_dx.scripts.run_acquisition
```

El script imprime las estadísticas del run al finalizar:

```
{'written_html': 287, 'written_pdf': 3, 'visited_total': 412,
 'unique_hashes': 290, 'skipped_not_persisted': 95, 'skipped_duplicates': 27}
```

---

## Notas de operación

- **Runs incrementales**: El servicio carga los `content_hash` existentes al inicio. Documentos con el mismo hash de contenido no se vuelven a escribir, aunque se re-visiten sus URLs.
- **Dominio activo en config actual**: Solo `seed_0012` (MSD Manuals profesional) está activo. Los seeds NHS y Mayo Clinic están comentados.
- **SSL**: `verify_ssl: false` está pensado para entornos de desarrollo/lab. En producción se recomienda habilitarlo.
