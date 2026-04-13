from pydantic import BaseModel, ConfigDict


class OpenSearchEmbeddingConfig(BaseModel):
    """Pydantic config for OpenSearchEmbeddingSink."""

    model_config = ConfigDict(frozen=True)

    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    verify_certs: bool = False
    index_name: str = "clinical_embeddings_v1"
    alias_name: str = "clinical_embeddings"
    vector_dim: int = 768
    shards: int = 1
    replicas: int = 0
    request_timeout: int = 60
    ef_construction: int = 128
    m: int = 16
