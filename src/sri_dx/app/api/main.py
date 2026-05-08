from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel

from sri_dx.app.api.deps import get_hybrid_search_use_case, get_retrieval_pipeline
from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
from sri_dx.usecases.search.tow_stage_retrieval_pipeline import TwoStageRetrievalPipeline
from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig
from sri_dx.modules.web_search.sufficiency import LocalSufficiencyEvaluator
from sri_dx.modules.web_search.schemas import LocalRetrievalResult, RetrievedChunkResult
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor

app = FastAPI(title="SRI-DX API", description="API para el motor de búsqueda y diagnóstico clínico")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a los dominios del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    k: int = 10
    fusion_method: str = "rrf"
    use_reranking: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    hybrid_candidates: int = 100

class DiagnoseRequest(BaseModel):
    query: str
    max_diseases: int = 10
    min_ner_score: float = 0.5
    hybrid_candidates: int = 100

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/search")
def search(
    request: SearchRequest,
    use_case: SearchHybridUseCase = Depends(get_hybrid_search_use_case)
):
    # Actualizar configuración del use case con los parámetros del request
    use_case.config.fusion_method = request.fusion_method
    use_case.config.use_reranking = request.use_reranking
    use_case.config.rerank_model_name = request.rerank_model
    use_case.config.lexical_k = request.hybrid_candidates
    use_case.config.semantic_k = request.hybrid_candidates
    
    # Reinicializar cross-encoder si es necesario
    if request.use_reranking:
        use_case.__post_init__()

    results = use_case.search(query=request.query, k=request.k)
    
    # ---------------------------------------------------------
    # Evaluación de Suficiencia (UI Integration)
    # ---------------------------------------------------------
    extractor = ConceptExtractor()
    symptoms = extractor.extract(request.query)
    
    evaluator = LocalSufficiencyEvaluator()
    
    chunk_results = []
    for r in results:
        chunk_results.append(RetrievedChunkResult(
            chunk_id=r.chunk_id,
            doc_id=r.doc_id,
            title=r.metadata.get("title", ""),
            url=r.metadata.get("url", ""),
            source_domain=r.metadata.get("source_domain", ""),
            chunk_text=r.metadata.get("chunk_text", ""),
            final_score=r.score,
            bm25_score=r.lexical_score,
            vector_score=r.vector_score,
            concept_ids=r.metadata.get("concept_ids", []),
            section_heading=r.metadata.get("section_heading", "")
        ))
        
    local_retrieval_result = LocalRetrievalResult(
        query=request.query,
        extracted_symptoms=symptoms,
        results=chunk_results
    )
    
    sufficiency = evaluator.evaluate(local_retrieval_result)
    
    return {
        "query": request.query,
        "results": results,
        "sufficiency": sufficiency
    }

@app.post("/api/diagnose")
def diagnose(
    request: DiagnoseRequest,
    pipeline: TwoStageRetrievalPipeline = Depends(get_retrieval_pipeline)
):
    # Configurar pipeline
    pipeline.config.max_diseases = request.max_diseases
    pipeline.config.min_ner_score = request.min_ner_score
    pipeline.config.hybrid_candidates = request.hybrid_candidates
    
    results = pipeline.search_diseases(query=request.query)
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
