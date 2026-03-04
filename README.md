# SRI-DX: Diagnosis Retrieval System

Este proyecto es un Sistema de Recuperación de Información (SRI) especializado en búsquedas clínicas y diagnósticas. Utiliza una arquitectura hexagonal para separar el dominio de las implementaciones tecnológicas y emplea `uv` para garantizar la reproducibilidad.

## 🏗️ Arquitectura

La estructura sigue un patrón hexagonal distribuido en módulos:

- **Core**: Modelos de datos (`schemas`) e interfaces (`ports`).
- **Use Cases**: Orquestación del flujo de negocio.
- **Modules**: Implementaciones específicas de los componentes del SRI (Indexación, Vector Store, RAG, etc.).
- **Adapters**: Controladores para servicios externos y persistencia.
- **App**: Puntos de entrada (CLI y Streamlit).

📖 **[Ver Documentación Completa de Arquitectura](ARQUITECTURA.md)**

## 🚀 Inicio Rápido

### ✅ Requisitos Previos

**Solo necesitas:**
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

**¡Eso es todo!** No necesitas Python, Elasticsearch, ni ninguna otra dependencia local.

### 🐳 Ejecución con Docker (Recomendado)

Este es el método más simple y garantiza que todo funcione sin configuración adicional:

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd Diagnosis-Retrieval-System

# 2. Levantar todos los servicios
docker compose up --build
```

Esto iniciará:
- ✅ Elasticsearch (base de datos e índice de búsqueda)
- ✅ Aplicación SRI-DX con interfaz web

**Acceder a la aplicación:**
- Interfaz web Streamlit: http://localhost:8501
- Elasticsearch API: http://localhost:9200

**Detener los servicios:**
```bash
docker compose down

# Para eliminar también los datos persistentes:
docker compose down -v
```

### 💻 Instalación Local (Desarrollo)

Si prefieres ejecutar la aplicación localmente (útil para desarrollo):

#### Requisitos
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Gestor de paquetes rápido)

#### Instalación de UV
```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# O con pip
pip install uv
```

#### Configurar Entorno

```bash
# 1. Sincronizar entorno virtual e instalar dependencias
uv sync

# 2. Copiar archivo de configuración (si no existe)
# El archivo .env ya está creado con valores por defecto

# 3. Levantar solo Elasticsearch con Docker
docker compose up -d elasticsearch

# 4. Ejecutar la interfaz Streamlit
uv run streamlit run src/sri_dx/app/ui_streamlit.py
```

### 🔧 Comandos Útiles

#### Con Docker Compose
```bash
# Ver logs en tiempo real
docker compose logs -f

# Solo logs de la aplicación
docker compose logs -f sri-dx

# Solo logs de Elasticsearch
docker compose logs -f elasticsearch

# Reiniciar un servicio específico
docker compose restart sri-dx

# Reconstruir contenedores
docker compose up --build --force-recreate
```

#### Con UV (Desarrollo Local)
```bash
# Ejecutar CLI
uv run python -m sri_dx.app.cli --help

# Ejecutar script de indexación
uv run python scripts/build_indexes.py

# Ejecutar pruebas
uv run pytest

# Formatear código
uv run ruff format .

# Verificar calidad de código
uv run ruff check .
```

## 📂 Estructura del Proyecto

```
Diagnosis-Retrieval-System/
├── .env                    # Variables de entorno (créalo desde .env.example)
├── .env.example            # Plantilla de configuración
├── docker-compose.yml      # Orquestación de servicios
├── Dockerfile              # Imagen de la aplicación
├── pyproject.toml          # Configuración de dependencias
├── uv.lock                 # Lock file para reproducibilidad
├── ARQUITECTURA.md         # Documentación detallada de arquitectura
│
├── doc/
│   ├── dev/
│   │   ├── architecture.md # Arquitectura hexagonal
│   │   └── uv_workflow.md  # Guía de UV
│   └── prod/
│       └── deployment.md   # Guía de deployment
│
├── scripts/
│   ├── build_indexes.py    # Script de indexación
│   └── smoke_test.py       # Pruebas básicas
│
└── src/sri_dx/
    ├── core/               # Dominio (schemas, ports)
    ├── usecases/           # Lógica de aplicación
    ├── modules/            # Implementaciones SRI
    ├── adapters/           # Infraestructura
    └── app/                # Interfaces (UI, CLI)
```

## 🔧 Configuración

### Variables de Entorno

El archivo `.env` ya está configurado con valores por defecto. Si necesitas personalizarlo:

```dotenv
# Elasticsearch
ELASTICSEARCH_HOST=http://elasticsearch:9200
ELASTICSEARCH_INDEX=sri_dx_diagnoses

# Modelo de embeddings
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# Rutas de datos
DATA_DIR=./data
INDEX_PATH=./data/artifacts/index.bin

# Configuración de aplicación
APP_NAME=SRI-DX
DEBUG=true
```

## 🧪 Testing

```bash
# Con UV
uv run pytest

# Con Docker
docker compose run --rm sri-dx uv run pytest
```

## 🛠️ Gestión de Dependencias

### Añadir Nueva Dependencia

```bash
# Dependencia principal
uv add nombre-paquete

# Dependencia de desarrollo
uv add --dev pytest-cov

# Dependencia opcional (grupo)
uv add --optional ui streamlit
```

### Actualizar Dependencias

```bash
# Actualizar todas las dependencias
uv lock --upgrade

# Actualizar paquete específico
uv lock --upgrade-package nombre-paquete
```

> **⚠️ Importante**: Siempre commitea `uv.lock` en Git para garantizar reproducibilidad.

## 📊 Monitoreo

### Verificar Estado de Elasticsearch

```bash
# Salud del cluster
curl http://localhost:9200/_cluster/health

# Listar índices
curl http://localhost:9200/_cat/indices?v

# Ver documentos indexados
curl http://localhost:9200/sri_dx_diagnoses/_count
```

## 🚨 Solución de Problemas

### El contenedor de Elasticsearch no inicia
```bash
# Verificar logs
docker compose logs elasticsearch

# Aumentar memoria disponible para Docker Desktop
# Settings → Resources → Memory (mínimo 4GB recomendado)
```

### Error: "Elasticsearch connection refused"
```bash
# Verificar que Elasticsearch esté corriendo
docker compose ps

# Esperar a que pase el healthcheck
docker compose logs -f elasticsearch | grep "started"
```

### Cambios en el código no se reflejan
```bash
# Para cambios en dependencias, rebuild
docker compose up --build

# Para cambios en código Python, ya tiene hot-reload automático
# Solo guarda el archivo y recarga la página de Streamlit
```

### Limpiar todo y empezar de cero
```bash
# Detener y eliminar contenedores + volúmenes
docker compose down -v

# Eliminar imágenes
docker rmi sri-dx-app

# Reconstruir desde cero
docker compose up --build
```

## 📚 Documentación Adicional

- **[ARQUITECTURA.md](ARQUITECTURA.md)**: Documentación técnica completa
  - Flujo de datos
  - Componentes y tecnologías
  - Guías de extensión
  - Mejores prácticas

- **[doc/dev/PLAN_IMPLEMENTACION_VECTORIAL.md](doc/dev/PLAN_IMPLEMENTACION_VECTORIAL.md)**: Plan detallado del sistema vectorial ⭐
  - Chunking inteligente de documentos médicos
  - Generación de embeddings (BioBERT, PubMedBERT)
  - Indexación vectorial (ANN/KNN con HNSW)
  - Búsqueda híbrida (vectorial + léxica)
  - Operaciones de conjuntos (AND, OR, NOT)
  - Sistema de metadatos médicos
  - Cronograma de 12 semanas

- **[doc/dev/RESUMEN_PLAN_VECTORIAL.md](doc/dev/RESUMEN_PLAN_VECTORIAL.md)**: Resumen ejecutivo del plan vectorial

- **[doc/dev/architecture.md](doc/dev/architecture.md)**: Patrón hexagonal
- **[doc/dev/uv_workflow.md](doc/dev/uv_workflow.md)**: Guía de desarrollo con UV
- **[doc/prod/deployment.md](doc/prod/deployment.md)**: Deployment en producción

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commitea tus cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Convenciones de Código

```bash
# Antes de hacer commit
uv run ruff format .  # Formatear código
uv run ruff check .   # Verificar linting
uv run pytest         # Ejecutar tests
```

## 📄 Licencia

Este proyecto es parte de un trabajo académico.

## 🙋 Soporte

Si tienes problemas:
1. Revisa la sección [Solución de Problemas](#-solución-de-problemas)
2. Consulta la [documentación de arquitectura](ARQUITECTURA.md)
3. Abre un issue en el repositorio

## 🎯 Roadmap

- [x] Arquitectura hexagonal base
- [x] Integración con Elasticsearch
- [x] Docker Compose completo
- [x] Interfaz Streamlit
- [x] Pipeline de embeddings
- [ ] Implementación RAG completa
- [ ] API REST con FastAPI
- [ ] Métricas de evaluación (NDCG, MAP)
- [ ] CI/CD pipeline

---

**¿Primera vez clonando el proyecto?** Solo ejecuta:
```bash
docker compose up --build
```

¡Y ya está! 🎉
