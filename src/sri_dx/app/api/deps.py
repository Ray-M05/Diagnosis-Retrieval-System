import os
from sri_dx.adapters.stores.opensearch_search_backend import (
    OpenSearchSearchBackend, OpenSearchSearchConfig
)
from sri_dx.adapters.stores import (
    OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig
)
from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
from sri_dx.usecases.search.two_stage_retrieval_pipeline import (
    TwoStageRetrievalPipeline, TwoStageRetrievalConfig
)
from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig

def get_hybrid_search_use_case() -> SearchHybridUseCase:
    host = os.getenv("OPENSEARCH_HOST", "localhost").replace("http://", "").split(":")[0]
    port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    
    lexical_index = os.getenv("LEXICAL_CHUNKS_INDEX", "clinical_chunks")
    semantic_index = os.getenv("SEMANTIC_CHUNKS_INDEX", "clinical_embeddings_v1")

    lexical_backend = OpenSearchSearchBackend(OpenSearchSearchConfig(
        host=host, port=port, index_alias=lexical_index,
        search_fields=["section_heading^3", "chunk_text^1"]
    ))
    
    embedding_store = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
        host=host, port=port, index_name=semantic_index
    ))

    # Default configuration; can be overridden per request
    config = HybridSearchConfig()

    return SearchHybridUseCase(
        lexical_backend=lexical_backend,
        embedding_store=embedding_store,
        config=config
    )

def get_retrieval_pipeline() -> TwoStageRetrievalPipeline:
    hybrid_search = get_hybrid_search_use_case()
    
    # Default configuration
    config = TwoStageRetrievalConfig()
    
    return TwoStageRetrievalPipeline(
        hybrid_search=hybrid_search,
        config=config
    )
