"""Freshness scoring for positioning."""

from __future__ import annotations

from datetime import datetime, timezone

from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.models import ClinicalGroup, PositioningCandidate


def parse_optional_datetime(value: object) -> datetime | None:
    """Parse common ISO datetime/date values without raising."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def days_since(date_value: datetime, reference_date: datetime) -> int:
    ref = reference_date if reference_date.tzinfo else reference_date.replace(tzinfo=timezone.utc)
    dt = date_value if date_value.tzinfo else date_value.replace(tzinfo=timezone.utc)
    return max(0, (ref - dt).days)


def freshness_from_days(age_days: int, config: PositioningConfig) -> float:
    if age_days <= 180:
        return 1.00
    if age_days <= 365:
        return 0.85
    if age_days <= 730:
        return 0.70
    if age_days <= 1825:
        return 0.55
    return 0.40


def candidate_freshness_score(
    candidate: PositioningCandidate,
    config: PositioningConfig,
    reference_date: datetime | None = None,
) -> float:
    reference = reference_date or datetime.now(timezone.utc)
    parsed = (
        parse_optional_datetime(candidate.updated_at)
        or parse_optional_datetime(candidate.published_at)
        or parse_optional_datetime(candidate.fetched_at)
    )
    if parsed is None:
        return config.unknown_freshness_score
    return freshness_from_days(days_since(parsed, reference), config)


def group_freshness_score(
    group: ClinicalGroup,
    config: PositioningConfig,
    reference_date: datetime | None = None,
) -> float:
    if not group.evidences:
        return config.unknown_freshness_score

    ranked = sorted(
        group.evidences,
        key=lambda ev: ev.normalized_scores.get("cross_encoder", ev.cross_encoder_score or 0.0),
        reverse=True,
    )
    top_evidences = ranked[:3]
    scores = [candidate_freshness_score(ev, config, reference_date) for ev in top_evidences]
    if not scores:
        return config.unknown_freshness_score
    return max(0.0, min(1.0, (0.70 * scores[0]) + (0.30 * max(scores))))
