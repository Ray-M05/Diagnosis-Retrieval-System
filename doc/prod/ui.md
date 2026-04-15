# Documentación de la Interfaz de Usuario (SRI-DX)

Esta documentación detalla la estructura, conexión y modo de ejecución del frontend React y su integración con el motor de búsqueda SRI-DX mediante el API REST.

## 🏗️ Arquitectura y Conexión

El sistema utiliza una arquitectura desacoplada:

1.  **Frontend (UI)**: Aplicación React moderna construida con Vite, Tailwind CSS y Motion.
2.  **Backend (API)**: Servicio FastAPI que expone la lógica del motor de búsqueda e interactúa con OpenSearch.
3.  **Comunicación**: El frontend se comunica con el backend mediante peticiones HTTP (JSON) a los endpoints expuestos en el puerto `8000`.

### Estructura del Proyecto

```text
frontend/
├── src/
│   ├── components/       # Componentes visuales (Sidebar, Header, Results)
│   ├── services/         # api.ts (Lógica de comunicación con el backend)
│   ├── data/             # Definición de tipos y esquemas de datos
│   └── App.tsx           # Orquestador principal de la UI
src/sri_dx/app/api/
├── main.py               # Punto de entrada de FastAPI y definición de rutas
└── deps.py               # Inyección de dependencias (casos de uso de búsqueda)
```

## 🚀 Ejecución del Sistema

Existen dos métodos para levantar la interfaz y el API:

### Método A: Usando Docker (Recomendado)

Docker Compose orquesta todos los servicios necesarios (OpenSearch, API, y Aplicación).

```bash
# Levantar el sistema completo en segundo plano
docker compose up -d

# Si solo deseas levantar el API específicamente
docker compose up -d sri-dx-api
```

*   **API**: Accesible en `http://localhost:8000`
*   **UI (Streamlit)**: Accesible en `http://localhost:8501`
*   **UI (React)**: Debe levantarse localmente (ver abajo) o integrarse en Docker.

### Método B: Ejecución Local (Desarrollo)

Para una iteración rápida durante el desarrollo, se recomienda ejecutar los servicios por separado.

#### 1. Levantar el Backend (API)
Asegúrate de tener el entorno virtual activo y configurado.

```bash
# Desde la raíz del proyecto
uv run python -m sri_dx.app.api.main
```

#### 2. Levantar el Frontend (React)
Asegúrate de tener instaladas las dependencias de Node.js.

```bash
cd frontend
npm install  # Solo la primera vez
npm run dev
```

*   La UI estará disponible generalmente en `http://localhost:5173`.

## 📂 Componentes Principales de la UI

- **Sidebar**: Permite configurar los parámetros de búsqueda (Fusión, Candidatos, Reranking).
- **Header**: Barra de búsqueda centralizada con soporte para limpieza de términos.
- **ResultsSection**: Maneja los estados de carga y renderiza las tarjetas de resultados (`HybridCard` o `DiagnosticCard`) basándose en los datos reales del motor.
- **apiService**: Localizado en `frontend/src/services/api.ts`, traduce las interacciones del usuario en llamadas a `/api/search` o `/api/diagnose`.
