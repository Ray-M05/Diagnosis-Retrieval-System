# Despliegue en Producción (Docker)

Este documento detalla cómo levantar el sistema **SRI-DX** utilizando Docker, garantizando un entorno idéntico al de desarrollo.

## 🐳 Requisitos

- Docker 20.10+
- Docker Compose v2+

## 🚀 Levantando el servicio

Para iniciar la aplicación en modo producción:

```bash
docker compose up --build -d
```

### Explicación de los archivos de infraestructura:

1.  **Dockerfile**: Utiliza una imagen base ligera (`python:3.11-slim`) e incorpora `uv` para una instalación de dependencias ultrarrápida y determinística mediante `uv.lock`.
2.  **docker-compose.yml**:
    - Mapea el puerto **8501** (Streamlit).
    - Monta el volumen `./data` para persistencia de índices y corpus.
    - Carga las variables de entorno desde el archivo `.env`.

## ⚙️ Configuración (.env)

Asegúrate de tener configurado tu archivo `.env` basado en `.env.example`.

```bash
cp .env.example .env
# Edita el archivo .env con tus claves y rutas
```

## 📊 Monitoreo de Logs

Para ver qué está pasando dentro del contenedor:

```bash
docker compose logs -f sri-dx
```

## 🛑 Detener el sistema

```bash
docker compose down
```
