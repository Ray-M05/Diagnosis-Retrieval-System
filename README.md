# SRI-DX

Sistema de Recuperacion de Informacion clinica para apoyo al analisis
diferencial.

El proyecto esta compuesto por:

- **OpenSearch** para indices lexicos, chunks y embeddings.
- **FastAPI** como backend HTTP para busqueda, RAG, feedback y evaluacion.
- **React + Vite** como frontend, dentro de `frontend/`.

## Requisitos

- Docker y Docker Compose.
- Python 3.11+ si vas a ejecutar comandos fuera de Docker.
- `uv` recomendado para el entorno Python local.
- Node.js 18+ y npm para correr el frontend local.

La primera ejecucion puede descargar modelos de HuggingFace para embeddings,
NER y reranking. Esa parte puede tardar.

## Servicios y puertos

El `docker-compose.yml` actual levanta estos servicios:

```text
opensearch   -> http://localhost:9200
sri-dx-api   -> FastAPI en http://localhost:8000
```

El frontend **no se levanta con Docker Compose**. Se corre localmente con Vite:

```text
frontend     -> React/Vite en http://localhost:5173
```

La UI llama al backend en `http://localhost:8000` por defecto. Si necesitas otro
backend, define `VITE_API_BASE` en `frontend/.env.development`.

## Inicio rapido: backend + frontend

Desde la raiz del repo, crea `.env` a partir de la plantilla versionada:

```bash
cp .env.example .env
```

En PowerShell:

```powershell
Copy-Item .env.example .env
```

El archivo `.env` queda solo para tu maquina y no debe subirse al repo. Edita
ese archivo local para completar claves privadas como `GROQ_API_KEY`,
`UMLS_API_KEY` u otros valores propios del entorno.

Levanta OpenSearch y la API:

```bash
docker compose up -d --build
```

Verifica que OpenSearch y FastAPI esten arriba:

```bash
curl http://localhost:9200/_cluster/health
curl http://localhost:8000/health
```

En otra terminal, levanta el frontend:

```bash
cd frontend
npm install
npm run dev
```

Abre:

```text
http://localhost:5173
```

Notas:

- `npm install` solo hace falta la primera vez o cuando cambie
  `frontend/package-lock.json`.
- Vite usa el puerto `5173` por defecto. Si esta ocupado, Vite puede ofrecer otro
  puerto en la terminal.
- Las funcionalidades de busqueda necesitan OpenSearch indexado.
- Las funcionalidades RAG con generacion necesitan `GROQ_API_KEY` en `.env`; si
  no esta configurado, `/health` puede aparecer como `degraded`, pero la busqueda
  puede seguir funcionando si OpenSearch esta listo.

## Ejecutar solo backend con Docker

Levantar todos los servicios definidos en Compose:

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker compose logs -f
```

Ver logs solo de la API:

```bash
docker compose logs -f sri-dx-api
```

Detener servicios:

```bash
docker compose down
```

Detener y borrar volumenes de OpenSearch:

```bash
docker compose down -v
```

## Ejecutar la API localmente, sin Docker

Si prefieres correr FastAPI fuera del contenedor, deja OpenSearch en Docker:

```bash
docker compose up -d opensearch
```

Instala dependencias del backend, incluyendo extras de API y RAG:

```bash
uv sync --extra api --extra rag
```

Arranca la API local:

```bash
uv run python -m sri_dx.app.api.run
```

La API queda en:

```text
http://localhost:8000
```

Tambien puedes usar Uvicorn directamente:

```bash
uv run python -m uvicorn sri_dx.app.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

## Preparar indices con datos locales

La ruta recomendada usa los JSONL existentes:

```text
data/processed/docs_html.jsonl
data/processed/docs_pdf.jsonl
```

Si solo vas a preparar indices y probar por CLI local, puedes levantar solo
OpenSearch:

```bash
docker compose up -d opensearch
```

Espera a que OpenSearch este saludable:

```bash
curl http://localhost:9200/_cluster/health
```

### Forzar reindexado

El manifest incremental evita reindexar documentos que no cambiaron. Para forzar
un reindexado, borralo:

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

### Ejecutar el orquestador local

El orquestador real esta en:

```text
src/sri_dx/app/cli/orchestrator.py
```

Ejecuta automaticamente:

```text
Fases 2+3: indexacion de documentos y chunks
Fase 4: generacion de embeddings
```

Como el repo ya tiene JSONL en `data/processed/`, normalmente se salta
adquisicion:

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

### Ejecutar el orquestador dentro del contenedor

Si la API esta levantada con Compose, puedes ejecutar comandos dentro del
contenedor `sri-dx-api`.

Dentro de Docker usa `--host opensearch`:

```bash
docker compose exec sri-dx-api /app/.venv/bin/python \
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

Si estas ejecutando la API con Docker, puedes lanzar el CLI dentro de
`sri-dx-api`.

Dentro de Docker usa `--host opensearch`:

```bash
docker compose exec sri-dx-api /app/.venv/bin/python \
  src/sri_dx/app/cli/search_cli.py \
  --host opensearch \
  --type hybrid \
  --q "fever cough shortness of breath" \
  --k 10 \
  --positioned \
  --positioned-results 5 \
  --show-component-scores
```

## Endpoints utiles de la API

```text
GET  /health
GET  /docs
POST /pipeline
POST /search/diseases
POST /rag/parse-chart
POST /rag/clinical
POST /feedback/relevance
POST /feedback/search/refine
POST /evaluation/run
GET  /evaluation/seed-qrels
GET  /evaluation/runs
```

La documentacion interactiva queda en:

```text
http://localhost:8000/docs
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

Build del frontend:

```bash
cd frontend
npm run build
```

## Problemas comunes

### El frontend abre, pero no responde la busqueda

Verifica que la API este arriba:

```bash
curl http://localhost:8000/health
```

Si usas un backend en otro puerto, configura `frontend/.env.development`:

```text
VITE_API_BASE=http://localhost:8000
```

Reinicia `npm run dev` despues de cambiar variables `VITE_*`.

### OpenSearch no esta listo

Revisa logs:

```bash
docker compose logs -f opensearch
```

Verifica salud:

```bash
curl http://localhost:9200/_cluster/health
```

### La API no encuentra OpenSearch

- Si la API corre en Docker, debe usar el host `opensearch`.
- Si la API corre localmente en tu maquina, debe usar `localhost`.

El codigo normaliza `OPENSEARCH_HOST=http://opensearch:9200` a `localhost`
cuando detecta que no esta dentro de Docker.

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

### Puerto ocupado

Puertos usados por defecto:

```text
5173 -> frontend Vite
8000 -> FastAPI
9200 -> OpenSearch
9600 -> OpenSearch performance analyzer
```

Cierra el proceso que este usando el puerto o cambia el puerto del servicio
correspondiente. Para Vite puedes usar:

```bash
cd frontend
npm run dev -- --port 3000
```

Si cambias el puerto del frontend, agrega ese origen en `SRI_CORS_ORIGINS` para
la API.

### Memoria insuficiente

OpenSearch y los modelos pueden consumir bastante RAM. Si el proceso se cae:

- baja `--embedding-batch-size` a `16`;
- usa `--embedding-device cpu`;
- prueba `--no-semantic-chunker`;
- asigna mas memoria a Docker.
