# Workflow de Desarrollo con `uv`

Para asegurar la reproducibilidad del entorno en todos los equipos (y en Docker), utilizamos **uv** como gestor de paquetes y entornos virtuales.

## 🛠️ Instalación de uv

Si no tienes `uv` instalado, puedes hacerlo con:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

O vía pip: `pip install uv`

## 🚀 Comandos Principales

### 1. Inicializar el entorno

La primera vez que clonas el repo, ejecuta:

```bash
uv sync
```

Esto creará una carpeta `.venv/` e instalará todas las dependencias exactamente como están definidas en `uv.lock`.

### 2. Ejecutar la aplicación

Usa siempre `uv run` para asegurarte de que se usa el entorno virtual correcto:

```bash
# Interfaz Visual
uv run streamlit run src/sri_dx/app/ui_streamlit.py

# CLI
uv run python -m sri_dx.app.cli --help
```

### 3. Gestionar Dependencias

- **Añadir una librería**: `uv add nombre-libreria`
- **Añadir dependencia de desarrollo**: `uv add --dev pytest`
- **Eliminar una librería**: `uv remove nombre-libreria`

> [!IMPORTANT]
> El archivo `uv.lock` **DEBE** versionarse en Git. Nunca lo añadas al `.gitignore`.

## 🧹 Calidad de Código

Antes de pushear, corre ruff para formatear y lintear:

```bash
uv run ruff check .
uv run ruff format .
```
