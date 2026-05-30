"""Tests for DiseaseAggregator, focusing on the title-fallback behavior."""
from types import SimpleNamespace

from sri_dx.modules.ranking.disease_aggregator import (
    DiseaseAggregator,
    DiseaseAggregatorConfig,
)


def _problem(text: str, score: float = 0.9) -> dict:
    return {"label": "PROBLEM", "text": text, "score": score, "start_char": 0, "end_char": 0}


def _chunk(doc_id, *, ner=None, ner_title=None, heading="", title="", url="", rerank=1.0):
    meta = {
        "chunk_id": f"{doc_id}:0:0",
        "url": url,
        "section_heading": heading,
        "title": title,
    }
    if ner is not None:
        meta["ner_entities"] = ner
    if ner_title is not None:
        meta["ner_entities_title"] = ner_title
    return SimpleNamespace(doc_id=doc_id, content="...", rerank_score=rerank, metadata=meta)


def test_text_ner_groups_and_counts():
    agg = DiseaseAggregator(DiseaseAggregatorConfig())
    results = [
        _chunk("d1", ner=[_problem("pneumonia")], rerank=2.0),
        _chunk("d2", ner=[_problem("pneumonia")], rerank=1.0),
    ]
    out = agg.aggregate(results)
    assert len(out) == 1
    assert out[0].disease_name == "pneumonia"
    assert out[0].evidence_count == 2  # both chunks support the same disease


def test_title_ner_fallback_when_text_has_no_problem():
    agg = DiseaseAggregator(DiseaseAggregatorConfig())
    results = [
        _chunk("d1", ner=[], ner_title=[_problem("asthma")], heading="Asthma", title="Asthma"),
    ]
    out = agg.aggregate(results)
    assert len(out) == 1
    assert out[0].disease_name == "asthma"
    assert out[0].evidence[0].section_heading == "Asthma"


def test_orphan_bucket_by_title_when_no_ner_at_all():
    agg = DiseaseAggregator(DiseaseAggregatorConfig())
    results = [
        _chunk("d1", ner=[], ner_title=[], title="High blood pressure", heading="Hypertension"),
    ]
    out = agg.aggregate(results)
    assert len(out) == 1
    assert out[0].disease_name == "high blood pressure"
    assert out[0].evidence[0].title == "High blood pressure"


def test_orphan_generic_heading_derives_name_from_url():
    """A boilerplate heading like 'Overview' must not become the disease name;
    fall back to the URL-derived name instead."""
    agg = DiseaseAggregator(DiseaseAggregatorConfig())
    results = [
        _chunk(
            "d1", ner=[], ner_title=[], title="", heading="Overview",
            url="https://www.mayoclinic.org/diseases-conditions/multiple-sclerosis/symptoms-causes/syc-20350269",
        ),
    ]
    out = agg.aggregate(results)
    assert len(out) == 1
    assert out[0].disease_name_display == "Multiple Sclerosis"
    # heading is still preserved on the evidence for the card subtitle
    assert out[0].evidence[0].section_heading == "Overview"


def test_orphan_generic_heading_without_useful_url_is_dropped():
    agg = DiseaseAggregator(DiseaseAggregatorConfig())
    results = [_chunk("d1", ner=[], ner_title=[], title="", heading="Summary", url="")]
    assert agg.aggregate(results) == []


def test_legacy_drops_chunks_without_problem_when_fallback_disabled():
    agg = DiseaseAggregator(DiseaseAggregatorConfig(title_fallback=False))
    results = [
        _chunk("d1", ner=[_problem("pneumonia")]),
        _chunk("d2", ner=[], ner_title=[_problem("asthma")], title="Asthma"),
        _chunk("d3", ner=[], ner_title=[], title="Hypertension"),
    ]
    out = agg.aggregate(results)
    assert [d.disease_name for d in out] == ["pneumonia"]


def test_evidence_carries_header_context():
    agg = DiseaseAggregator(DiseaseAggregatorConfig())
    results = [
        _chunk("d1", ner=[_problem("pneumonia")], heading="Lung infection",
               title="Pneumonia overview", url="http://x/pneumonia"),
    ]
    ev = agg.aggregate(results)[0].evidence[0]
    assert ev.title == "Pneumonia overview"
    assert ev.section_heading == "Lung infection"
    assert ev.url == "http://x/pneumonia"
