from ..core.schemas import Query, SearchResult, Evidence
from ..core.ports import Retriever, Ranker

class SearchUseCase:
    def __init__(self, retriever: Retriever, ranker: Ranker):
        self.retriever = retriever
        self.ranker = ranker

    def execute(self, query_text: str) -> SearchResult:
        query = Query(text=query_text)
        
        # 1. Retrieval
        candidates = self.retriever.retrieve(query)
        
        # 2. Ranking
        ranked_results = self.ranker.rank(query, candidates)
        
        return SearchResult(
            query=query,
            results=ranked_results,
            explanation="Generated using SRI-DX Diagnostic Retrieval Flow."
        )
