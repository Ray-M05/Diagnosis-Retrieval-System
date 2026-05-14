from __future__ import annotations

import re


class SynonymExpander:

    def __init__(self, synonyms: dict[str, list[str]] | None = None) -> None:
        self.synonyms = synonyms or {
            "dyspnea": ["shortness of breath", "difficulty breathing", "breathlessness"],
            "chest pain": ["chest discomfort", "thoracic pain", "angina"],
            "fever": ["febrile illness", "pyrexia", "elevated temperature"],
            "fatigue": ["tiredness", "weakness", "malaise"],
            "headache": ["cephalgia", "migraine"],
            "cough": ["productive cough", "dry cough"],
            "nausea": ["queasiness"],
            "vomiting": ["emesis"],
            "hypertension": ["high blood pressure", "HTN"],
            "hyperglycemia": ["high blood sugar"],
            "myocardial infarction": ["heart attack", "MI"],
            "urinary tract infection": ["UTI", "dysuria", "urinary frequency"],
            "chronic obstructive pulmonary disease": ["COPD", "chronic bronchitis", "emphysema"],
            "heart failure": ["congestive heart failure", "CHF"],
            "pulmonary embolism": ["PE", "pleuritic chest pain"],
            "diabetic ketoacidosis": ["DKA", "ketosis"],
            "abdominal pain": ["stomach pain", "epigastric pain"],
        }

    def expand(self, query: str, max_terms: int = 12) -> str:
        query_clean = query.strip()
        query_lower = query_clean.lower()
        expansion_terms: list[str] = []

        for canonical_term, variants in self.synonyms.items():
            if self._contains_term(query_lower, canonical_term):
                expansion_terms.extend(variants)

            for variant in variants:
                if self._contains_term(query_lower, variant):
                    expansion_terms.append(canonical_term)
                    expansion_terms.extend(variants)

        unique_terms: list[str] = []
        seen: set[str] = set()
        for term in expansion_terms:
            normalized = term.lower()
            if normalized in seen or normalized in query_lower:
                continue
            seen.add(normalized)
            unique_terms.append(term)
            if len(unique_terms) >= max_terms:
                break

        if not unique_terms:
            return query
        return f"{query_clean} {' '.join(unique_terms)}"

    @staticmethod
    def _contains_term(query_lower: str, term: str) -> bool:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(term.lower()) + r"(?![a-zA-Z0-9])"
        return re.search(pattern, query_lower) is not None
