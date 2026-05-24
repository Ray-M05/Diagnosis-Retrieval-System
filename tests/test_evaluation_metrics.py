"""Unit tests for the IR evaluation metrics and qrels loader."""

from __future__ import annotations

import math

import pytest

from sri_dx.modules.evaluation import metrics as M
from sri_dx.modules.evaluation.normalization import normalize_disease_name
from sri_dx.modules.evaluation.qrels import Qrels


# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------

def test_normalization_strips_accents_and_lowercases():
    assert normalize_disease_name("Hipertiroidismo") == "hipertiroidismo"
    assert normalize_disease_name("Acromegalía") == "acromegalia"
    assert normalize_disease_name("  Hipertiroidismo  ") == "hipertiroidismo"
    assert normalize_disease_name("ENFERMEDAD\tDE  ADDISON") == "enfermedad de addison"


def test_normalization_handles_empty_and_none():
    assert normalize_disease_name("") == ""
    assert normalize_disease_name(None) == ""  # type: ignore[arg-type]


def test_normalization_keeps_meaningful_punctuation():
    # Slashes and parens are kept verbatim — only accents/whitespace change.
    assert normalize_disease_name("Diabetes Mellitus tipo 2") == "diabetes mellitus tipo 2"


# ---------------------------------------------------------------------------
# precision_at_k, recall_at_k, f1_at_k
# ---------------------------------------------------------------------------

def test_precision_at_k_basic():
    retrieved = ["a", "b", "c", "d", "e"]
    relevant = {"a", "c", "e"}
    assert M.precision_at_k(retrieved, relevant, 5) == pytest.approx(0.6)
    assert M.precision_at_k(retrieved, relevant, 3) == pytest.approx(2 / 3)
    assert M.precision_at_k(retrieved, relevant, 1) == pytest.approx(1.0)


def test_precision_at_k_zero_when_no_hits():
    assert M.precision_at_k(["x", "y"], {"a"}, 2) == 0.0


def test_precision_at_k_edge_cases():
    assert M.precision_at_k([], {"a"}, 5) == 0.0
    assert M.precision_at_k(["a"], {"a"}, 0) == 0.0


def test_recall_at_k_basic():
    retrieved = ["a", "b", "c"]
    relevant = {"a", "b", "x", "y"}
    assert M.recall_at_k(retrieved, relevant, 3) == pytest.approx(2 / 4)
    assert M.recall_at_k(retrieved, relevant, 2) == pytest.approx(2 / 4)
    assert M.recall_at_k(retrieved, relevant, 1) == pytest.approx(1 / 4)


def test_recall_at_k_zero_relevants_returns_zero():
    assert M.recall_at_k(["a", "b"], set(), 5) == 0.0


def test_f1_at_k_harmonic_mean():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "b"}
    # P@4 = 2/4 = 0.5, R@4 = 2/2 = 1.0  →  F1 = 2*0.5/(1.5) = 2/3
    assert M.f1_at_k(retrieved, relevant, 4) == pytest.approx(2 / 3)


def test_f1_at_k_zero_when_both_zero():
    assert M.f1_at_k(["x"], {"a"}, 1) == 0.0


# ---------------------------------------------------------------------------
# average_precision, MAP
# ---------------------------------------------------------------------------

def test_average_precision_perfect_ordering():
    retrieved = ["a", "b", "c"]
    relevant = {"a", "b", "c"}
    # P@1=1, P@2=1, P@3=1 → mean = 1.0
    assert M.average_precision(retrieved, relevant) == pytest.approx(1.0)


def test_average_precision_with_gaps():
    retrieved = ["a", "x", "b", "y"]
    relevant = {"a", "b"}
    # hit at rank 1: P=1/1; hit at rank 3: P=2/3; sum=5/3; / |rel|=2 → 5/6
    assert M.average_precision(retrieved, relevant) == pytest.approx(5 / 6)


def test_average_precision_zero_for_empty_relevant():
    assert M.average_precision(["a", "b"], set()) == 0.0


def test_average_precision_zero_when_none_retrieved():
    assert M.average_precision(["x", "y"], {"a"}) == 0.0


# ---------------------------------------------------------------------------
# reciprocal_rank
# ---------------------------------------------------------------------------

def test_reciprocal_rank_first_hit():
    assert M.reciprocal_rank(["a", "b", "c"], {"a"}) == pytest.approx(1.0)
    assert M.reciprocal_rank(["x", "a", "b"], {"a"}) == pytest.approx(0.5)
    assert M.reciprocal_rank(["x", "y", "a"], {"a"}) == pytest.approx(1 / 3)


def test_reciprocal_rank_zero_when_no_hit():
    assert M.reciprocal_rank(["x", "y", "z"], {"a"}) == 0.0


# ---------------------------------------------------------------------------
# dcg_at_k, ndcg_at_k
# ---------------------------------------------------------------------------

def test_dcg_at_k_binary_relevance():
    # rank 1: 1/log2(2)=1; rank 2: 1/log2(3); rank 3: 0
    retrieved = ["a", "b", "x"]
    relevant = {"a", "b"}
    assert M.dcg_at_k(retrieved, relevant, 3) == pytest.approx(1 + 1 / math.log2(3))


def test_ndcg_at_k_perfect_ordering_is_one():
    retrieved = ["a", "b"]
    relevant = {"a", "b"}
    assert M.ndcg_at_k(retrieved, relevant, 2) == pytest.approx(1.0)


def test_ndcg_at_k_imperfect_ordering_below_one():
    # Two relevants but only one in top-3: NDCG < 1
    retrieved = ["x", "y", "a"]
    relevant = {"a", "b"}
    val = M.ndcg_at_k(retrieved, relevant, 3)
    assert 0 < val < 1


def test_ndcg_at_k_zero_when_no_relevants():
    assert M.ndcg_at_k(["a", "b"], set(), 3) == 0.0


# ---------------------------------------------------------------------------
# fallout_at_k
# ---------------------------------------------------------------------------

def test_fallout_at_k_basic():
    # 3 irrelevant in top-4 out of corpus 100 with 1 relevant → 3 / 99
    retrieved = ["x", "y", "z", "a"]
    relevant = {"a"}
    assert M.fallout_at_k(retrieved, relevant, 4, corpus_size=100) == pytest.approx(3 / 99)


def test_fallout_at_k_zero_when_all_relevant_in_top():
    retrieved = ["a"]
    relevant = {"a"}
    assert M.fallout_at_k(retrieved, relevant, 1, corpus_size=100) == 0.0


def test_fallout_at_k_zero_when_corpus_invalid():
    assert M.fallout_at_k(["x"], {"a"}, 1, corpus_size=0) == 0.0


# ---------------------------------------------------------------------------
# r_precision
# ---------------------------------------------------------------------------

def test_r_precision_equals_p_at_r():
    retrieved = ["a", "b", "x", "y"]
    relevant = {"a", "b", "c"}
    # R=3, top-3 has 2 hits → 2/3
    assert M.r_precision(retrieved, relevant) == pytest.approx(2 / 3)


def test_r_precision_zero_for_empty_relevant():
    assert M.r_precision(["a"], set()) == 0.0


# ---------------------------------------------------------------------------
# macro_average
# ---------------------------------------------------------------------------

def test_macro_average_mean_per_key():
    rows = [
        {"p": 1.0, "r": 0.5},
        {"p": 0.0, "r": 0.5},
    ]
    result = M.macro_average(rows)
    assert result["p"] == pytest.approx(0.5)
    assert result["r"] == pytest.approx(0.5)


def test_macro_average_handles_missing_keys():
    rows = [{"p": 1.0}, {"r": 0.5}]
    result = M.macro_average(rows)
    assert result["p"] == pytest.approx(0.5)
    assert result["r"] == pytest.approx(0.25)


def test_macro_average_empty_returns_empty():
    assert M.macro_average([]) == {}


# ---------------------------------------------------------------------------
# Qrels loader
# ---------------------------------------------------------------------------

def test_qrels_load_basic():
    content = (
        '{"query": "q1", "relevant_disease_names": ["Acromegalia"]}\n'
        '{"query": "q2", "relevant_disease_names": ["Hipertiroidismo"]}\n'
    )
    qrels = Qrels.load_jsonl(content)
    assert len(qrels.entries) == 2
    # Diseases are normalized.
    assert qrels.entries[0].relevant_disease_names == ["acromegalia"]
    assert qrels.entries[1].relevant_disease_names == ["hipertiroidismo"]
    # Hash is deterministic for identical content.
    assert qrels.qrels_hash == Qrels.load_jsonl(content).qrels_hash


def test_qrels_load_skips_blank_lines():
    content = (
        '\n'
        '{"query": "q1", "relevant_disease_names": ["Acromegalia"]}\n'
        '   \n'
        '{"query": "q2", "relevant_disease_names": ["Artrosis"]}\n'
    )
    qrels = Qrels.load_jsonl(content)
    assert len(qrels.entries) == 2


def test_qrels_load_rejects_invalid_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        Qrels.load_jsonl('{not json}\n')


def test_qrels_load_rejects_missing_query():
    with pytest.raises(ValueError, match="missing or empty 'query'"):
        Qrels.load_jsonl('{"relevant_disease_names": ["x"]}\n')


def test_qrels_load_rejects_empty_file():
    with pytest.raises(ValueError, match="empty"):
        Qrels.load_jsonl('')


def test_qrels_detects_chunk_level():
    content = (
        '{"query": "q1", "relevant_disease_names": ["d1"]}\n'
        '{"query": "q2", "relevant_disease_names": ["d2"], '
        '"relevant_chunk_ids": ["c1"]}\n'
    )
    qrels = Qrels.load_jsonl(content)
    assert not qrels.entries[0].has_chunk_level
    assert qrels.entries[1].has_chunk_level
    assert qrels.has_any_chunk_level
