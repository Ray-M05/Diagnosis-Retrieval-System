"""Pure IR metrics — agnostic to the meaning of the string IDs.

All functions take:
  - retrieved: ordered list of string IDs returned by the system (rank 1 first).
  - relevant: set of string IDs judged relevant by the qrels.
  - k: cut-off rank (only the first k retrieved items count).

Disease-name matching is done upstream via `normalize_disease_name` — these
functions assume both `retrieved` and `relevant` are already normalized.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


def _topk(retrieved: list[str], k: int) -> list[str]:
    if k <= 0:
        return []
    return retrieved[:k]


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """P@k = |retrieved_top_k ∩ relevant| / k."""
    if k <= 0:
        return 0.0
    top = _topk(retrieved, k)
    if not top:
        return 0.0
    hits = sum(1 for item in top if item in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """R@k = |retrieved_top_k ∩ relevant| / |relevant|."""
    if not relevant:
        return 0.0
    top = _topk(retrieved, k)
    hits = sum(1 for item in top if item in relevant)
    return hits / len(relevant)


def f1_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """F1@k — harmonic mean of P@k and R@k."""
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    if p + r == 0.0:
        return 0.0
    return 2 * p * r / (p + r)


def average_precision(retrieved: list[str], relevant: set[str]) -> float:
    """AP = mean of P@i for each i where retrieved[i] is relevant.

    Divisor is |relevant| (standard TREC definition), so unfound relevants
    contribute 0 to the average.
    """
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            hits += 1
            total += hits / i
    return total / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """RR = 1 / rank_of_first_relevant. 0 if none retrieved."""
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def dcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """DCG@k with binary relevance: sum rel_i / log2(i + 1)."""
    top = _topk(retrieved, k)
    total = 0.0
    for i, item in enumerate(top, start=1):
        rel = 1.0 if item in relevant else 0.0
        total += rel / math.log2(i + 1)
    return total


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """NDCG@k = DCG@k / IDCG@k. Ideal ordering puts all relevants first."""
    if not relevant or k <= 0:
        return 0.0
    dcg = dcg_at_k(retrieved, relevant, k)
    # Ideal DCG: up to min(k, |relevant|) ones in the top positions.
    ideal_hits = min(k, len(relevant))
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def fallout_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int,
    corpus_size: int,
) -> float:
    """Fallout@k = |retrieved_top_k \\ relevant| / |corpus \\ relevant|.

    Uses the closed-world assumption: any indexed document not in `relevant`
    is irrelevant. `corpus_size` should be the total number of documents in
    the index against which retrieval was performed.
    """
    if corpus_size <= 0:
        return 0.0
    irrelevant_total = corpus_size - len(relevant)
    if irrelevant_total <= 0:
        return 0.0
    top = _topk(retrieved, k)
    irrelevant_retrieved = sum(1 for item in top if item not in relevant)
    return irrelevant_retrieved / irrelevant_total


def r_precision(retrieved: list[str], relevant: set[str]) -> float:
    """R-Precision = P@R where R = |relevant|.

    Less sensitive to k than P@k and more defensible than Fallout when qrels
    are sparse.
    """
    r = len(relevant)
    if r == 0:
        return 0.0
    return precision_at_k(retrieved, relevant, r)


def macro_average(per_query_metrics: Iterable[dict[str, float]]) -> dict[str, float]:
    """Macro-average a list of {metric_name: value} dicts.

    Returns a single dict with the mean of each metric across all queries.
    Missing keys are treated as 0.0 (consistent with how the per-query
    helpers behave on edge cases).
    """
    rows = list(per_query_metrics)
    if not rows:
        return {}
    keys: set[str] = set()
    for row in rows:
        keys.update(row.keys())
    n = len(rows)
    return {key: sum(row.get(key, 0.0) for row in rows) / n for key in keys}
