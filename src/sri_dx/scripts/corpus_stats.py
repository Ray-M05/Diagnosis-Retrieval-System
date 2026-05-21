from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

# -----------------------------
# Helpers
# -----------------------------
def safe_get(d: dict, path: list[str], default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())

def percentiles(values: list[int], ps=(50, 90, 95, 99)) -> dict:
    if not values:
        return {f"p{p}": 0 for p in ps}
    v = sorted(values)
    out = {}
    for p in ps:
        k = (len(v) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            out[f"p{p}"] = v[int(k)]
        else:
            out[f"p{p}"] = int(v[f] + (v[c] - v[f]) * (k - f))
    return out

# -----------------------------
# Collector
# -----------------------------
@dataclass
class CorpusStats:
    total_docs: int = 0

    by_mime: Counter = None
    by_domain: Counter = None
    by_language: Counter = None
    by_seed_group: Counter = None
    by_seed_id: Counter = None
    by_depth: Counter = None

    body_chars: list[int] = None
    body_words: list[int] = None
    num_sections: list[int] = None

    missing_title: int = 0
    missing_language: int = 0

    content_hashes: Counter = None

    heading_counter: Counter = None
    has_symptoms_and_diagnosis: int = 0

    def __post_init__(self):
        self.by_mime = Counter()
        self.by_domain = Counter()
        self.by_language = Counter()
        self.by_seed_group = Counter()
        self.by_seed_id = Counter()
        self.by_depth = Counter()

        self.body_chars = []
        self.body_words = []
        self.num_sections = []

        self.content_hashes = Counter()
        self.heading_counter = Counter()

    def add_doc(self, doc: dict):
        self.total_docs += 1

        mime = safe_get(doc, ["content", "mime_type"], "unknown")
        domain = doc.get("source_domain", "unknown")
        lang = safe_get(doc, ["page_meta", "language"], None)
        seed_group = safe_get(doc, ["crawl", "seed_group"], "unknown")
        seed_id = safe_get(doc, ["crawl", "seed_id"], "unknown")
        depth = safe_get(doc, ["crawl", "depth"], None)

        self.by_mime[mime] += 1
        self.by_domain[domain] += 1
        self.by_seed_group[seed_group] += 1
        self.by_seed_id[seed_id] += 1
        if isinstance(depth, int):
            self.by_depth[depth] += 1

        if lang:
            self.by_language[lang] += 1
        else:
            self.missing_language += 1

        title = safe_get(doc, ["content", "title"], None)
        if not title:
            self.missing_title += 1

        body = safe_get(doc, ["content", "body"], "") or ""
        self.body_chars.append(len(body))
        self.body_words.append(word_count(body))

        sections = safe_get(doc, ["content", "sections"], []) or []
        self.num_sections.append(len(sections))

        ch = doc.get("content_hash")
        if isinstance(ch, str) and ch:
            self.content_hashes[ch] += 1

        headings = []
        for s in sections:
            if isinstance(s, dict):
                h = (s.get("heading") or "").strip()
                if h:
                    headings.append(h.lower())
                    self.heading_counter[h.lower()] += 1

        if "symptoms" in headings and "diagnosis" in headings:
            self.has_symptoms_and_diagnosis += 1

    def finalize(self) -> dict:
        dup_docs = sum(c for c in self.content_hashes.values() if c > 1)
        dup_unique = sum(1 for c in self.content_hashes.values() if c > 1)

        out = {
            "total_docs": self.total_docs,

            "by_mime_type": dict(self.by_mime),
            "by_language": dict(self.by_language),
            "by_seed_group": dict(self.by_seed_group),
            "by_seed_id": dict(self.by_seed_id),
            "by_depth": dict(sorted(self.by_depth.items(), key=lambda x: x[0])),

            "top_source_domains": self.by_domain.most_common(15),
            "top_headings": self.heading_counter.most_common(20),

            "body_chars": {
                "avg": int(mean(self.body_chars)) if self.body_chars else 0,
                "min": min(self.body_chars) if self.body_chars else 0,
                "max": max(self.body_chars) if self.body_chars else 0,
                **percentiles(self.body_chars),
            },
            "body_words": {
                "avg": int(mean(self.body_words)) if self.body_words else 0,
                "min": min(self.body_words) if self.body_words else 0,
                "max": max(self.body_words) if self.body_words else 0,
                **percentiles(self.body_words),
            },
            "sections": {
                "avg_count": round(mean(self.num_sections), 2) if self.num_sections else 0.0,
                "min": min(self.num_sections) if self.num_sections else 0,
                "max": max(self.num_sections) if self.num_sections else 0,
                **percentiles(self.num_sections),
            },

            "missing_fields": {
                "missing_title": self.missing_title,
                "missing_language": self.missing_language,
            },

            "duplicates": {
                "duplicate_docs_total": dup_docs,
                "duplicate_hashes_unique": dup_unique,
            },

            "structural_quality": {
                "docs_with_symptoms_and_diagnosis_headings": self.has_symptoms_and_diagnosis,
                "rate": round(self.has_symptoms_and_diagnosis / self.total_docs, 4) if self.total_docs else 0.0,
            },
        }
        return out


# -----------------------------
# IO
# -----------------------------
def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def print_all_results(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))

def main():
    inputs = [
        Path("data/processed/docs_html.jsonl"),
        Path("data/processed/docs_pdf.jsonl"),
    ]
    inputs = [p for p in inputs if p.exists()]

    stats = CorpusStats()
    for p in inputs:
        for doc in iter_jsonl(p):
            stats.add_doc(doc)

    result = stats.finalize()

    out_path = Path("data/processed/corpus_stats.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Main output step:
    print_all_results(result)

    print("\nOK - wrote", out_path)

if __name__ == "__main__":
    main()