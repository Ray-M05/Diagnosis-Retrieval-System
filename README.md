# SRI-DX: Diagnosis Retrieval System

Este proyecto es un Sistema de Recuperación de Información (SRI) especializado en búsquedas clínicas y diagnósticas. Utiliza una arquitectura hexagonal para separar el dominio de las implementaciones tecnológicas y emplea `uv` para garantizar la reproducibilidad.

## 🏗️ Arquitectura

La estructura sigue un patrón hexagonal distribuido en módulos:

- **Core**: Modelos de datos (`schemas`) e interfaces (`ports`).
- **Use Cases**: Orquestación del flujo de negocio.
- **Modules**: Implementaciones específicas de los componentes del SRI (Indexación, Vector Store, RAG, etc.).
- **Adapters**: Controladores para servicios externos y persistencia.
- **App**: Puntos de entrada (CLI y Streamlit).

## 🚀 Quickstart

### Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Recomendado) o Docker

### Instalación Local (con uv)

```bash
# Sincronizar entorno e instalar dependencias
uv sync

# Ejecutar la interfaz Streamlit
uv run streamlit run src/sri_dx/app/ui_streamlit.py
```

### Ejecución con Docker

```bash
docker compose up --build
```

## 📂 Estructura del Repositorio

- `src/sri_dx/`: Código fuente principal.
- `data/`: Corpus, índices y artefactos persistidos.
- `scripts/`: Utilidades para construcción de índices y pruebas.
- `pyproject.toml`: Configuración de dependencias y proyecto.
