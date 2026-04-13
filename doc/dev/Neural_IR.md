# Modelo No Básico del Sistema de Recuperación

## Neural Information Retrieval (Neural IR) Híbrido

### Proyecto

Sistema de Recuperación para Apoyo a Diagnóstico Diferencial

---

# 1. Introducción

El sistema implementará como **modelo no básico de Recuperación de Información (IR)** un enfoque basado en **Redes Neuronales**, específicamente un modelo de **Neural Information Retrieval (Neural IR)** utilizando **representaciones densas (embeddings)**.

Este modelo permitirá recuperar documentos clínicos relevantes incluso cuando **no exista coincidencia literal entre los términos de la consulta y los documentos**, algo fundamental en el dominio médico debido a la gran cantidad de **sinónimos, variaciones lingüísticas y expresiones coloquiales** utilizadas para describir síntomas.

Ejemplo:

| Consulta del usuario     | Texto médico        |
| ------------------------ | ------------------- |
| falta de aire            | disnea              |
| opresión en el pecho     | dolor torácico      |
| dificultad para respirar | shortness of breath |

Un sistema léxico clásico fallaría en muchos de estos casos, mientras que un modelo basado en embeddings puede capturar la **similitud semántica** entre ellos.

---

# 2. Justificación del Modelo

La orientación del proyecto exige implementar **al menos un modelo no básico de recuperación de información**.

Entre las categorías aceptadas se encuentran:

- Modelo Booleano Difuso
- Modelo Vectorial Generalizado
- Latent Semantic Indexing (LSI)
- **Modelos basados en Redes Neuronales**
- Redes de Inferencia
- Redes de Creencia
- Modelos Probabilísticos de Lenguaje

El modelo elegido pertenece a la categoría:

**Modelos basados en Redes Neuronales**

Dentro de esta categoría se encuentra el enfoque moderno conocido como:

**Neural Information Retrieval (Neural IR)**

Por lo tanto, la implementación cumple completamente con el requisito de usar un **modelo avanzado de IR**.

---

# 3. Fundamento Teórico

## 3.1 Recuperación de Información Clásica

En los modelos clásicos la relevancia se calcula mediante coincidencia de términos.

Ejemplo:

```
score(q,d) = tf-idf(q,d)
```

o

```
score(q,d) = BM25(q,d)
```

Estos modelos dependen de que las palabras coincidan exactamente.

---

## 3.2 Recuperación Neural

En Neural IR, tanto consultas como documentos se transforman mediante una **red neuronal** en representaciones vectoriales llamadas **embeddings**.

Formalmente:

```
vector_q = f(q)
vector_d = f(d)
```

donde

```
f(x) = encoder neuronal
```

La relevancia se calcula mediante similitud vectorial:

```
score(q,d) = cosine(vector_q, vector_d)
```

Esto permite capturar similitud **semántica**, no solo coincidencia de palabras.

---

# 4. Arquitectura del Modelo

El sistema implementará un **recuperador híbrido multi-etapa**, combinando recuperación semántica con recuperación léxica.

## Arquitectura conceptual

```
             Consulta
                │
                ▼
        Módulo 3 (Retriever)
                │
      ┌─────────┴─────────┐
      │                   │
      ▼                   ▼
 Recuperación        Recuperación
   Léxica             Semántica
  (BM25)              (Neural IR)
      │                   │
      └─────────┬─────────┘
                ▼
           Fusión Ranking
                ▼
             Re-ranking
                ▼
         Top-N resultados
```

Este enfoque es estándar en motores de búsqueda modernos.

---

# 5. Tipo de Neural IR Implementado

El sistema utilizará un modelo conocido como:

**Dense Retrieval con Bi-Encoder**

también llamado:

- Dual Encoder
- Siamese Encoder

## Funcionamiento

### Paso 1 — Representación

Consulta y documento se codifican de forma independiente.

```
query → encoder → vector_q
doc   → encoder → vector_d
```

El encoder puede ser un modelo basado en transformadores como:

- Sentence-BERT
- BioBERT
- ClinicalBERT

---

### Paso 2 — Espacio Vectorial Semántico

Todos los textos se representan como vectores de alta dimensión.

Ejemplo:

```
"disnea"               → [0.12, -0.45, 0.91, ...]
"falta de aire"        → [0.14, -0.41, 0.88, ...]
```

Estos vectores quedan **cercanos en el espacio semántico**.

---

### Paso 3 — Búsqueda de Vecinos Cercanos

Se busca el documento con embedding más cercano a la consulta.

```
sim(q,d) = cosine(vector_q, vector_d)
```

---

### Paso 4 — Búsqueda Aproximada

Para acelerar la búsqueda se utiliza un índice ANN:

**Approximate Nearest Neighbor**

Ejemplos:

- HNSW
- FAISS
- ScaNN

En este proyecto se usará **HNSW**.

---

# 6. Relación con los Módulos del Proyecto

## Módulo 1 — Adquisición

Responsable de:

- obtener documentos médicos
- limpiar el contenido
- estructurar secciones

Estos documentos alimentan el sistema de indexación.

---

## Módulo 2 — Indexación

Construye:

- índice invertido
- índice de conceptos clínicos
- metadatos de documentos

Este módulo permite la **recuperación léxica**.

---

## Módulo 4 — Base Vectorial

Se encarga de:

- generar embeddings de documentos
- almacenar vectores
- construir índice ANN

Esto permite la **recuperación semántica**.

---

## Módulo 3 — Recuperador (este módulo)

Responsable de:

1. recibir la consulta
2. generar embedding de la query
3. buscar vecinos semánticos
4. ejecutar búsqueda léxica
5. fusionar resultados
6. devolver Top-N candidatos

---

# 7. Fusión Híbrida

La relevancia final combinará señales léxicas y semánticas.

Ejemplo:

```
score_final =
a * score_semantico +
(1-a) * score_lexico
```

Esto permite:

- aprovechar coincidencias exactas
- capturar similitud semántica

---

# 8. Re-Ranking

Después de recuperar candidatos se aplicará un re-ranking más preciso.

Objetivos:

- mejorar ordenamiento
- manejar negaciones
- capturar relaciones más complejas

Este paso puede usar:

- Cross Encoder
- modelo ligero adicional

---

# 9. Ventajas para Diagnóstico Diferencial

Este enfoque es especialmente adecuado para medicina porque:

- los síntomas tienen múltiples formas de expresarse
- las consultas pueden ser incompletas
- el lenguaje del usuario puede ser coloquial

Ejemplo:

```
usuario: "me cuesta respirar"
documento: "disnea progresiva"
```

Un modelo léxico puede fallar, pero el modelo semántico detecta la relación.

---

# 10. Ventajas del Enfoque Híbrido

| Recuperación | Ventaja                            |
| ------------ | ---------------------------------- |
| Léxica       | precisión en coincidencias exactas |
| Semántica    | comprensión del significado        |
| Híbrida      | mejor balance precisión/recall     |

Por esta razón los motores de búsqueda modernos utilizan **recuperación híbrida**.

---

# 11. Flujo de Consulta

El proceso completo será:

1. usuario introduce síntomas
2. sistema genera embedding de la consulta
3. se ejecuta búsqueda semántica en la base vectorial
4. se ejecuta búsqueda léxica en el índice invertido
5. se fusionan resultados
6. se aplica re-ranking
7. se devuelven Top-N documentos

---

# 12. Bibliografía

Mitra, B. & Craswell, N. (2018)
An Introduction to Neural Information Retrieval

Karpukhin et al. (2020)
Dense Passage Retrieval for Open-Domain Question Answering

Reimers, N. & Gurevych, I. (2019)
Sentence-BERT: Sentence Embeddings using Siamese BERT Networks

---

# 13. Conclusión

El sistema implementará un **modelo de recuperación basado en redes neuronales (Neural IR)** mediante **representaciones densas y búsqueda semántica**, combinado con recuperación léxica tradicional en un enfoque híbrido.

Este modelo permite capturar relaciones semánticas entre síntomas y evidencia médica incluso cuando no existe coincidencia textual directa, lo cual resulta fundamental para un sistema de apoyo al diagnóstico diferencial.
