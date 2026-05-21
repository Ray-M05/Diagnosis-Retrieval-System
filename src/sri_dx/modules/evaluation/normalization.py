"""String normalization and similarity for disease-name matching.

Normalization: lowercase + Unicode NFD accent strip + whitespace collapse.

Similarity policy: token-set overlap with a tunable threshold. A retrieved
name counts as a hit against an expected name when the share of expected
tokens present in the retrieved name reaches `DEFAULT_MATCH_THRESHOLD`. This
tolerates qualifier differences ("Hemolytic anemia" vs. "Hemolytic anemia due
to G6PD deficiency") without collapsing distinct diseases into the same
bucket. Documented here so the academic report can cite it for
reproducibility.
"""

from __future__ import annotations

import re
import unicodedata

DEFAULT_MATCH_THRESHOLD = 0.8

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS: frozenset[str] = frozenset(
    {"the", "a", "an", "of", "and", "or", "to", "in", "with", "due", "by", "for"}
)

# Clinical adjectives / qualifiers — count for coverage but cannot be the
# "head noun" of a disease name. Keeping them out of the head heuristic
# avoids picking `idiopathic` over `parkinson` in "idiopathic parkinson
# disease" or `congenital` over `hypothyroidism` in "congenital
# hypothyroidism".
_NON_HEAD_TOKENS: frozenset[str] = frozenset(
    {
        "acute", "chronic", "subacute", "recurrent", "persistent",
        "primary", "secondary", "tertiary", "essential",
        "idiopathic", "congenital", "acquired", "hereditary", "familial",
        "autoimmune", "viral", "bacterial", "fungal", "infectious",
        "benign", "malignant", "severe", "mild", "moderate",
        "disease", "syndrome", "disorder", "attack", "crisis",
        "overview", "introduction", "summary", "review",
        "type", "stage", "grade", "class",
    }
)


def normalize_disease_name(s: str) -> str:
    """Normalize a disease name for matching.

    Steps:
      1. Unicode NFD decomposition + drop combining marks (strips accents).
      2. Lowercase.
      3. Collapse internal whitespace and trim.
    """
    if s is None:
        return ""
    decomposed = unicodedata.normalize("NFD", s)
    no_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return " ".join(no_accents.lower().split())


def _tokenize(s: str) -> frozenset[str]:
    """Split a normalized name into a set of content tokens (no stopwords)."""
    return frozenset(t for t in _TOKEN_RE.findall(s) if t not in _STOPWORDS)


def similarity(a: str, b: str) -> float:
    """Token-set coverage of `a` by `b` (asymmetric, in [0, 1]).

    Returns the fraction of `a`'s content tokens that also appear in `b`.
    Used to ask "does the retrieved name (b) cover the expected name (a)?"
    Empty `a` returns 0.0 (no expectation cannot be satisfied).
    """
    a_tokens = _tokenize(a)
    if not a_tokens:
        return 0.0
    b_tokens = _tokenize(b)
    if not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens)


def _head_token(s: str) -> str | None:
    """Return the most specific clinical token of a normalized disease name.

    Strategy:
      1. Filter out generic adjectives/qualifiers (`_NON_HEAD_TOKENS`) that
         describe a disease but are not the disease itself ("acute",
         "idiopathic", "disease", "syndrome", ...).
      2. From what remains, pick the longest token. Falls back to the
         longest content token when everything got filtered out.

    Examples:
      - "acute pancreatitis"          → pancreatitis
      - "idiopathic parkinson disease" → parkinson
      - "primary hyperthyroidism"      → hyperthyroidism
      - "type 2 diabetes mellitus"     → mellitus (numeric "2" lost in tokens)
    """
    tokens = list(_tokenize(s))
    if not tokens:
        return None
    specific = [t for t in tokens if t not in _NON_HEAD_TOKENS]
    pool = specific if specific else tokens
    return max(pool, key=lambda t: (len(t), pool.index(t)))


def is_match(retrieved: str, expected: str, threshold: float = DEFAULT_MATCH_THRESHOLD) -> bool:
    """True when `retrieved` matches `expected` under either rule:

    1. Token-set coverage: `retrieved` covers at least `threshold` of
       `expected`'s content tokens (asymmetric — extra qualifiers in
       `retrieved` are fine, e.g. "Hemolytic anemia due to G6PD" matches
       "Hemolytic anemia").
    2. Head-token rule: `retrieved` contains the most specific clinical
       token of `expected` (e.g. "pancreatitis attack" matches "acute
       pancreatitis" because both share the head token `pancreatitis`).
    """
    if similarity(expected, retrieved) >= threshold:
        return True
    head = _head_token(expected)
    if head is None:
        return False
    return head in _tokenize(retrieved)


def has_match(retrieved: str, expected_list: list[str], threshold: float = DEFAULT_MATCH_THRESHOLD) -> bool:
    """True when `retrieved` matches any name in `expected_list`."""
    return any(is_match(retrieved, e, threshold) for e in expected_list)


def any_match(retrieved_aliases: list[str], expected_list: list[str], threshold: float = DEFAULT_MATCH_THRESHOLD) -> bool:
    """True when any alias of the retrieved item matches any expected name.

    A "retrieved item" can carry several aliases (e.g. the NER-aggregated
    disease name plus the title of the top evidence document). The hit
    counts as long as at least one alias passes the threshold against at
    least one expected name.
    """
    return any(is_match(alias, e, threshold) for alias in retrieved_aliases if alias for e in expected_list)
