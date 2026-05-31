"""Unit tests — web_search query builder."""
from __future__ import annotations

import pytest

from sri_dx.modules.web_search.query_builder import (
    build_europepmc_query,
    build_medlineplus_query,
    build_pubmed_query,
    build_scientific_query,
)


class TestBuildMedlinePlusQuery:
    def test_multiple_symptoms(self):
        result = build_medlineplus_query(["chest pain", "shortness of breath", "fatigue"])
        assert result == "chest pain shortness of breath fatigue"

    def test_single_symptom(self):
        result = build_medlineplus_query(["fever"])
        assert result == "fever"

    def test_empty_list(self):
        assert build_medlineplus_query([]) == ""

    def test_strips_whitespace(self):
        result = build_medlineplus_query(["  chest pain  ", "  fever  "])
        assert result == "chest pain fever"

    def test_ignores_blank_entries(self):
        result = build_medlineplus_query(["chest pain", "", "  ", "fever"])
        assert result == "chest pain fever"


class TestBuildEuropePmcQuery:
    def test_terms_are_not_quoted(self):
        # Quoting collapses Europe PMC recall (phrase-match cliff); keywords
        # must stay unquoted so the combination ranks the right condition.
        result = build_europepmc_query(["chest pain", "shortness of breath"])
        assert '"' not in result
        assert "chest pain" in result
        assert "shortness of breath" in result

    def test_terms_joined_with_or(self):
        result = build_europepmc_query(["chest pain", "fever"])
        assert " OR " in result
        assert " AND " not in result
        # multi-word term parenthesised so OR binds the whole term
        assert "(chest pain)" in result

    def test_ignores_blank_entries(self):
        result = build_europepmc_query(["chest pain", "", "fever"])
        assert "chest pain" in result
        assert "fever" in result

    def test_strips_whitespace_in_symptoms(self):
        result = build_europepmc_query(["  chest pain  "])
        assert "(chest pain)" in result
        assert "  chest pain  " not in result

    def test_empty_list_uses_diagnostic_cue(self):
        result = build_europepmc_query([])
        assert "diagnosis" in result
        assert '"' not in result

    def test_scientific_query_is_europepmc_alias(self):
        # Historical name must keep mapping to the Europe PMC (OR) form.
        assert build_scientific_query(["fever", "cough"]) == build_europepmc_query(
            ["fever", "cough"]
        )


class TestBuildPubMedQuery:
    def test_terms_joined_with_and(self):
        # PubMed needs AND: OR returns unrelated articles for symptom queries.
        result = build_pubmed_query(["cytopenias", "vacuoles"])
        assert result == "cytopenias AND vacuoles"

    def test_multi_word_terms_are_parenthesised(self):
        result = build_pubmed_query(["chest pain", "fever"])
        assert "(chest pain)" in result
        assert " AND " in result
        assert " OR " not in result

    def test_terms_are_not_quoted(self):
        result = build_pubmed_query(["chest pain", "fever"])
        assert '"' not in result

    def test_ignores_blank_entries(self):
        result = build_pubmed_query(["cytopenias", "", "  ", "vacuoles"])
        assert result == "cytopenias AND vacuoles"

    def test_strips_whitespace(self):
        result = build_pubmed_query(["  cytopenias  "])
        assert result == "cytopenias"

    def test_ands_all_terms(self):
        # All terms are ANDed (no filtering/capping); recall is covered by the
        # Europe PMC OR query and the downstream rerank.
        result = build_pubmed_query(["inflammation", "cytopenias", "vacuoles"])
        assert result == "inflammation AND cytopenias AND vacuoles"

    def test_empty_list_uses_diagnostic_cue(self):
        assert "diagnosis" in build_pubmed_query([])
