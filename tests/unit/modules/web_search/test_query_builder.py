"""Unit tests — web_search query builder."""
from __future__ import annotations

import pytest

from sri_dx.modules.web_search.query_builder import (
    build_medlineplus_query,
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


class TestBuildScientificQuery:
    _CONTEXT = '(diagnosis OR symptoms OR etiology OR "differential diagnosis")'

    def test_multiple_symptoms(self):
        result = build_scientific_query(["chest pain", "shortness of breath"])
        assert '"chest pain"' in result
        assert '"shortness of breath"' in result
        assert "AND" in result
        assert self._CONTEXT in result

    def test_single_symptom(self):
        result = build_scientific_query(["fever"])
        assert result == f'("fever") AND {self._CONTEXT}'

    def test_empty_list(self):
        result = build_scientific_query([])
        assert result == self._CONTEXT

    def test_ignores_blank_entries(self):
        result = build_scientific_query(["chest pain", "", "fever"])
        assert '"chest pain"' in result
        assert '"fever"' in result
        # blank should not appear as an empty quoted pair
        assert '""' not in result

    def test_strips_whitespace_in_symptoms(self):
        result = build_scientific_query(["  chest pain  "])
        assert '"chest pain"' in result

    def test_structure_with_three_symptoms(self):
        result = build_scientific_query(["a", "b", "c"])
        assert result.startswith('("a" AND "b" AND "c")')
