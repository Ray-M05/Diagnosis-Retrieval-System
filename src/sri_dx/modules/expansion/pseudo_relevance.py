from __future__ import annotations
import re
from collections import Counter


class SimplePseudoRelevanceFeedback:
    """Extracts frequent terms from top chunks and appends them to a query."""

    def __init__(self, top_docs: int = 5, top_terms: int = 8) -> None:
        self.top_docs = top_docs
        self.top_terms = top_terms
        self.stopwords = {
            "and", "or", "the", "of", "in", "to", "for", "with",
            "patient", "patients", "may", "can", "also", "disease",
        }

    def expand(self, original_query: str, top_chunks: list[str]) -> str:
        text = " ".join(top_chunks[: self.top_docs]).lower()
        tokens = re.findall(r"[a-zA-Z]{4,}", text)
        query_terms = set(original_query.lower().split())
        candidates = [
            token for token in tokens
            if token not in self.stopwords and token not in query_terms
        ]
        selected_terms = [
            term for term, _ in Counter(candidates).most_common(self.top_terms)
        ]
        if not selected_terms:
            return original_query
        return f"{original_query.strip()} {' '.join(selected_terms)}"
