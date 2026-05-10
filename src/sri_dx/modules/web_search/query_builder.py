"""
Pure functions that build API-specific query strings from a list of symptom terms.
"""
from __future__ import annotations


def build_medlineplus_query(symptoms: list[str]) -> str:
    """
    Build a plain-text query for MedlinePlus Web Service.

    MedlinePlus performs best with simple keyword lists rather than Boolean
    expressions.

    Examples
    --------
    >>> build_medlineplus_query(["chest pain", "shortness of breath"])
    'chest pain shortness of breath'
    >>> build_medlineplus_query([])
    ''
    """
    return " ".join(s.strip() for s in symptoms if s.strip())


def build_scientific_query(symptoms: list[str]) -> str:
    """
    Build a Boolean query suitable for Europe PMC and PubMed (NCBI E-Utilities).

    The query wraps each symptom in double quotes and combines them with AND,
    then appends clinical context terms to bias towards diagnostic literature.

    Examples
    --------
    >>> build_scientific_query(["chest pain", "shortness of breath"])
    '("chest pain" AND "shortness of breath") AND (diagnosis OR symptoms OR etiology OR "differential diagnosis")'
    >>> build_scientific_query([])
    '(diagnosis OR symptoms OR etiology OR "differential diagnosis")'
    """
    clinical_context = (
        '(diagnosis OR symptoms OR etiology OR "differential diagnosis")'
    )

    if not symptoms:
        return clinical_context

    symptom_expr = " AND ".join(
        f'"{s.strip()}"' for s in symptoms if s.strip()
    )
    return f"({symptom_expr}) AND {clinical_context}"
