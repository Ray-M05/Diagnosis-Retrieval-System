# Despliegue en Producción (Docker)

Este documento detalla cómo levantar el sistema **SRI-DX** utilizando Docker, garantizando un entorno idéntico al de desarrollo.

## 🐳 Requisitos

- Docker 20.10+
- Docker Compose v2+

## 🎬 Inicialización del Proyecto

Sigue estos pasos para preparar el entorno antes de iniciar los servicios:

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/Diagnosis-Retrieval-System.git
    cd Diagnosis-Retrieval-System
    ```

2.  **Configurar entono (.env):**
    Basado en el ejemplo, configura tus claves y rutas:
    ```bash
    cp .env.example .env
    # Edita .env con tus valores (OpenSearch host, etc.)
    ```

3.  **Descargar Modelos (Opcional pero Recomendado):**
    Para evitar que el contenedor tarde mucho en su primera ejecución o falle por mala conexión:
    ```bash
    uv run download-models
    ```
    *Esto almacenará los pesos de Bio_ClinicalBERT, NER y Cross-Encoder en tu caché local (`~/.cache/huggingface`).*

## 🚀 Levantando el servicio

Para iniciar la aplicación en modo producción (con OpenSearch):

```bash
docker compose -f docker-compose.yml -f docker-compose.opensearch.yml up --build -d
```

### Explicación de los archivos de infraestructura:

1.  **Dockerfile**: Utiliza una imagen base ligera (`python:3.11-slim`) e incorpora `uv` para una instalación de dependencias ultrarrápida y determinística mediante `uv.lock`.
2.  **docker-compose.yml**:
    - Mapea el puerto **8501** (Streamlit).
    - Monta el volumen `./data` para persistencia de índices y corpus.
    - Carga las variables de entorno desde el archivo `.env`.

## 📊 Monitoreo de Logs

Para ver qué está pasando dentro del contenedor:

```bash
docker compose logs -f sri-dx
```

## 🛑 Detener el sistema

```bash
docker compose down
```
