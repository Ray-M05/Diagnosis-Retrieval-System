from __future__ import annotations

from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.grouping import group_candidates, normalize_disease_name
from sri_dx.modules.positioning.models import PositioningCandidate


def _candidate(**kwargs):
    defaults = {
        "chunk_id": "chunk-1",
        "doc_id": "doc-1",
        "text": "evidence",
    }
    defaults.update(kwargs)
    return PositioningCandidate(**defaults)


def test_group_candidates_by_problem_entity():
    candidate = _candidate(
        ner_entities=[{"label": "PROBLEM", "text": "Pneumonia", "score": 0.91}]
    )

    groups = group_candidates([candidate])

    assert len(groups) == 1
    assert groups[0].disease_name == "pneumonia"
    assert groups[0].display_name == "Pneumonia"
    assert groups[0].evidences == [candidate]


def test_group_candidates_limits_multiple_diseases_per_chunk():
    candidate = _candidate(
        ner_entities=[
            {"label": "PROBLEM", "text": "A", "score": 0.9},
            {"label": "PROBLEM", "text": "B", "score": 0.8},
            {"label": "PROBLEM", "text": "C", "score": 0.7},
        ]
    )
    config = PositioningConfig(max_diseases_per_chunk=2)

    groups = group_candidates([candidate], config)

    assert [g.display_name for g in groups] == ["A", "B"]


def test_group_candidates_filters_by_min_ner_score_and_falls_back_to_title():
    candidate = _candidate(
        title="Asthma symptoms",
        ner_entities=[{"label": "PROBLEM", "text": "Asthma", "score": 0.2}],
    )

    groups = group_candidates([candidate], PositioningConfig(min_ner_score=0.5))

    assert groups[0].disease_name == "asthma"
    assert groups[0].display_name == "Asthma symptoms"


def test_group_candidates_falls_back_to_url_then_doc_id():
    by_url = _candidate(chunk_id="c-url", doc_id="doc-url", url="https://site.org/heart-failure.html")
    by_doc = _candidate(chunk_id="c-doc", doc_id="doc-only")

    groups = group_candidates([by_url, by_doc])

    assert groups[0].disease_name == "heart failure"
    assert groups[1].disease_name == "doc only"


def test_normalize_disease_name_removes_generic_suffixes_and_acronyms():
    assert normalize_disease_name("  COPD Symptoms ") == "chronic obstructive pulmonary disease"
    assert normalize_disease_name("Heart Failure Disease") == "heart failure"
