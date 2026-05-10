"""Evidence selection for positioned results."""

from __future__ import annotations

import re

from sri_dx.modules.positioning.authority import candidate_authority_score
from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.models import (
    ClinicalGroup,
    PositioningCandidate,
    PositioningEvidence,
)


def _section_score(section_heading: str | None, config: PositioningConfig) -> float:
    if not section_heading:
        return config.preferred_sections.get("main", 0.70)

    heading = section_heading.strip().lower()
    for section, score in config.preferred_sections.items():
        if section in heading:
            return score
    return 0.65


def _normalized_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) >= 3
    }


def _text_similarity(left: str, right: str) -> float:
    left_tokens = _normalized_tokens(left)
    right_tokens = _normalized_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def evidence_display_score(
    candidate: PositioningCandidate,
    config: PositioningConfig,
) -> float:
    ce = candidate.normalized_scores.get("cross_encoder", candidate.cross_encoder_score or 0.0)
    authority = candidate_authority_score(candidate, config)
    section = _section_score(candidate.section_heading, config)
    return (0.65 * ce) + (0.20 * authority) + (0.15 * section)


def select_top_evidences(
    group: ClinicalGroup,
    config: PositioningConfig,
) -> list[PositioningEvidence]:
    ranked = sorted(
        group.evidences,
        key=lambda ev: evidence_display_score(ev, config),
        reverse=True,
    )

    selected: list[PositioningCandidate] = []
    for candidate in ranked:
        if any(_text_similarity(candidate.text, other.text) >= 0.85 for other in selected):
            continue
        selected.append(candidate)
        if len(selected) >= config.top_evidences:
            break

    return [
        PositioningEvidence(
            chunk_id=e.chunk_id,
            doc_id=e.doc_id,
            text=e.text,
            content_preview=e.text[:300],
            url=e.url or "",
            source_domain=e.source_domain or "",
            section_heading=e.section_heading,
            cross_encoder_score=e.cross_encoder_score,
            hybrid_score=e.hybrid_score,
            lexical_score=e.lexical_score,
            vector_score=e.vector_score,
            authority_score=round(candidate_authority_score(e, config), 6),
        )
        for e in selected
    ]
