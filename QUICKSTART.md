# 🚀 Inicio Rápido - SRI-DX

## Para usuarios que solo quieren ejecutar el proyecto

### Requisitos
- Docker Desktop instalado
- Git (para clonar el repositorio)

### 3 Pasos Simples

#### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd Diagnosis-Retrieval-System
```

#### 2. Iniciar el sistema
```bash
docker compose up --build
```

#### 3. Acceder a la aplicación
Abre tu navegador en: http://localhost:8501

**¡Listo!** 🎉

---

## Verificar que todo funciona

### Elasticsearch
```bash
curl http://localhost:9200/_cluster/health
```

Deberías ver algo como:
```json
{"status":"green","number_of_nodes":1,...}
```

### Script de verificación
```bash
# Con Docker
docker compose run --rm sri-dx uv run python scripts/health_check.py

# Con uv local
uv run python scripts/health_check.py
```

---

## Detener el sistema

```bash
docker compose down

# Para eliminar también los datos:
docker compose down -v
```

---

## Problemas comunes

### "Port already in use"
Otro servicio está usando el puerto 8501 o 9200.

**Solución:**
```bash
# Ver qué está usando el puerto
netstat -ano | findstr :8501

# Cambiar el puerto en docker-compose.yml
# Por ejemplo: "8502:8501" en vez de "8501:8501"
```

### "Not enough memory"
Docker necesita más RAM.

**Solución:**
1. Abre Docker Desktop
2. Settings → Resources → Memory
3. Aumenta a mínimo 4GB
4. Reinicia Docker

### Los contenedores no inician
**Solución:**
```bash
# Ver los logs
docker compose logs

# Reiniciar desde cero
docker compose down -v
docker compose up --build
```

---

## Para desarrolladores

Si vas a modificar el código, revisa:
- [README.md](README.md) - Documentación completa
- [ARQUITECTURA.md](ARQUITECTURA.md) - Guía técnica detallada
- [doc/dev/uv_workflow.md](doc/dev/uv_workflow.md) - Workflow de desarrollo

---

**¿Dudas?** Abre un issue en el repositorio.
