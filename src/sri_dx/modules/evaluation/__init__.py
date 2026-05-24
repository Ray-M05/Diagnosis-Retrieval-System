"""IR evaluation module — metrics, qrels, batch evaluator, and persistence."""

from sri_dx.modules.evaluation.metrics import (
    average_precision,
    dcg_at_k,
    f1_at_k,
    fallout_at_k,
    ndcg_at_k,
    precision_at_k,
    r_precision,
    recall_at_k,
    reciprocal_rank,
)
from sri_dx.modules.evaluation.normalization import normalize_disease_name
from sri_dx.modules.evaluation.qrels import QrelEntry, Qrels

__all__ = [
    "QrelEntry",
    "Qrels",
    "average_precision",
    "dcg_at_k",
    "f1_at_k",
    "fallout_at_k",
    "ndcg_at_k",
    "normalize_disease_name",
    "precision_at_k",
    "r_precision",
    "recall_at_k",
    "reciprocal_rank",
]
