from sri_dx.adapters.stores.sqlite_feedback_store import SqliteFeedbackStore
from sri_dx.modules.expansion import SimplePseudoRelevanceFeedback, SynonymExpander
from sri_dx.modules.feedback import FeedbackTextualExpander


def test_synonym_expander_adds_local_medical_terms():
    expander = SynonymExpander()

    expanded = expander.expand("patient with shortness of breath and chest pain")

    assert "dyspnea" in expanded
    assert "difficulty breathing" in expanded
    assert "angina" in expanded


def test_synonym_expander_matches_abbreviations_as_terms_only():
    expander = SynonymExpander()

    assert expander.expand("family history of migraines") == "family history of migraines"

    expanded = expander.expand("possible MI with chest pain")

    assert "myocardial infarction" in expanded
    assert "heart attack" in expanded


def test_pseudo_relevance_feedback_adds_frequent_terms():
    prf = SimplePseudoRelevanceFeedback(top_docs=2, top_terms=3)

    expanded = prf.expand(
        "chest pain",
        [
            "myocardial infarction myocardial infarction troponin elevation",
            "troponin elevation coronary syndrome",
        ],
    )

    assert expanded.startswith("chest pain")
    assert "myocardial" in expanded
    assert "troponin" in expanded


def test_feedback_textual_expander_uses_relevant_chunks():
    expander = FeedbackTextualExpander(top_terms=3)

    refined = expander.expand_with_relevant_chunks(
        "fever cough",
        ["pneumonia consolidation pneumonia infiltrate cough fever"],
    )

    assert refined.startswith("fever cough")
    assert "pneumonia" in refined
    assert "consolidation" in refined


def test_sqlite_feedback_store_persists_feedback_and_expansions():
    store = SqliteFeedbackStore(":memory:")

    store.save_feedback("s1", "q", "c1", "d1", True)
    store.save_query_expansion("s1", "q", "q expanded", "synonym")

    feedback = store.get_feedback_for_session("s1")
    store.close()

    assert feedback == [
        {
            "session_id": "s1",
            "query": "q",
            "chunk_id": "c1",
            "doc_id": "d1",
            "relevant": True,
            "created_at": feedback[0]["created_at"],
        }
    ]
