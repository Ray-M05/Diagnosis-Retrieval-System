from pydantic import BaseModel, ConfigDict


class OpenSearchChunkReaderConfig(BaseModel):
    """Pydantic config for OpenSearchChunkReader."""

    model_config = ConfigDict(frozen=True)

    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    verify_certs: bool = False
    index_name: str = "clinical_chunks_v1"
    scroll_size: int = 100
    scroll_timeout: str = "20m"
    request_timeout: int = 60
