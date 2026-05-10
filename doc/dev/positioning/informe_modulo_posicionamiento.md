# Informe técnico: implementación del módulo de posicionamiento

## 1. Propósito del módulo

El módulo de posicionamiento tiene como objetivo transformar la salida técnica del recuperador en una lista final de resultados clínicos ordenados, diversos, explicables y adecuados para la interfaz visual del sistema.

En el contexto del sistema de recuperación de información para apoyo al diagnóstico diferencial, el posicionamiento no debe interpretarse como una decisión diagnóstica. Su función es ordenar condiciones clínicas potencialmente asociadas a la consulta del usuario y presentar evidencias relevantes, trazables y comprensibles.

La idea central es:

> La búsqueda recupera candidatos; el posicionamiento decide qué resultados se muestran primero, cómo se agrupan, cómo se diversifican y cómo se explican al usuario.

El módulo se implementa como una etapa posterior al recuperador híbrido y al re-ranking profundo ya definidos en el sistema.

---

## 2. Relación con la arquitectura actual

El sistema ya cuenta con una arquitectura de recuperación basada en Neural Information Retrieval, complementada con señales semánticas y léxicas. La arquitectura actual puede resumirse así:

```text
Consulta del usuario
        ↓
Procesamiento de consulta
        ↓
Búsqueda semántica densa
        ↓
Búsqueda léxica BM25
        ↓
Fusión híbrida mediante RRF
        ↓
Re-ranking profundo con cross-encoder
        ↓
Lista de chunks/documentos candidatos
```

El módulo de posicionamiento se incorpora después de esta etapa:

```text
Consulta del usuario
        ↓
Recuperador híbrido
        ↓
Cross-encoder
        ↓
Módulo de posicionamiento clínico
        ↓
Resultados agrupados por condición clínica
        ↓
Evidencias seleccionadas
        ↓
Respuesta RAG / interfaz visual
```

La responsabilidad del nuevo módulo no es recuperar documentos desde cero, sino reorganizar y enriquecer los candidatos ya recuperados.

---

## 3. Algoritmo propuesto

Se propone implementar un:

> Algoritmo de Re-ranking Clínico Multicriterio con Diversificación basado en MMR.

También puede denominarse:

> Clinical MMR Re-ranking.

Este algoritmo combina dos ideas:

1. **Relevancia clínica multicriterio**: calcula qué tan útil es un resultado para la consulta.
2. **Diversificación mediante MMR**: evita que el ranking final contenga resultados redundantes o demasiado similares entre sí.

Esto resulta especialmente importante en un sistema de apoyo al diagnóstico diferencial, porque no conviene mostrar muchos fragmentos de la misma enfermedad si existen otras condiciones clínicas relevantes que también deben considerarse.

---

## 4. Entrada del módulo

El módulo recibe como entrada:

- Consulta original del usuario.
- Lista de síntomas detectados o normalizados.
- Lista de chunks/documentos candidatos devueltos por el recuperador.
- Scores generados por las etapas previas:
  - score BM25;
  - score vectorial;
  - score RRF;
  - score del cross-encoder.
- Metadatos de cada documento:
  - identificador del documento;
  - identificador del chunk;
  - título;
  - enfermedad o condición clínica asociada;
  - dominio de la fuente;
  - URL;
  - sección del documento;
  - fecha de adquisición;
  - tipo de contenido.

Una estructura sugerida para representar cada candidato es:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str

    title: str
    disease_name: Optional[str]
    source_url: str
    source_domain: str
    section: Optional[str]
    acquired_at: Optional[datetime]

    bm25_score: Optional[float]
    vector_score: Optional[float]
    rrf_score: Optional[float]
    cross_encoder_score: Optional[float]

    embedding: Optional[list[float]] = None
    metadata: Optional[dict] = None
```

El campo `disease_name` puede obtenerse de varias formas:

- desde el título del documento;
- desde metadatos del scraping;
- desde el encabezado principal;
- desde una entidad clínica detectada durante la indexación.

Para una primera versión, puede usarse el título del documento o el nombre principal de la página como aproximación razonable.

---

## 5. Salida del módulo

La salida del módulo no debe ser una lista plana de chunks. Debe ser una lista de resultados clínicos posicionados, donde cada resultado representa una enfermedad o condición clínica candidata.

Estructura sugerida:

```python
from dataclasses import dataclass
from typing import List


@dataclass
class PositionedClinicalResult:
    rank: int
    disease_name: str
    final_score: float
    relevance_label: str

    matched_symptoms: List[str]
    evidences: List[RetrievedChunk]
    explanation: List[str]

    source_domains: List[str]
    display_group: str
```

Ejemplo conceptual de salida:

```json
{
  "rank": 1,
  "disease_name": "Pneumonia",
  "final_score": 0.87,
  "relevance_label": "Alta",
  "matched_symptoms": [
    "fever",
    "cough",
    "shortness of breath"
  ],
  "explanation": [
    "Alta relevancia semántica con la consulta.",
    "Coincide con varios síntomas introducidos por el usuario.",
    "La evidencia procede de una fuente médica confiable.",
    "El resultado aporta información no redundante respecto a otros resultados mostrados."
  ]
}
```

---

## 6. Relevancia clínica multicriterio

Para cada grupo clínico `g`, correspondiente a una enfermedad o condición, se calcula una puntuación de relevancia:

```text
Rel(g, q) =
    α · CE(g, q)
  + β · RRF(g)
  + γ · Coverage(g, S)
  + δ · Authority(g)
  + ε · Freshness(g)
```

Donde:

- `g`: grupo clínico, por ejemplo "neumonía".
- `q`: consulta del usuario.
- `S`: síntomas detectados en la consulta.
- `CE(g, q)`: relevancia según el cross-encoder.
- `RRF(g)`: score proveniente de la fusión híbrida.
- `Coverage(g, S)`: cobertura de síntomas.
- `Authority(g)`: confiabilidad de la fuente.
- `Freshness(g)`: frescura del contenido.

Pesos iniciales recomendados:

```text
α = 0.45   cross-encoder
β = 0.20   RRF
γ = 0.15   cobertura de síntomas
δ = 0.15   autoridad de fuente
ε = 0.05   frescura
```

Estos pesos deben dejarse configurables para facilitar ajustes posteriores.

---

## 7. Normalización de scores

Antes de combinar scores heterogéneos, deben normalizarse. BM25, RRF, similitud vectorial y cross-encoder pueden estar en escalas diferentes.

Función sugerida:

```python
def minmax_normalize(values: list[float]) -> list[float]:
    if not values:
        return []

    min_value = min(values)
    max_value = max(values)

    if max_value == min_value:
        return [1.0 for _ in values]

    return [
        (value - min_value) / (max_value - min_value)
        for value in values
    ]
```

En caso de que el cross-encoder devuelva logits, puede aplicarse una sigmoide:

```python
import math


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))
```

---

## 8. Agrupación por enfermedad o condición clínica

El recuperador trabaja con chunks, pero el usuario necesita ver condiciones clínicas organizadas. Por tanto, el primer paso del módulo es agrupar los candidatos por enfermedad.

```python
from collections import defaultdict


def group_by_disease(candidates: list[RetrievedChunk]) -> dict[str, list[RetrievedChunk]]:
    groups = defaultdict(list)

    for candidate in candidates:
        key = (
            candidate.disease_name
            or candidate.title
            or candidate.document_id
        )

        groups[key].append(candidate)

    return dict(groups)
```

Esta agrupación evita que el ranking final muestre muchos chunks aislados de la misma enfermedad.

---

## 9. Agregación de evidencia por grupo

Para calcular el score de un grupo clínico no se deben sumar todos los chunks, porque eso favorecería injustamente los documentos más largos. Se recomienda combinar:

- el mejor chunk del grupo;
- el promedio de los tres mejores chunks;
- una señal moderada de densidad de evidencia.

Fórmula propuesta:

```text
GroupScore(g) =
    0.70 · best_chunk_score
  + 0.20 · avg_top_3_chunk_scores
  + 0.10 · evidence_density
```

Implementación sugerida:

```python
import math


def aggregate_scores(scores: list[float]) -> float:
    if not scores:
        return 0.0

    sorted_scores = sorted(scores, reverse=True)

    best = sorted_scores[0]
    top_3 = sorted_scores[:3]
    avg_top_3 = sum(top_3) / len(top_3)

    density = min(
        1.0,
        math.log(1 + len(sorted_scores)) / math.log(10)
    )

    return 0.70 * best + 0.20 * avg_top_3 + 0.10 * density
```

---

## 10. Cobertura de síntomas

La cobertura de síntomas mide cuántos de los síntomas introducidos por el usuario aparecen representados en las evidencias recuperadas.

Versión inicial:

```python
def symptom_coverage(
    symptoms: list[str],
    evidences: list[RetrievedChunk],
) -> tuple[float, list[str]]:
    if not symptoms:
        return 0.0, []

    combined_text = " ".join(
        chunk.text.lower()
        for chunk in evidences
    )

    matched_symptoms = []

    for symptom in symptoms:
        normalized_symptom = symptom.lower()
        if normalized_symptom in combined_text:
            matched_symptoms.append(symptom)

    coverage = len(matched_symptoms) / len(symptoms)
    return coverage, matched_symptoms
```

Versión mejorada con sinónimos clínicos:

```python
SYMPTOM_SYNONYMS = {
    "shortness of breath": [
        "dyspnea",
        "difficulty breathing",
        "breathlessness"
    ],
    "chest pain": [
        "thoracic pain",
        "chest discomfort"
    ],
    "fatigue": [
        "tiredness",
        "weakness"
    ],
    "fever": [
        "pyrexia",
        "high temperature"
    ]
}


def symptom_coverage_with_synonyms(
    symptoms: list[str],
    evidences: list[RetrievedChunk],
    synonyms: dict[str, list[str]],
) -> tuple[float, list[str]]:
    if not symptoms:
        return 0.0, []

    combined_text = " ".join(
        chunk.text.lower()
        for chunk in evidences
    )

    matched_symptoms = []

    for symptom in symptoms:
        terms = [symptom.lower()]
        terms.extend(
            synonym.lower()
            for synonym in synonyms.get(symptom.lower(), [])
        )

        if any(term in combined_text for term in terms):
            matched_symptoms.append(symptom)

    coverage = len(matched_symptoms) / len(symptoms)
    return coverage, matched_symptoms
```

Esta parte es especialmente importante en el dominio médico, porque una misma manifestación puede expresarse con lenguaje técnico o coloquial.

---

## 11. Autoridad de fuente

En salud, la confiabilidad de la fuente debe influir en el posicionamiento. Se recomienda mantener una tabla configurable de autoridad por dominio.

Ejemplo:

```python
SOURCE_RELIABILITY = {
    "medlineplus.gov": 1.00,
    "cdc.gov": 0.95,
    "who.int": 0.95,
    "mayoclinic.org": 0.95,
    "nhs.uk": 0.90,
}
```

Cálculo sugerido:

```python
def authority_score(
    evidences: list[RetrievedChunk],
    source_reliability: dict[str, float],
    default_score: float = 0.70,
) -> float:
    if not evidences:
        return default_score

    scores = [
        source_reliability.get(
            chunk.source_domain,
            default_score
        )
        for chunk in evidences
    ]

    return max(scores)
```

Se usa el máximo porque basta con que el grupo tenga evidencia fuerte proveniente de una fuente confiable para que esa autoridad se refleje en el resultado.

---

## 12. Frescura del contenido

La frescura puede ayudar a desempatar resultados, especialmente cuando la información proviene de búsqueda web reciente. Sin embargo, en medicina no debe dominar el ranking, porque muchos contenidos clínicos mantienen vigencia durante largos períodos.

Implementación sugerida:

```python
from datetime import datetime


def freshness_score(acquired_at: datetime | None) -> float:
    if acquired_at is None:
        return 0.5

    days = (datetime.now() - acquired_at).days

    if days <= 30:
        return 1.0

    if days <= 180:
        return 0.8

    if days <= 365:
        return 0.6

    return 0.4
```

Para un grupo con varias evidencias:

```python
def group_freshness_score(evidences: list[RetrievedChunk]) -> float:
    scores = [
        freshness_score(chunk.acquired_at)
        for chunk in evidences
    ]

    if not scores:
        return 0.5

    return max(scores)
```

---

## 13. Diversificación mediante MMR

Después de calcular la relevancia clínica de cada grupo, se aplica Maximal Marginal Relevance para construir el ranking final.

La fórmula es:

```text
MMR(g) = λ · Rel(g, q) - (1 - λ) · max Sim(g, r)
```

Donde:

- `g`: grupo candidato todavía no seleccionado.
- `r`: resultado ya seleccionado.
- `Rel(g, q)`: relevancia clínica del grupo.
- `Sim(g, r)`: similitud entre el grupo candidato y un resultado ya seleccionado.
- `λ`: parámetro de balance entre relevancia y diversidad.

Valor recomendado:

```text
λ = 0.75
```

Con este valor, el algoritmo prioriza la relevancia, pero penaliza resultados redundantes.

---

## 14. Cálculo de similitud entre grupos

La similitud entre grupos puede calcularse de varias formas.

### Opción A: similitud entre embeddings promedio

Si los chunks tienen embeddings disponibles:

```python
import numpy as np


def average_embedding(evidences: list[RetrievedChunk]) -> np.ndarray | None:
    embeddings = [
        np.array(chunk.embedding, dtype=float)
        for chunk in evidences
        if chunk.embedding is not None
    ]

    if not embeddings:
        return None

    return np.mean(embeddings, axis=0)


def cosine_similarity(
    vector_a: np.ndarray | None,
    vector_b: np.ndarray | None,
) -> float:
    if vector_a is None or vector_b is None:
        return 0.0

    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))
```

### Opción B: similitud léxica simple

Si no se quieren usar embeddings en esta etapa:

```python
def lexical_jaccard_similarity(text_a: str, text_b: str) -> float:
    terms_a = set(text_a.lower().split())
    terms_b = set(text_b.lower().split())

    if not terms_a or not terms_b:
        return 0.0

    return len(terms_a & terms_b) / len(terms_a | terms_b)
```

Para una primera versión, la similitud por embeddings promedio es preferible si ya están disponibles.

---

## 15. Pseudocódigo completo del algoritmo

```text
Algoritmo: Clinical MMR Re-ranking

Entrada:
    q: consulta del usuario
    S: síntomas detectados
    C: chunks candidatos recuperados
    k: cantidad de resultados finales

Salida:
    R: ranking final de condiciones clínicas

Pasos:

1. Normalizar los scores de los chunks:
       bm25_score
       vector_score
       rrf_score
       cross_encoder_score

2. Agrupar los chunks por enfermedad o condición clínica:
       G = group_by_disease(C)

3. Para cada grupo g en G:
       calcular CE(g, q)
       calcular RRF(g)
       calcular Coverage(g, S)
       calcular Authority(g)
       calcular Freshness(g)
       calcular Rel(g, q)

4. Inicializar R = []

5. Mientras |R| < k y existan grupos no seleccionados:
       Para cada grupo g no seleccionado:
            redundancy = max Sim(g, r), para cada r en R
            mmr_score = λ * Rel(g, q) - (1 - λ) * redundancy

       seleccionar g* con mayor mmr_score
       agregar g* a R

6. Para cada resultado en R:
       seleccionar las mejores evidencias
       generar explicación del posicionamiento
       asignar etiqueta de relevancia

7. Devolver R
```

---

## 16. Clase principal propuesta

```python
class ClinicalPositioningService:
    def __init__(
        self,
        source_reliability: dict[str, float],
        lambda_mmr: float = 0.75,
        top_evidences: int = 3,
        weights: dict[str, float] | None = None,
    ):
        self.source_reliability = source_reliability
        self.lambda_mmr = lambda_mmr
        self.top_evidences = top_evidences
        self.weights = weights or {
            "cross_encoder": 0.45,
            "rrf": 0.20,
            "symptom_coverage": 0.15,
            "authority": 0.15,
            "freshness": 0.05,
        }

    def position(
        self,
        query: str,
        symptoms: list[str],
        candidates: list[RetrievedChunk],
        top_k: int = 10,
    ) -> list[PositionedClinicalResult]:
        if not candidates:
            return []

        normalized_candidates = self._normalize_candidate_scores(candidates)
        groups = self._group_by_disease(normalized_candidates)
        scored_groups = self._score_groups(query, symptoms, groups)
        ranked_groups = self._mmr_rerank(scored_groups, top_k)
        return self._build_positioned_results(ranked_groups, symptoms)
```

---

## 17. Representación interna de grupos

Se recomienda crear una clase auxiliar para representar cada grupo clínico durante el ranking.

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClinicalGroup:
    disease_name: str
    evidences: list[RetrievedChunk]

    relevance_score: float = 0.0
    mmr_score: float = 0.0

    cross_encoder_score: float = 0.0
    rrf_score: float = 0.0
    symptom_coverage_score: float = 0.0
    authority_score: float = 0.0
    freshness_score: float = 0.0

    matched_symptoms: list[str] = field(default_factory=list)
    average_embedding: Optional[list[float]] = None
```

---

## 18. Cálculo de relevancia por grupo

```python
def compute_group_relevance(
    group: ClinicalGroup,
    weights: dict[str, float],
) -> float:
    return (
        weights["cross_encoder"] * group.cross_encoder_score
        + weights["rrf"] * group.rrf_score
        + weights["symptom_coverage"] * group.symptom_coverage_score
        + weights["authority"] * group.authority_score
        + weights["freshness"] * group.freshness_score
    )
```

El valor resultante debe mantenerse entre 0 y 1 si todas las señales fueron normalizadas correctamente.

---

## 19. Re-ranking MMR

```python
def mmr_rerank(
    groups: list[ClinicalGroup],
    top_k: int,
    lambda_mmr: float,
) -> list[ClinicalGroup]:
    selected: list[ClinicalGroup] = []
    remaining = groups.copy()

    while remaining and len(selected) < top_k:
        best_group = None
        best_score = float("-inf")

        for group in remaining:
            if not selected:
                redundancy = 0.0
            else:
                redundancy = max(
                    group_similarity(group, selected_group)
                    for selected_group in selected
                )

            mmr_score = (
                lambda_mmr * group.relevance_score
                - (1.0 - lambda_mmr) * redundancy
            )

            if mmr_score > best_score:
                best_score = mmr_score
                best_group = group

        best_group.mmr_score = best_score
        selected.append(best_group)
        remaining.remove(best_group)

    return selected
```

Función de similitud:

```python
def group_similarity(
    group_a: ClinicalGroup,
    group_b: ClinicalGroup,
) -> float:
    if group_a.average_embedding is not None and group_b.average_embedding is not None:
        return cosine_similarity(
            np.array(group_a.average_embedding),
            np.array(group_b.average_embedding),
        )

    text_a = " ".join(chunk.text for chunk in group_a.evidences)
    text_b = " ".join(chunk.text for chunk in group_b.evidences)

    return lexical_jaccard_similarity(text_a, text_b)
```

---

## 20. Selección de evidencias por resultado

Por cada condición clínica posicionada, deben mostrarse solo las mejores evidencias.

Reglas recomendadas:

- mostrar como máximo 2 o 3 evidencias;
- priorizar evidencias con mayor score del cross-encoder;
- evitar evidencias textualmente repetidas;
- preferir evidencias de secciones clínicas útiles, por ejemplo:
  - symptoms;
  - causes;
  - diagnosis;
  - overview;
  - treatment.

Implementación inicial:

```python
PREFERRED_SECTIONS = {
    "overview": 1.00,
    "symptoms": 1.00,
    "causes": 0.90,
    "diagnosis": 0.90,
    "treatment": 0.75,
}


def evidence_display_score(chunk: RetrievedChunk) -> float:
    ce_score = chunk.cross_encoder_score or 0.0
    section_score = PREFERRED_SECTIONS.get(
        (chunk.section or "").lower(),
        0.70,
    )

    return 0.80 * ce_score + 0.20 * section_score


def select_top_evidences(
    evidences: list[RetrievedChunk],
    top_n: int = 3,
) -> list[RetrievedChunk]:
    ranked = sorted(
        evidences,
        key=evidence_display_score,
        reverse=True,
    )

    return ranked[:top_n]
```

---

## 21. Explicación del posicionamiento

Cada resultado debe acompañarse de una explicación breve. Esto mejora la transparencia del sistema y facilita la defensa del proyecto.

Función sugerida:

```python
def generate_explanation(group: ClinicalGroup) -> list[str]:
    explanation = []

    if group.cross_encoder_score >= 0.75:
        explanation.append(
            "Alta relevancia semántica con la consulta del usuario."
        )

    if group.symptom_coverage_score >= 0.60:
        explanation.append(
            "Coincide con varios síntomas introducidos en la consulta."
        )

    if group.authority_score >= 0.90:
        explanation.append(
            "La evidencia procede de una fuente médica confiable."
        )

    if len(group.evidences) >= 3:
        explanation.append(
            "Existen varias evidencias recuperadas asociadas a esta condición."
        )

    explanation.append(
        "El resultado fue seleccionado considerando relevancia y diversidad respecto a otros resultados."
    )

    return explanation
```

---

## 22. Etiquetas de relevancia

Para la interfaz, es útil convertir el score numérico en una etiqueta comprensible.

```python
def relevance_label(score: float) -> str:
    if score >= 0.75:
        return "Alta"

    if score >= 0.50:
        return "Media"

    return "Baja"
```

Esta etiqueta no representa certeza diagnóstica. Solo expresa nivel de relevancia informativa para la consulta.

---

## 23. Integración con RAG

El módulo RAG debe consumir preferentemente los resultados ya posicionados.

Flujo recomendado:

```text
Resultados posicionados
        ↓
Top condiciones clínicas
        ↓
Top evidencias por condición
        ↓
Construcción de contexto RAG
        ↓
Respuesta generada
```

Esto evita que el generador reciba evidencia redundante, débil o mal organizada.

Ejemplo:

```python
def build_rag_context(
    positioned_results: list[PositionedClinicalResult],
    max_conditions: int = 5,
    evidences_per_condition: int = 2,
) -> str:
    blocks = []

    for result in positioned_results[:max_conditions]:
        blocks.append(f"Condition: {result.disease_name}")

        for evidence in result.evidences[:evidences_per_condition]:
            blocks.append(f"Source: {evidence.source_url}")
            blocks.append(f"Evidence: {evidence.text}")

    return "\\n\\n".join(blocks)
```

---

## 24. Integración con búsqueda web

Si el módulo de búsqueda web recupera documentos nuevos, estos deben pasar por el mismo flujo:

```text
Búsqueda web
        ↓
Scraping / limpieza
        ↓
Indexación
        ↓
Recuperación
        ↓
Posicionamiento
```

Cada documento recuperado desde la web debe tener metadatos adicionales:

```python
metadata = {
    "source_type": "web_dynamic",
    "first_seen_at": "...",
    "indexed": True,
}
```

En la interfaz, se recomienda marcar estos resultados:

```text
Resultado incorporado desde búsqueda web.
```

Esto permite diferenciar contenido previamente almacenado de contenido adquirido dinámicamente.

---

## 25. Estructura de archivos sugerida

Dependiendo de la organización actual del proyecto, se recomienda una estructura similar a esta:

```text
src/
  application/
    services/
      clinical_positioning_service.py

  domain/
    models/
      retrieved_chunk.py
      positioned_clinical_result.py
      clinical_group.py

  infrastructure/
    config/
      positioning_config.py

  presentation/
    schemas/
      positioning_response.py
```

Otra alternativa más compacta:

```text
src/
  positioning/
    __init__.py
    models.py
    service.py
    scoring.py
    mmr.py
    explanations.py
    config.py
```

---

## 26. Configuración sugerida

Archivo `positioning_config.py`:

```python
POSITIONING_WEIGHTS = {
    "cross_encoder": 0.45,
    "rrf": 0.20,
    "symptom_coverage": 0.15,
    "authority": 0.15,
    "freshness": 0.05,
}

SOURCE_RELIABILITY = {
    "medlineplus.gov": 1.00,
    "cdc.gov": 0.95,
    "who.int": 0.95,
    "mayoclinic.org": 0.95,
    "nhs.uk": 0.90,
}

POSITIONING_DEFAULTS = {
    "lambda_mmr": 0.75,
    "top_evidences": 3,
    "top_k": 10,
}
```

---

## 27. Endpoint sugerido

Si existe un endpoint de búsqueda, el posicionamiento debe integrarse allí.

Flujo sugerido:

```python
@app.post("/search")
def search(request: SearchRequest):
    query = request.query

    symptoms = symptom_extractor.extract(query)

    candidates = retrieval_service.retrieve(
        query=query,
        top_k=100,
    )

    reranked_candidates = reranker.rerank(
        query=query,
        candidates=candidates,
        top_k=50,
    )

    positioned_results = positioning_service.position(
        query=query,
        symptoms=symptoms,
        candidates=reranked_candidates,
        top_k=10,
    )

    rag_answer = rag_service.generate(
        query=query,
        positioned_results=positioned_results,
    )

    return {
        "query": query,
        "symptoms": symptoms,
        "answer": rag_answer,
        "results": positioned_results,
    }
```

---

## 28. Comportamiento esperado

Consulta:

```text
fever, dry cough and shortness of breath
```

Salida esperada:

```text
1. Pneumonia
   Relevancia: Alta
   Síntomas relacionados: fever, cough, shortness of breath
   Evidencias: 3
   Explicación:
   - Alta relevancia semántica con la consulta.
   - Coincide con varios síntomas.
   - Evidencia procedente de fuente confiable.
   - Resultado seleccionado por relevancia y diversidad.

2. COVID-19
   Relevancia: Alta
   Síntomas relacionados: fever, dry cough, shortness of breath
   Evidencias: 2

3. Bronchitis
   Relevancia: Media
   Síntomas relacionados: cough, shortness of breath
   Evidencias: 2
```

El sistema debe evitar salidas de este tipo:

```text
1. Pneumonia chunk A
2. Pneumonia chunk B
3. Pneumonia chunk C
4. Pneumonia chunk D
```

Porque eso sería redundante y poco útil para diagnóstico diferencial.

---

## 29. Consideraciones de seguridad médica

El sistema no debe presentar los resultados como diagnósticos automáticos.

Evitar frases como:

```text
Diagnóstico más probable: neumonía.
```

Usar frases como:

```text
Condiciones clínicas potencialmente asociadas a la consulta.
```

O:

```text
Resultados informativos recuperados para apoyar el análisis diferencial.
```

También se recomienda mostrar una advertencia breve:

```text
Este sistema no emite diagnósticos médicos. Los resultados muestran información recuperada desde fuentes clínicas para apoyar el análisis y la consulta.
```

---

## 30. Redacción sugerida para el informe académico

Puede incorporarse una sección similar a esta en el informe final:

```text
El módulo de posicionamiento se implementó como una etapa posterior al recuperador híbrido y al re-ranking profundo. Su objetivo es transformar la lista de fragmentos recuperados en una presentación ordenada, diversa y explicable de condiciones clínicas potencialmente asociadas a la consulta del usuario.

Para ello se diseñó un algoritmo de Re-ranking Clínico Multicriterio con Diversificación basado en Maximal Marginal Relevance. Primero, los fragmentos candidatos se agrupan por enfermedad o condición clínica. Luego, para cada grupo se calcula una relevancia clínica combinando la puntuación del cross-encoder, el score de fusión RRF, la cobertura de síntomas, la autoridad de la fuente y la frescura del contenido. Finalmente, se aplica MMR para seleccionar resultados que sean relevantes pero no redundantes entre sí.

Este enfoque resulta adecuado para el dominio de apoyo al diagnóstico diferencial, ya que permite mostrar al usuario un conjunto diverso de condiciones posibles, acompañadas de evidencia clínica trazable, sin emitir diagnósticos automáticos.
```

---

## 31. Tareas concretas para implementación con Codex

### Tarea 1: crear modelos de datos

Crear:

```text
RetrievedChunk
ClinicalGroup
PositionedClinicalResult
```

Los modelos deben permitir transportar scores, metadatos y evidencias desde el recuperador hasta la interfaz.

### Tarea 2: implementar normalización

Implementar funciones para normalizar:

```text
bm25_score
vector_score
rrf_score
cross_encoder_score
```

Usar normalización min-max por lote de resultados.

### Tarea 3: implementar agrupación por enfermedad

Agrupar candidatos usando:

```text
disease_name
title
document_id
```

en ese orden de prioridad.

### Tarea 4: implementar scoring multicriterio

Calcular para cada grupo:

```text
cross_encoder_score agregado
rrf_score agregado
symptom_coverage_score
authority_score
freshness_score
relevance_score
```

### Tarea 5: implementar MMR

Implementar selección iterativa usando:

```text
MMR(g) = λ · Rel(g, q) - (1 - λ) · max Sim(g, r)
```

El parámetro `λ` debe estar en configuración.

### Tarea 6: seleccionar evidencias

Para cada resultado clínico final, seleccionar las mejores evidencias usando:

```text
cross_encoder_score
sección del documento
no redundancia
```

### Tarea 7: generar explicación

Generar una lista de razones para cada resultado:

```text
- relevancia semántica;
- cobertura de síntomas;
- autoridad de fuente;
- cantidad de evidencia;
- diversidad frente a otros resultados.
```

### Tarea 8: integrar con endpoint de búsqueda

Modificar el flujo actual:

```text
retrieval → reranking → positioning → RAG/interfaz
```

### Tarea 9: ajustar interfaz

Mostrar:

```text
- nombre de la condición;
- etiqueta de relevancia;
- síntomas relacionados;
- evidencias principales;
- fuentes;
- explicación del posicionamiento.
```

---

## 32. Prompt sugerido para Codex

Se puede usar el siguiente prompt para iniciar la implementación:

```text
Implementa un módulo de posicionamiento clínico para el sistema de recuperación de información.

El módulo debe recibir como entrada una lista de chunks ya recuperados y re-rankeados por el sistema. Cada chunk contiene texto, título, enfermedad asociada, fuente, sección, fecha de adquisición, scores BM25, vectorial, RRF y cross-encoder.

Crea un servicio llamado ClinicalPositioningService que:
1. Normalice los scores de los candidatos.
2. Agrupe los chunks por enfermedad o condición clínica.
3. Calcule una relevancia clínica multicriterio para cada grupo usando cross_encoder_score, rrf_score, symptom_coverage, source_authority y freshness.
4. Aplique Maximal Marginal Relevance para construir un ranking final diverso.
5. Seleccione las mejores evidencias por resultado.
6. Genere una explicación textual del posicionamiento.
7. Devuelva una lista de PositionedClinicalResult.

Usa Python, dataclasses y funciones separadas para scoring, MMR, agrupación, explicación y configuración. El código debe ser modular, testeable y fácil de integrar con el endpoint de búsqueda existente.
```

---

## 33. Conclusión

El módulo de posicionamiento debe implementarse como una capa posterior al recuperador híbrido, no como un recuperador alternativo. Su valor está en convertir una lista de chunks en una presentación clínica organizada, diversa y explicable.

La solución recomendada es:

```text
Re-ranking Clínico Multicriterio + Diversificación MMR
```

Este enfoque cumple con la exigencia de implementar un algoritmo de posicionamiento, se adapta al dominio médico, aprovecha las señales ya generadas por el sistema y mejora la utilidad visual de los resultados para el usuario.
