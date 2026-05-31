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


def build_europepmc_query(symptoms: list[str]) -> str:
    """
    Build a query for Europe PMC.

    The terms are combined with explicit ``OR`` so the API ranks by *how many*
    discriminating terms a document matches. This is what surfaces a rare
    condition to the top.

    Why ``OR`` and not space/``AND``: empirically against Europe PMC a bare
    space behaves like an implicit ``AND``. With many auto-extracted terms that
    over-constrains and the target condition drops out entirely (a 13-term VEXAS
    query returned 22 noisy hits, 0 of them VEXAS); the same terms joined with
    ``OR`` ranked VEXAS into 6-8 of the top 10. Quoting has the same recall-
    collapsing effect as ``AND``, so multi-word terms are parenthesised rather
    than quoted.

    Examples
    --------
    >>> build_europepmc_query(["chest pain", "fever"])
    '(chest pain) OR fever'
    >>> build_europepmc_query([])
    'diagnosis OR symptoms OR differential'
    """
    parts: list[str] = []
    for s in symptoms:
        s = s.strip()
        if not s:
            continue
        # Parenthesise multi-word terms so OR binds the whole term, not just its
        # last word, while still avoiding the exact-phrase (quote) recall cliff.
        parts.append(f"({s})" if " " in s else s)

    if not parts:
        return "diagnosis OR symptoms OR differential"

    return " OR ".join(parts)


def build_pubmed_query(symptoms: list[str]) -> str:
    """
    Build a query for PubMed (NCBI E-Utilities ESearch).

    PubMed needs the opposite combination from Europe PMC. With ``OR`` over many
    terms, PubMed's relevance sort returns essentially unrelated articles (a
    VEXAS symptom OR-query returned SGLT2 inhibitors, tea polyphenols, compassion
    fatigue…). Combining the same terms with ``AND`` makes the *intersection* of
    the clinical picture select the right literature.

    All terms are ANDed. With many terms this can over-constrain and return few
    or no hits; that is acceptable here because Europe PMC (OR) covers recall and
    the downstream cross-encoder rerank discards any off-target PubMed results.

    Multi-word terms are parenthesised so ``AND`` binds the whole term.

    Examples
    --------
    >>> build_pubmed_query(["chest pain", "fever"])
    '(chest pain) AND fever'
    >>> build_pubmed_query([])
    'diagnosis AND symptoms'
    """
    terms = [s.strip() for s in symptoms if s.strip()]
    if not terms:
        return "diagnosis AND symptoms"

    parts = [f"({s})" if " " in s else s for s in terms]
    return " AND ".join(parts)


# Backwards-compatible alias: the historical name mapped to the Europe PMC form.
build_scientific_query = build_europepmc_query
