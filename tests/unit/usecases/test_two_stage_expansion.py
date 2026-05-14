from sri_dx.core.schemas.search.search_result_schema import HybridSearchResult
from sri_dx.modules.ranking.schemas import RerankResponse, RerankResult
from sri_dx.usecases.search.two_stage_retrieval_pipeline import (
    TwoStageRetrievalConfig,
    TwoStageRetrievalPipeline,
)


class FakeHybridSearch:
    def __init__(self):
        self.queries = []

    def search(self, query: str, k: int):
        self.queries.append((query, k))
        return [
            HybridSearchResult(
                doc_id="d1",
                chunk_id="c1",
                score=1.0,
                lexical_score=1.0,
                vector_score=None,
                metadata={"content": "shortness of breath and chest pain", "chunk_id": "c1"},
            )
        ]


class FakeCrossEncoder:
    def __init__(self):
        self.requests = []

    def rerank(self, request):
        self.requests.append(request)
        return RerankResponse(
            query=request.query,
            ranked_results=[
                RerankResult(
                    original_result=request.results[0],
                    rerank_score=0.9,
                    original_position=0,
                    new_position=0,
                )
            ],
            model_name="fake",
            model_version="test",
        )


def test_pipeline_uses_expanded_query_for_hybrid_and_original_for_rerank():
    hybrid = FakeHybridSearch()
    cross_encoder = FakeCrossEncoder()
    pipeline = TwoStageRetrievalPipeline(
        hybrid_search=hybrid,
        cross_encoder=cross_encoder,
        config=TwoStageRetrievalConfig(enable_synonym_expansion=True),
    )

    results = pipeline.search("shortness of breath")

    assert "dyspnea" in hybrid.queries[0][0]
    assert cross_encoder.requests[0].query == "shortness of breath"
    assert results[0].doc_id == "d1"
