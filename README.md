# SRI-DX

Sistema de Recuperacion de Informacion clinica para apoyo al analisis diferencial.

Este proyecto usa **OpenSearch** como motor de busqueda e indexacion.

El README esta enfocado solo en:

- montar el proyecto localmente;
- preparar indices;
- ejecutar el orquestador;
- probar busquedas desde CLI.

## Requisitos

- Docker y Docker Compose.
- Python 3.11+ si vas a ejecutar comandos fuera de Docker.
- `uv` recomendado para entorno local.

La primera ejecucion puede descargar modelos de HuggingFace para embeddings, NER y reranking. Esa parte puede tardar.

## Servicios del proyecto

El `docker-compose.yml` levanta:

```text
opensearch     -> http://localhost:9200
sri-dx         -> Streamlit en http://localhost:8501
sri-dx-api     -> FastAPI en http://localhost:8000
```

## Montaje rapido con Docker

Desde la raiz del repo:

```bash
docker compose up -d --build
```

Verifica OpenSearch:

```bash
curl http://localhost:9200/_cluster/health
```

Ver indices:

```bash
curl http://localhost:9200/_cat/indices?v
```

Ver logs:

```bash
docker compose logs -f
```

Detener servicios:

```bash
docker compose down
```

Detener y borrar volumenes de OpenSearch:

```bash
docker compose down -v
```

## Ruta automatizada recomendada para reindexar y probar

Esta es la via recomendada para probar el proyecto con los datos existentes en:

```text
data/processed/docs_html.jsonl
data/processed/docs_pdf.jsonl
```

La ruta hace:

```text
1. Levantar contenedores
2. Borrar manifest local
3. Ejecutar orquestador
4. Probar consultas por CLI
```

### 1. Levantar OpenSearch

Si solo vas a preparar indices y probar por CLI local:

```bash
docker compose up -d opensearch
```

Si quieres dejar tambien Streamlit y API arriba:

```bash
docker compose up -d --build
```

Espera a que OpenSearch este saludable:

```bash
curl http://localhost:9200/_cluster/health
```

### 2. Borrar manifest para forzar reindexado

El manifest incremental evita reindexar documentos que no cambiaron. Para forzar un reindexado, borralo:

```bash
mkdir -p data/index
rm -f data/index/manifest.sqlite \
      data/index/manifest.sqlite-journal \
      data/index/manifest.sqlite-shm \
      data/index/manifest.sqlite-wal
```

Si tambien quieres borrar indices y datos persistidos en OpenSearch:

```bash
docker compose down -v
docker compose up -d opensearch
```

Despues de esto, vuelve a esperar salud del cluster:

```bash
curl http://localhost:9200/_cluster/health
```

### 3. Ejecutar el orquestador

El orquestador real esta en:

```text
src/sri_dx/app/cli/orchestrator.py
```

Ejecuta automaticamente:

```text
Fases 2+3: indexacion de documentos y chunks
Fase 4: generacion de embeddings
```

Como el repo ya tiene JSONL en `data/processed/`, normalmente se salta adquisicion:

```bash
uv run python src/sri_dx/app/cli/orchestrator.py \
  --skip-acquisition \
  --host localhost \
  --port 9200 \
  --embedding-device cpu \
  --embedding-batch-size 32
```

Si `uv` no funciona en tu maquina, usa el Python del entorno virtual:

```bash
.venv/bin/python src/sri_dx/app/cli/orchestrator.py \
  --skip-acquisition \
  --host localhost \
  --port 9200 \
  --embedding-device cpu \
  --embedding-batch-size 32
```

Para una prueba mas rapida, desactiva el chunker semantico:

```bash
.venv/bin/python src/sri_dx/app/cli/orchestrator.py \
  --skip-acquisition \
  --no-semantic-chunker \
  --embedding-device cpu \
  --embedding-batch-size 32
```

Para ejecutar solo indexacion de documentos y chunks, sin embeddings:

```bash
.venv/bin/python src/sri_dx/app/cli/orchestrator.py \
  --skip-acquisition \
  --skip-embeddings
```

Al terminar, deberias ver indices parecidos a:

```text
clinical_docs_v1
clinical_chunks_v1
clinical_embeddings_v1
```

Compruebalo:

```bash
curl http://localhost:9200/_cat/indices?v
```

## Ejecutar el orquestador dentro del contenedor

Tambien puedes correr el orquestador dentro del contenedor `sri-dx`.

En ese caso el host de OpenSearch es el nombre del servicio Docker:

```bash
docker compose exec sri-dx /app/.venv/bin/python \
  src/sri_dx/app/cli/orchestrator.py \
  --skip-acquisition \
  --host opensearch \
  --port 9200 \
  --embedding-device cpu \
  --embedding-batch-size 32
```

## Probar busquedas por CLI

El CLI principal es:

```text
src/sri_dx/app/cli/search_cli.py
```

### Busqueda lexica

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type lexical \
  --q "diabetes mellitus insulin treatment" \
  --k 5
```

### Busqueda semantica

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type semantic \
  --q "high blood pressure treatment" \
  --k 5
```

### Busqueda hibrida

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10
```

### Busqueda hibrida con reranking

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type hybrid \
  --q "chest pain shortness of breath fatigue" \
  --k 10 \
  --rerank
```

### Agregacion por enfermedades

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10 \
  --diseases \
  --max-diseases 5 \
  --min-ner-score 0.5
```

### Condiciones posicionadas

Este modo prueba el modulo de posicionamiento clinico:

```bash
.venv/bin/python src/sri_dx/app/cli/search_cli.py \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10 \
  --positioned \
  --positioned-results 5 \
  --show-component-scores
```

La salida debe incluir:

```text
rank
condicion clinica
etiqueta de relevancia
score final
sintomas o conceptos coincidentes
fuentes
explicacion
evidencias principales
scores por componente
```

## Probar CLI dentro del contenedor

Si estas ejecutando todo en Docker, puedes lanzar el CLI dentro de `sri-dx`.

Importante: dentro de Docker usa `--host opensearch`.

```bash
docker compose exec sri-dx /app/.venv/bin/python \
  src/sri_dx/app/cli/search_cli.py \
  --host opensearch \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10 \
  --positioned \
  --positioned-results 5 \
  --show-component-scores
```

## Consultas sugeridas

```text
fever cough shortness of breath
```

```text
chest pain shortness of breath fatigue
```

```text
diabetes mellitus insulin treatment hyperglycemia
```

```text
seizures epilepsy anticonvulsant medication
```

```text
multiple sclerosis neurological symptoms
```

## Pruebas unitarias rapidas

Suite del modulo de posicionamiento:

```bash
.venv/bin/python -m pytest tests/unit/modules/positioning
```

Suite enfocada usada para validar posicionamiento y use cases existentes:

```bash
.venv/bin/python -m pytest \
  tests/unit/modules/positioning \
  tests/unit/modules/indexing/test_concept_extractor.py \
  tests/unit/usecases
```

## Problemas comunes

### OpenSearch no esta listo

Revisa logs:

```bash
docker compose logs -f opensearch
```

Verifica salud:

```bash
curl http://localhost:9200/_cluster/health
```

### El indexador salta documentos

Borra el manifest:

```bash
rm -f data/index/manifest.sqlite \
      data/index/manifest.sqlite-journal \
      data/index/manifest.sqlite-shm \
      data/index/manifest.sqlite-wal
```

### Quieres empezar totalmente de cero

```bash
docker compose down -v
rm -f data/index/manifest.sqlite \
      data/index/manifest.sqlite-journal \
      data/index/manifest.sqlite-shm \
      data/index/manifest.sqlite-wal
docker compose up -d --build
```

### Memoria insuficiente

OpenSearch y los modelos pueden consumir bastante RAM. Si el proceso se cae:

- baja `--embedding-batch-size` a `16`;
- usa `--embedding-device cpu`;
- prueba `--no-semantic-chunker`;
- asigna mas memoria a Docker.
