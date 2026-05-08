# Guía de Integración UI - Módulo Web Search

Para que la interfaz de usuario (`frontend/src/App.tsx` y sus componentes asociados) pueda aprovechar el orquestador de Búsqueda Web (`SearchWebAndEnrichUseCase`), se recomiendan las siguientes incorporaciones arquitectónicas y visuales:

## 1. Botón o Toggle de "Búsqueda Web Profunda"
**Qué hacer:** Agregar un control (por ejemplo, un Switch o un botón con un ícono de la nube/internet) junto a la barra de búsqueda en `App.tsx` que permita al usuario decidir si desea habilitar la búsqueda en internet.
**Por qué:** La búsqueda web incluye indexado dinámico y re-ranking mediante modelos de lenguaje pesados, lo que incrementa el tiempo de respuesta. El usuario debe tener la opción de hacer una búsqueda local rápida o una profunda.

## 2. Indicador de "Evaluación de Suficiencia"
**Qué hacer:** Si la búsqueda devuelve resultados y el orquestador los evalúa como "Insuficientes", la UI debería mostrar un cuadro de aviso o alerta discreta debajo de la barra de búsqueda o encima de los resultados.
**Qué mostrar:**
- El estado: "⚠️ *La información local encontrada podría no ser óptima para tu consulta.*"
- La razón (`failed_criteria`): Por ejemplo, "Falta diversidad de fuentes" (low_source_diversity) o "Baja relevancia médica" (low_ranking_confidence).
- Un botón de acción rápida (si no estaba activo el toggle anterior): "🌐 Buscar en internet para mejorar resultados".

## 3. Feedback Visual de Progreso (Loading States)
**Qué hacer:** Dado que la búsqueda web tiene varias fases (Fase 1 local, Fase 3 consultas a APIs, Fase 6 indexado, Fase 7 re-ranking), el estado de `isSearching` debe enriquecerse.
**Por qué:** Una simple animación de "Cargando..." puede frustrar al usuario si el proceso toma 10 segundos.
**Cómo:** El backend debería enviar eventos (Server-Sent Events o WebSockets) o, al menos, la UI debería tener mensajes dinámicos:
- *"Buscando en bases locales..."*
- *"Resultados locales insuficientes, consultando PubMed y MedlinePlus..."*
- *"Analizando e indexando nuevos documentos clínicos..."*

## 4. Distintivo (Badge) de "Recuperado de la Web" en los Resultados
**Qué hacer:** En el componente que renderiza la lista de resultados (`ResultsSection`), los ítems deberían incluir una etiqueta o badge visual.
**Cómo:** Si un documento tiene metadatos que indican que proviene de una API externa (ej. `source_domain` como `pubmed.ncbi.nlm.nih.gov` o contiene un `PMID`), agregar un pequeño badge azul o verde que diga "🌐 Obtenido de Web" o "Reciente de PubMed".
**Por qué:** Aumenta la confianza del profesional médico al dejar claro qué resultados estaban en el corpus original y cuáles fueron traídos bajo demanda por el orquestador web.

## 5. Diseño Sugerido para `ResultsSection`
Modificar el renderizado de cada tarjeta de resultado para incluir:
- **Score de Confianza:** Mostrar de forma visual (ej. barras de colores) si la IA tiene alta confianza en la respuesta (scores positivos altos) o baja confianza (scores negativos).
- **Metadatos Originales:** Enlaces directos (URLs) a la fuente (MedlinePlus o PubMed) si el documento fue asimilado desde la web.

---

## Anexo: Arquitectura Backend Implementada (¿De dónde sale la información?)

Para mostrar los indicadores de "Evaluación de Suficiencia" en la UI **sin haber disparado la búsqueda web** (es decir, en una búsqueda local normal), el backend expone ahora esta información. Esto se logró enriqueciendo el endpoint de búsqueda local actual (`/api/search`).

### Archivos Clave Modificados para la Integración

1. **Endpoint Modificado (`src/sri_dx/app/api/main.py`):**
   El endpoint `/api/search` instancia el `LocalSufficiencyEvaluator` y extrae síntomas de la `query` para generar un reporte de suficiencia on-the-fly.
   
2. **Lógica de Suficiencia (`src/sri_dx/modules/web_search/sufficiency.py`):**
   Aquí se encuentra la clase `LocalSufficiencyEvaluator` y sus criterios (ej. diversidad de fuentes, relevancia médica).
   
3. **Esquemas de Datos (`src/sri_dx/modules/web_search/schemas.py`):**
   Define la estructura `SufficiencyDecision` y `LocalRetrievalResult` que se devuelven al cliente.

### 1. Estructura del Payload JSON

El endpoint `/api/search` devuelve ahora el campo `sufficiency` junto con los `results`. Al consumir la API desde el frontend, el payload será el siguiente:

```json
{
  "query": "fever and chest pain",
  "results": [ ... ],
  "sufficiency": {
    "sufficient": false,
    "insufficiency_score": 0.707,
    "rank_confidence": 0.45,
    "useful_count": 2,
    "symptom_coverage": 0.5,
    "source_diversity": 1,
    "failed_criteria": ["low_ranking_confidence", "few_useful_docs", "low_source_diversity"]
  }
}
```

### 2. Mapeo en el Frontend (`App.tsx`)

Para realizar la integración visual en la UI, se recomienda mapear la respuesta de la siguiente forma:

- **`response.sufficiency.sufficient`**: Dicta si se debe mostrar el aviso "⚠️ La información local podría no ser óptima".
- **`response.sufficiency.failed_criteria`**: Sirve para mapear el mensaje exacto (ej. si incluye `"low_source_diversity"`, mostrar *"Falta diversidad de fuentes"*).
- **`result.metadata.source_domain` o `result.doc_id`**: En cada elemento de `results`, se debe leer el `source_domain` en sus metadatos (comprobando si el dominio pertenece a PubMed, MedlinePlus, etc.) para mostrar un badge de "🌐 Recuperado de la Web".
