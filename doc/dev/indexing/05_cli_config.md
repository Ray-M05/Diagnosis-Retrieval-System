# Indexing Module: CLI & Configuración

Guía técnica para operar el módulo de indexación.

## Configuración (`config.toml`)

El sistema busca un archivo `config.toml` en la raíz por defecto. También permite usar variables de entorno con el prefijo `SRI_`.

### Ejemplo de Configuración

```toml
[opensearch]
host = "localhost"
port = 9200
index_name = "clinical_docs_v1"
alias_name = "clinical_docs"

[indexing]
html_source = "data/processed/docs_html.jsonl"
batch_size = 500
```

## CLI (`sri-dx`)

El comando principal está definido en `src/sri_dx/app/cli.py`.

### Comandos de Indexación

- `index run`: Ejecuta el flujo incremental.
  - `--refresh`: Fuerza el refresco del índice al final.
  - `--index <nombre>`: Sobrescribe el índice de destino.
- `index create --name <idx>`: Crea un nuevo índice configurado con los mappings de clinical documents.
- `index alias --to <idx>`: Cambia el alias estable al índice indicado (útil para despliegue azul-verde).

### Reportes

Cada ejecución de `index run` genera un reporte en:
`data/index/reports/index_run_YYYYMMDD_HHMMSS.json`

Contiene:

- Documentos procesados, saltados y fallidos.
- Estadísticas por tipo MIME y por dominio de origen.
- Lista de errores de ejecución.
