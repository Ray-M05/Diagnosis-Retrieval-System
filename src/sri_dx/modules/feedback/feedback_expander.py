from __future__ import annotations

import re
from collections import Counter


class FeedbackTextualExpander:

    def __init__(self, top_terms: int = 10) -> None:
        self.top_terms = top_terms
        self.stopwords = {
            "and", "or", "the", "of", "in", "to", "for", "with",
            "patient", "patients", "disease", "symptoms",
        }

    def expand_with_relevant_chunks(
        self,
        original_query: str,
        relevant_chunks: list[str],
    ) -> str:
        text = " ".join(relevant_chunks).lower()
        tokens = re.findall(r"[a-zA-Z]{4,}", text)
        original_terms = set(original_query.lower().split())
        candidates = [
            token for token in tokens
            if token not in self.stopwords and token not in original_terms
        ]
        selected_terms = [
            term for term, _ in Counter(candidates).most_common(self.top_terms)
        ]
        if not selected_terms:
            return original_query
        return f"{original_query.strip()} {' '.join(selected_terms)}"
