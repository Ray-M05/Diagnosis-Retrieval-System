"""QueryComposer — builds retrieval queries from a clinical question + chart entities.

The semantic query is optimised for Bio_ClinicalBERT embeddings (fluent sentence).
The lexical query is a bag-of-key-terms optimised for BM25.
Both are passed to TwoStageRetrievalPipeline.search(semantic_query).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sri_dx.modules.rag.patient_chart_enricher import PatientChartEntities


@dataclass
class ComposedQuery:
    semantic_query: str          # fluent text → passed to pipeline.search()
    lexical_query: str           # bag-of-terms (informational, used if backend exposes it)
    concept_ids: list[str] = field(default_factory=list)
    language: str = "en"


class QueryComposer:
    """Combine the physician's free-text query with extracted chart entities."""

    # How many entities to include in each part
    MAX_SYMPTOMS = 8
    MAX_TREATMENTS = 4
    MAX_TESTS = 4

    def compose(
        self,
        user_query: str,
        entities: PatientChartEntities,
        language: str = "en",
    ) -> ComposedQuery:
        user_query = user_query.strip()

        # --- Semantic query (fluent, for BERT) ---
        parts: list[str] = [user_query] if user_query else []

        symptoms_str = ", ".join(entities.symptoms[: self.MAX_SYMPTOMS])
        if symptoms_str:
            parts.append(f"patient presenting with {symptoms_str}")

        treatments_str = ", ".join(entities.treatments[: self.MAX_TREATMENTS])
        if treatments_str:
            parts.append(f"on {treatments_str}")

        tests_str = ", ".join(entities.tests[: self.MAX_TESTS])
        if tests_str:
            parts.append(f"relevant tests: {tests_str}")

        semantic_query = ". ".join(parts).strip()
        if not semantic_query:
            semantic_query = "clinical diagnosis differential"

        # --- Lexical query (bag-of-terms, for BM25) ---
        lexical_terms: list[str] = []
        if user_query:
            lexical_terms.append(user_query)
        lexical_terms.extend(entities.symptoms[: self.MAX_SYMPTOMS])
        lexical_terms.extend(entities.treatments[: self.MAX_TREATMENTS])
        lexical_terms.extend(entities.tests[: self.MAX_TESTS])

        # deduplicate preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for t in lexical_terms:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                deduped.append(t)

        lexical_query = " ".join(deduped)

        return ComposedQuery(
            semantic_query=semantic_query,
            lexical_query=lexical_query,
            concept_ids=entities.concept_ids,
            language=language,
        )
