from __future__ import annotations

from datetime import datetime, timezone

from sri_dx.modules.positioning.authority import group_authority_score, normalize_domain
from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.freshness import (
    candidate_freshness_score,
    days_since,
    parse_optional_datetime,
)
from sri_dx.modules.positioning.models import ClinicalGroup, PositioningCandidate
from sri_dx.modules.positioning.scoring import (
    aggregate_group_signal,
    minmax_normalize,
    normalize_candidate_scores,
    score_clinical_group,
    sigmoid,
)
from sri_dx.modules.positioning.symptoms import compute_symptom_coverage


def _candidate(**kwargs):
    defaults = {
        "chunk_id": "chunk-1",
        "doc_id": "doc-1",
        "text": "The patient has fever and dyspnea.",
    }
    defaults.update(kwargs)
    return PositioningCandidate(**defaults)


def test_minmax_normalize_empty_equal_and_none_values():
    assert minmax_normalize([]) == []
    assert minmax_normalize([2.0, 2.0, None]) == [1.0, 1.0, None]
    assert minmax_normalize([1.0, 3.0]) == [0.0, 1.0]


def test_sigmoid_is_bounded():
    assert 0.0 < sigmoid(-5.0) < 0.5
    assert 0.5 < sigmoid(5.0) < 1.0


def test_normalize_candidate_scores_preserves_raw_scores():
    candidates = [
        _candidate(chunk_id="a", cross_encoder_score=-1.0, hybrid_score=0.1),
        _candidate(chunk_id="b", cross_encoder_score=2.0, hybrid_score=0.3),
    ]

    normalized = normalize_candidate_scores(candidates)

    assert normalized[0].cross_encoder_score == -1.0
    assert normalized[1].normalized_scores["cross_encoder"] == 1.0
    assert normalized[0].normalized_scores["hybrid"] == 0.0
    assert normalized[1].normalized_scores["hybrid"] == 1.0


def test_parse_optional_datetime_and_days_since_are_deterministic():
    parsed = parse_optional_datetime("2026-01-01T00:00:00Z")
    reference = datetime(2026, 1, 11, tzinfo=timezone.utc)

    assert parsed is not None
    assert days_since(parsed, reference) == 10
    assert parse_optional_datetime("not-a-date") is None


def test_symptom_coverage_matches_aliases_and_concepts():
    evidence = _candidate(
        text="Symptoms include dyspnea and high temperature.",
        concept_ids=["DYSPNEA"],
    )
    group = ClinicalGroup("pneumonia", "Pneumonia", [evidence])

    score, matched = compute_symptom_coverage("shortness of breath and fever", group)

    assert score == 1.0
    assert "shortness of breath" in matched
    assert "fever" in matched


def test_symptom_coverage_neutral_without_detectable_symptoms():
    group = ClinicalGroup("diabetes", "Diabetes", [_candidate()])

    score, matched = compute_symptom_coverage("general clinical article", group)

    assert score == 0.5
    assert matched == []


def test_authority_normalizes_domains_and_scores_group():
    config = PositioningConfig()
    group = ClinicalGroup(
        "pneumonia",
        "Pneumonia",
        [
            _candidate(chunk_id="a", source_domain="www.mayoclinic.org"),
            _candidate(chunk_id="b", source_domain="unknown.example"),
        ],
    )

    assert normalize_domain("https://www.mayoclinic.org/foo") == "mayoclinic.org"
    assert group_authority_score(group, config) > config.unknown_authority_score


def test_freshness_prefers_updated_published_fetched():
    config = PositioningConfig()
    reference = datetime(2026, 5, 1, tzinfo=timezone.utc)
    candidate = _candidate(
        fetched_at="2020-01-01",
        published_at="2025-01-01",
        updated_at="2026-04-01",
    )

    assert candidate_freshness_score(candidate, config, reference) == 1.0
    assert candidate_freshness_score(_candidate(), config, reference) == config.unknown_freshness_score


def test_aggregate_group_signal_and_score_clinical_group():
    evidence = normalize_candidate_scores(
        [
            _candidate(
                cross_encoder_score=0.9,
                hybrid_score=0.8,
                source_domain="cdc.gov",
                concept_ids=["FEVER"],
                fetched_at="2026-01-01",
            )
        ]
    )[0]
    group = ClinicalGroup("pneumonia", "Pneumonia", [evidence])

    assert aggregate_group_signal([1.0], [evidence]) > 0.9

    scored = score_clinical_group(
        "fever",
        group,
        PositioningConfig(),
        datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    assert scored.relevance_score > 0.7
    assert scored.component_scores["symptom_coverage"] == 1.0
