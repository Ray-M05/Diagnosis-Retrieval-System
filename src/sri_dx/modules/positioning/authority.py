"""Source authority scoring for clinical positioning."""

from __future__ import annotations

from urllib.parse import urlparse

from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.models import ClinicalGroup, PositioningCandidate


def normalize_domain(domain_or_url: str | None) -> str:
    """Normalize a domain or URL for source reliability lookup."""

    if not domain_or_url:
        return ""

    value = domain_or_url.strip().lower()
    if "://" in value:
        parsed = urlparse(value)
        value = parsed.netloc or parsed.path

    value = value.strip().strip("/")
    if value.startswith("www."):
        value = value[4:]
    return value


def candidate_authority_score(
    candidate: PositioningCandidate,
    config: PositioningConfig,
) -> float:
    domain = normalize_domain(candidate.source_domain or candidate.url)
    if not domain:
        return config.missing_domain_authority_score
    return config.source_reliability.get(domain, config.unknown_authority_score)


def group_authority_score(
    group: ClinicalGroup,
    config: PositioningConfig,
) -> float:
    if not group.evidences:
        return config.unknown_authority_score

    by_domain: dict[str, float] = {}
    missing_scores: list[float] = []

    for evidence in group.evidences:
        domain = normalize_domain(evidence.source_domain or evidence.url)
        score = candidate_authority_score(evidence, config)
        if domain:
            by_domain[domain] = max(score, by_domain.get(domain, 0.0))
        else:
            missing_scores.append(score)

    scores = list(by_domain.values()) or missing_scores
    if not scores:
        return config.unknown_authority_score

    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    return max(0.0, min(1.0, (0.75 * max_score) + (0.25 * avg_score)))
