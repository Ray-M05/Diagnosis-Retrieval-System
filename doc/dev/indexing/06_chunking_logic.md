# Indexing Module: Chunking Logic

El sistema implementa una estrategia de fragmentación (chunking) en dos niveles para optimizar tanto la búsqueda léxica como la recuperación semántica (RAG).

## Estrategia de Dos Niveles

### 1. Nivel Segmentación Clínica

En lugar de trocear el documento de forma arbitraria, el sistema respeta las secciones definidas por el extractor de contenido (HTML/PDF).

- **Beneficio**: Mantiene la cohesión temática. Un fragmento no mezclará contenido de "Antecedentes" con "Tratamiento" si están en secciones distintas.
- **Implementación**: Se itera sobre `doc.content.sections`.

### 2. Nivel Ventana con Overlap

Dentro de cada sección, si el texto supera el tamaño máximo (`max_chars`), se aplica una ventana deslizante.

- **Parámetros**:
  - `max_chars`: Tamaño objetivo del trozo (ej: 1200).
  - `overlap_chars`: Caracteres que se repiten del trozo anterior (ej: 200). Ayuda a no perder contexto en los bordes.
  - `min_chars`: Se descartan trozos residuales demasiado pequeños.
- **Inteligencia de Corte**: El algoritmo busca el espacio en blanco (`whitespace`) más cercano al límite de la ventana para evitar cortar palabras por la mitad.

## Trazabilidad y Tramos

Cada chunk generado mantiene punteros exactos al origen:

- `section_index`: Índice de la sección en el array original.
- `section_heading`: Nombre de la sección para dar contexto al LLM.
- `start_char` / `end_char`: Posición absoluta del fragmento dentro del texto de la sección.

## Soporte Vectorial (kNN)

El índice `clinical_chunks` está configurado con soporte nativo para búsqueda por proximidad en OpenSearch:

- **Engine**: `nmslib`.
- **Algoritmo**: `HNSW` (Hierarchical Navigable Small World).
- **Métrica**: Distancia `L2` (Euclídea) o Coseno.
- **Preparado para**: Embeddings de modelos como `bge-m3` o `multilingual-e5`.
