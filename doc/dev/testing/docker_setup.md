# Guía de Entorno Docker

Debido a requisitos de seguridad de OpenSearch (versión >= 2.12) y la necesidad de manejar correctamente las dependencias de los modelos de Deep Learning (como los de HuggingFace), el entorno Dockerizado se ha actualizado.

Esta guía explica los comandos necesarios para desplegar y correr el sistema correctamente.

## 1. Levantar el Entorno (Setup Inicial)

Para inicializar la infraestructura local de OpenSearch junto con el frontend de Streamlit, debes hacer lo siguiente desde la raíz del proyecto:

1. Asegúrate de tener el Docker daemon corriendo.
2. Ejecuta el comando de docker compose:

```bash
docker compose up -d
```

### ¿Qué hace `docker compose up -d` ahora?

- Configura e inicializa de manera automática un default seguro para `OPENSEARCH_INITIAL_ADMIN_PASSWORD` (si no lo tienes seteado en un archivo `.env`).
- Inicializa dos contenedores:
  - `sri-dx-opensearch`: Base de datos de documentos e índices vectoriales K-NN (expuesto en `localhost:9200`).
  - `sri-dx-app`: Contenedor principal de la aplicación, configurado para no descargar ni recompilar dependencias críticas automáticamente para evitar timeouts de red. Expone la UI de Streamlit en `localhost:8501`.

## 2. Verificar el Estado

Para comprobar que OpenSearch y la aplicación estén corriendo de manera saludable:

```bash
docker ps
```

Deberías ver ambos contenedores con el status `Up`. En el caso del `sri-dx-opensearch`, espera a que indique `(healthy)`.

## 3. Logs y Depuración

Si notas que algo no funciona, puedes inspeccionar los registros de ambos servicios:

**Para OpenSearch:**

```bash
docker logs sri-dx-opensearch
```

Si ves `Cluster health status changed from [YELLOW] to [GREEN]`, el clúster está listo.

**Para la Aplicación Python:**

```bash
docker logs sri-dx-app
```

Esto te mostrará los registros del framework de Streamlit.

## 4. Dependencias y Modelos Neurales

El pipeline de generación de vectores (Chunks semánticos y Vectores) depende de conectarse en tiempo real a la API de **HuggingFace** durante su primera ejecución para descargar el modelo (`Bio_ClinicalBERT`).

Si tu conexión a internet local o de los servidores es inestable:

- **EVITA** correr el comando Orquestador completo (`Fase 3` y `Fase 4`) mediante el flag `--skip-chunks` y `--skip-embeddings`.
- O alternativamente, espera a tener una red estable antes de lanzar la indexación de _Chunks_ en el Docker, de modo que el modelo alcance a descargarse correctamente.

```bash
# Ejemplo de orquestación segura sin internet potente (Solo Fase 1 y Fase 2):
docker exec sri-dx-app uv run python src/sri_dx/app/cli/orchestrator.py --skip-chunks --skip-embeddings --host opensearch
```

## 5. Bajar el Entorno

Cuando termines de trabajar y quieras liberar los recursos en tu máquina:

```bash
docker compose down
```

_(Si agregas la bandera `-v` eliminará los volúmenes en donde se guardaron los índices de base de datos de OpenSearch, por lo que toda la indexación previa se perderá)._
