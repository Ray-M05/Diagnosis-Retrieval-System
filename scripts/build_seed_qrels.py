"""Parse tests/TEST_CASES.md → data/qrels/test_cases.jsonl.

The markdown is organized as:
  ## N. <Disease Name>
      ### N.1 Consulta sin chart [...]
      ```
      <multi-line query>
      ```
      ...
      ### N.4 Salida esperada
      - **Top-1 esperado:** <disease name>

Subcases (sections 8/9/10/11.X) follow the same convention, occasionally with
slight variations (e.g. "Top-1 esperado por corpus:"). The parser is lenient:
it extracts every (consulta-block, top-1) pair it finds anywhere in the file.
Output is idempotent (sorted by source order, stable line format).

Usage:
    python scripts/build_seed_qrels.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Allow running this script without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sri_dx.modules.evaluation.normalization import normalize_disease_name  # noqa: E402

INPUT_PATH = ROOT / "tests" / "TEST_CASES.md"
OUTPUT_PATH = ROOT / "data" / "qrels" / "test_cases.jsonl"

# Match a markdown heading that introduces a case section (## or ###).
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)

# A fenced code block (```...```), capturing its contents.
CODE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9]*\s*\n(.*?)```", re.DOTALL)

# "Top-1 esperado" line — may end with disease name, "por corpus", etc.
# Accept formats like:
#   - **Top-1 esperado:** Acromegalia
#   - **Top-1 esperado por corpus:** Hipotiroidismo congénito.
#   - **Top-1 esperado:**
#       - **Hombre:** Anemia hemolítica por déficit de G6PD ...
#       - **Mujer:** Anemia hemolítica autoinmune ...
# When the same-line capture is empty, fall back to the first sub-bullet.
TOP1_RE = re.compile(
    r"\*\*Top-1 esperado(?:\s+por\s+corpus)?:\*\*\s*(.*)\n((?:\s*-\s+\*\*.+\n)*)",
    re.MULTILINE,
)


def _extract_top1_text(match: re.Match[str]) -> str:
    """Pull the disease name from a TOP1_RE match — same-line or sub-bullet.

    Some cases lay out the Top-1 as a list of patient variants:
        **Top-1 esperado:**
          - **Hombre:** Enfermedad de Cushing ...
          - **Mujer:**  Síndrome de Cushing iatrogénico ...
    In that case the regex's "inline" capture may pick up the dash-line
    itself; fall back to extracting the disease that follows the inner
    label (`**Hombre:**`).
    """
    inline = (match.group(1) or "").strip()
    sub_bullet_re = re.compile(r"-\s+\*\*[^*]+\*\*[:\s]*(.+)")
    if inline:
        if inline.lstrip().startswith("-"):
            m_sub = sub_bullet_re.search(inline)
            if m_sub:
                return m_sub.group(1).strip()
        else:
            return inline
    # Fall back to the captured sub-bullet block.
    sub = match.group(2) or ""
    first_sub = sub_bullet_re.search(sub)
    if first_sub:
        return first_sub.group(1).strip()
    return ""


def _clean_disease_name(raw: str) -> str:
    """Strip parenthetical clarifications, trailing punctuation, footnotes.

    Examples:
        "Acromegalia."                          → "Acromegalia"
        "Aterosclerosis (con enfermedad ...)"   → "Aterosclerosis"
        "Hipertiroidismo (Enfermedad de Graves..." → "Hipertiroidismo"
        "Anemia hemolítica autoinmune ..."      → "Anemia hemolítica autoinmune"
    """
    # Cut off at the first parenthesis or em-dash (clarifications/qualifiers).
    cut = re.split(r"[(—\-:]", raw, maxsplit=1)[0]
    # Strip trailing punctuation/whitespace.
    return cut.strip(" \t.,;:•").strip()


def _extract_queries_and_top1(markdown: str) -> list[tuple[str, str]]:
    """Walk the file and emit (query, top-1 disease) pairs.

    Two-pass strategy:
      1. Split by top-level `## N. Title` sections — for each, pair the first
         code block in the whole section with the first Top-1 line. This
         catches the canonical cases (§1–§7, §11.1–§11.10) where the consulta
         lives in `### N.1` and the Top-1 in `### N.4`.
      2. Within each top-level section, also split by `### N.X` subsections —
         if a subsection has BOTH its own code block AND its own Top-1, emit
         that pair too. This catches §8/§9/§10 where each subcase is
         self-contained.
    Deduplicates on (query, normalized disease) at the call site.
    """
    pairs: list[tuple[str, str]] = []

    # Pass 1: top-level sections.
    h2_positions = [m.start() for m in re.finditer(r"^##\s+\d", markdown, re.MULTILINE)]
    h2_positions.append(len(markdown))
    h2_chunks = [markdown[h2_positions[i]:h2_positions[i + 1]] for i in range(len(h2_positions) - 1)]

    for chunk in h2_chunks:
        code_blocks = list(CODE_BLOCK_RE.finditer(chunk))
        top1_matches = list(TOP1_RE.finditer(chunk))
        if code_blocks and top1_matches:
            query = code_blocks[0].group(1).strip()
            top1 = _clean_disease_name(_extract_top1_text(top1_matches[0]))
            if query and top1:
                pairs.append((query, top1))

        # Pass 2: §N.X subsections inside this top-level chunk.
        h3_positions = [m.start() for m in re.finditer(r"^###\s+\d+\.\d", chunk, re.MULTILINE)]
        h3_positions.append(len(chunk))
        h3_chunks = [chunk[h3_positions[i]:h3_positions[i + 1]] for i in range(len(h3_positions) - 1)]
        for sub in h3_chunks:
            sub_code = list(CODE_BLOCK_RE.finditer(sub))
            sub_top1 = list(TOP1_RE.finditer(sub))
            if sub_code and sub_top1:
                sub_query = sub_code[0].group(1).strip()
                sub_disease = _clean_disease_name(_extract_top1_text(sub_top1[0]))
                if sub_query and sub_disease:
                    pairs.append((sub_query, sub_disease))

    return pairs


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"ERROR: {INPUT_PATH} not found", file=sys.stderr)
        return 1

    markdown = INPUT_PATH.read_text(encoding="utf-8")
    pairs = _extract_queries_and_top1(markdown)

    if not pairs:
        print("ERROR: no query/top-1 pairs extracted", file=sys.stderr)
        return 1

    # Deduplicate on (normalized query, normalized disease) while preserving order.
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for query, disease in pairs:
        key = (query, normalize_disease_name(disease))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((query, disease))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        for query, disease in deduped:
            obj = {
                "query": query,
                "relevant_disease_names": [disease],
            }
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"Wrote {len(deduped)} entries to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
