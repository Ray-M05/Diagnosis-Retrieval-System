"""String normalization for disease-name matching during evaluation.

Match policy is deliberately strict (no fuzzy): lowercase + Unicode NFD accent
strip + whitespace collapse. Documenting this here so the academic report can
cite it for reproducibility.
"""

from __future__ import annotations

import unicodedata


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
