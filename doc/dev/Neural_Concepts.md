# Justificación del modelo no básico implementado
## Neural IR híbrido y multi-etapa para apoyo a diagnóstico diferencial

## 1. Qué modelo vamos a implementar

El modelo no básico que implementaremos es un **Modelo basado en Redes Neuronales**, específicamente un enfoque de **Neural Information Retrieval (Neural IR)**.

En nuestro proyecto, este modelo se concreta como una arquitectura de recuperación **híbrida y multi-etapa**, compuesta por:

1. **Recuperación semántica con embeddings clínicos**
2. **Búsqueda ANN** sobre la base vectorial
3. **Re-ranking** de candidatos
4. **Fusión híbrida** entre score semántico y score léxico

En términos prácticos, no estamos implementando “solo embeddings”, sino un recuperador completo que combina:

- **Bi-encoder** para recuperar candidatos con alto recall
- **ANN** para búsqueda eficiente
- **Cross-encoder o re-ranker ligero** para afinar precisión
- **BM25/TF-IDF + conceptos clínicos** para no perder coincidencias exactas importantes

---

## 2. Por qué usamos esta implementación específicamente

La decisión no es arbitraria. Esta implementación es la mejor para nuestro proyecto porque el problema que queremos resolver no es una búsqueda textual simple, sino la recuperación de evidencia clínica relevante a partir de síntomas escritos por un usuario.

Eso implica varios retos:

- el usuario puede escribir en lenguaje coloquial
- puede usar síntomas incompletos
- puede no emplear términos médicos exactos
- puede describir una misma idea clínica de muchas formas

Ejemplos:

- “falta de aire” vs “disnea”
- “opresión en el pecho” vs “dolor torácico”
- “me cuesta respirar” vs “dificultad respiratoria”

Un sistema puramente léxico no resuelve bien eso porque depende demasiado de la coincidencia exacta de palabras.

Por eso esta implementación es adecuada: porque combina **comprensión semántica** con **control léxico**.

### En concreto, esta implementación se escoge porque:

### a) El bi-encoder da alto recall
El bi-encoder transforma la consulta y los fragmentos en embeddings comparables en un mismo espacio vectorial.  
Eso permite recuperar candidatos aunque no compartan exactamente las mismas palabras.

### b) ANN hace viable la búsqueda
Como el corpus crecerá, no es realista comparar la consulta contra todos los fragmentos uno por uno.  
Por eso se usa búsqueda aproximada por vecinos cercanos (ANN), que permite recuperar los Top-k candidatos de forma rápida.

### c) El re-ranking mejora la precisión
La primera etapa prioriza no perder buenos candidatos.  
Luego, el re-ranker toma los mejores resultados y analiza con más detalle la relación entre la query y cada fragmento.

Aquí se refinan aspectos como:

- negaciones
- frases críticas
- temporalidad
- correspondencia fina entre evidencia y consulta

### d) La fusión híbrida evita errores del puro vectorial
Un sistema solo semántico puede recuperar cosas cercanas en significado, pero perder términos exactos raros o expresiones clínicas importantes.

Por eso se combina:

- **score neural**
- **score léxico**

Así se logra un sistema más robusto que un recuperador puramente denso o puramente léxico.

---

## 3. Por qué redes neuronales y no otro modelo no básico

La orientación permite varias familias de modelos no básicos, pero no todas se ajustan igual de bien a nuestro dominio.

## 3.1 Por qué no Booleano Difuso o Booleano Extendido

Esos modelos mejoran al booleano clásico, pero siguen siendo relativamente rígidos frente a variaciones de lenguaje.

Nuestro dominio requiere tolerar:

- sinonimia clínica
- reformulaciones
- consultas incompletas
- lenguaje coloquial

Un modelo booleano, incluso extendido, sigue dependiendo demasiado de los términos usados.

**Problema:** si el usuario no escribe el término exacto, el sistema pierde capacidad de recuperación.

**Conclusión:** no es la mejor opción para medicina clínica orientada a síntomas.

---

## 3.2 Por qué no LSI o modelos semánticos clásicos

LSI aporta una idea semántica interesante, pero trabaja con una semántica más global y menos contextual.

Nuestro proyecto necesita distinguir mejor entre relaciones clínicas específicas, no solo similitud temática general.

En medicina, el contexto importa mucho:

- síntomas principales
- signos de alarma
- pruebas diagnósticas
- temporalidad
- sección clínica del documento

Los embeddings modernos aprenden mejor estas relaciones que LSI.

**Conclusión:** Neural IR ofrece una semántica más útil, más actual y más compatible con la base vectorial que ya estamos construyendo.

---

## 3.3 Por qué no un modelo probabilístico puro

Los modelos probabilísticos clásicos son valiosos, pero como núcleo del sistema tienen una limitación fuerte: dependen bastante de cómo está expresada la consulta.

Eso en nuestro proyecto es un problema, porque:

- el usuario puede escribir de manera poco técnica
- los documentos médicos pueden usar terminología muy distinta
- la relación importante puede ser semántica, no literal

Por eso no usamos un modelo puramente probabilístico como corazón del recuperador.

En cambio, lo probabilístico puede quedar como **señal auxiliar** dentro del ranking híbrido.

**Conclusión:** lo probabilístico sí aporta, pero no como modelo central.

---

## 3.4 Por qué redes neuronales sí son la mejor opción

Elegimos redes neuronales porque permiten aprender representaciones semánticas densas del texto.

Eso es exactamente lo que necesitamos para conectar:

- síntomas expresados por un usuario
- terminología médica formal
- fragmentos clínicos relevantes
- evidencia útil para explicación posterior

En otras palabras: las redes neuronales son la mejor opción porque nuestro problema requiere **similitud semántica**, no solo coincidencia de términos.

---

## 4. Qué características de las redes neuronales están presentes en esta implementación

No basta con decir que “usa embeddings”.  
Lo correcto es identificar qué propiedades de los modelos neuronales están realmente presentes en nuestro diseño.

## 4.1 Representaciones densas aprendidas

Esta es la característica principal.

Consulta y documento no se representan como bolsas de palabras aisladas, sino como vectores densos que codifican significado.

### Dónde aparece:
- en los **embeddings clínicos**
- en la **base vectorial**
- en la comparación entre query y fragmentos

---

## 4.2 Captura de similitud semántica

La red neuronal permite que textos clínicamente relacionados queden cerca en el espacio vectorial aunque no compartan exactamente las mismas palabras.

### Dónde aparece:
- en el **bi-encoder**
- en la recuperación semántica inicial
- en la robustez ante sinonimia y parafraseo

---

## 4.3 Arquitectura dual o bi-encoder

La consulta y cada fragmento se codifican por separado con un encoder compatible.

Esto permite:

- precomputar embeddings de documentos
- consultar rápido en tiempo real
- escalar mejor que una comparación profunda contra todo el corpus

### Dónde aparece:
- en la etapa de **recuperación de candidatos**

---

## 4.4 Modelado contextual fino en el re-ranking

El re-ranker representa otra propiedad de los modelos neuronales: su capacidad para analizar relaciones más finas entre dos textos.

### Dónde aparece:
- en la etapa de **alta precisión**
- cuando se vuelve a ordenar el Top-N inicial
- cuando se evalúan negaciones, detalle contextual y correspondencia fina

---

## 4.5 Transformación no lineal del lenguaje

Un modelo neuronal no compara solo términos visibles.  
Aprende una función más compleja que transforma el texto en una representación interna útil para estimar relevancia.

### Dónde aparece:
- en el encoder de embeddings
- en el re-ranker
- en la similitud semántica que va más allá del matching exacto

---

## 5. Cómo se ubican estas características dentro de nuestra arquitectura

Nuestro sistema sigue una arquitectura modular y hexagonal mínima.  
Por eso, las partes neuronales no deben quedar mezcladas de manera desordenada con la lógica del dominio.

## 5.1 En `adapters/`
Aquí viven las implementaciones concretas ligadas a librerías o infraestructura externa:

- modelo de embeddings
- cliente de base vectorial
- posible re-ranker

Es decir, aquí vive la parte “tecnológica” neuronal.

---

## 5.2 En `use cases/` o `modules/`
Aquí vive la lógica del recuperador:

- recibir consulta
- pedir embeddings
- ejecutar recuperación semántica
- ejecutar recuperación léxica
- fusionar resultados
- devolver candidatos reordenados

Es decir, aquí no vive “la red neuronal como librería”, sino la orquestación del proceso de recuperación.

---

## 5.3 En el módulo 4
Aquí se materializa la parte vectorial:

- almacenamiento de embeddings
- índice ANN
- filtros por metadatos
- recuperación Top-k por similitud

---

## 5.4 En el módulo 2
Aquí está la parte complementaria no neuronal:

- índice invertido
- conceptos clínicos
- filtros y facetas
- soporte para trazabilidad y expansión

Esto es importante porque nuestro sistema no es solo neural: es **híbrido**.

---

## 6. Cómo se relaciona con lo que ya está hecho

Esta implementación no rompe lo que ya hicieron; al contrario, se apoya directamente en ello.

## 6.1 Relación con el módulo 1: adquisición
El módulo 1 produce documentos limpios, estructurados y con metadatos.

Eso es fundamental porque un buen recuperador neural depende de:

- corpus confiable
- segmentación razonable
- trazabilidad
- calidad documental

---

## 6.2 Relación con el módulo 2: indexación
El módulo 2 aporta:

- índice invertido
- conceptos clínicos
- campos estructurados
- filtros

Eso alimenta la parte léxica del sistema y fortalece la recuperación híbrida.

La indexación por conceptos es especialmente importante porque ayuda a mapear expresiones como:

- “falta de aire” → disnea
- “mareo” → vértigo
- otras variantes clínicas

Esto conecta muy bien con la recuperación semántica.

---

## 6.3 Relación con el módulo 4: base vectorial
El módulo 4 es la infraestructura natural del modelo neuronal.

Aporta:

- embeddings de documentos o fragmentos
- índice ANN
- búsqueda eficiente
- salida semántica Top-k con metadatos

Sin el módulo 4, la implementación neuronal no sería operativa.

---

## 6.4 Relación con el módulo 5: RAG
El módulo 3 no produce la respuesta final.  
Produce candidatos relevantes y trazables que luego el módulo RAG convierte en una salida explicable.

Eso exige que la recuperación sea buena semánticamente, pero también precisa y justificable.

Por eso el enfoque híbrido encaja tan bien: recupera mejor y luego explica mejor.

---

## 6.5 Relación con el módulo 6: posicionamiento
El módulo 6 combina señales adicionales para ordenar la salida final.

Ahí se aprovechan:

- score neural
- score léxico
- calidad de fuente
- nivel de evidencia
- recencia
- cobertura

Eso demuestra que nuestra implementación no está aislada, sino integrada en un ranking final clínicamente útil.

---

## 7. Por qué esta implementación convence más que otras

La razón principal es que resuelve mejor el problema real del proyecto.

Nuestro sistema debe:

- recibir síntomas en lenguaje natural
- recuperar evidencia médica relevante
- no depender de coincidencia literal exacta
- mantener trazabilidad
- producir una base sólida para RAG y ranking final

Esta implementación lo logra porque:

- **entiende similitud semántica**
- **escala con ANN**
- **refina con re-ranking**
- **mantiene control con recuperación léxica**
- **se integra perfectamente con los módulos ya implementados**

Dicho de forma simple:

- usar solo léxico sería demasiado rígido
- usar solo vectorial sería menos controlable
- usar otro modelo no básico sería menos natural para el dominio y menos compatible con lo ya construido

La implementación elegida es la más coherente técnica, teórica y arquitectónicamente.

---

## 8. Fuente bibliográfica principal

La fuente bibliográfica principal para la definición general del modelo es:

**Mitra, B., & Craswell, N. (2018). _An Introduction to Neural Information Retrieval_. Foundations and Trends in Information Retrieval, 13(1), 1–126.**

Fuentes complementarias para la implementación concreta:

**Reimers, N., & Gurevych, I. (2019). _Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks_.**

**Karpukhin, V. et al. (2020). _Dense Passage Retrieval for Open-Domain Question Answering_.**

---

## 9. Conclusión

Elegimos una implementación de **Neural IR híbrida y multi-etapa** porque es la que mejor se adapta a nuestro dominio de apoyo a diagnóstico diferencial.

No basta con buscar coincidencias exactas.  
Necesitamos recuperar evidencia clínica relevante aunque la consulta esté escrita de forma variable, incompleta o coloquial.

Por eso nuestra decisión no fue simplemente “usar redes neuronales”, sino usar una arquitectura concreta que combine:

- semántica
- eficiencia
- precisión
- control léxico
- integración con RAG
- compatibilidad con la arquitectura del sistema

Esa es la razón por la que esta implementación es la más defendible para nuestro proyecto.