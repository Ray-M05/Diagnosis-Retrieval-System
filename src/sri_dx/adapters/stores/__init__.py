# Adaptadores de almacenamiento
# Conexiones a OpenSearch y SQLite para persistencia

from .opensearch_sink import OpenSearchIndexSink, OpenSearchConfig
from .opensearch_search_backend import OpenSearchSearchBackend
from .opensearch_chunk_sink import OpenSearchChunksSink
from .schemas.opensearch_chunks_config import OpenSearchChunksConfig
from .opensearch_chunk_reader import OpenSearchChunkReader
from .schemas.opensearch_chunk_reader_config import OpenSearchChunkReaderConfig
from .opensearch_embedding_sink import OpenSearchEmbeddingSink
from .schemas.opensearch_embedding_config import OpenSearchEmbeddingConfig
from .sqlite_manifest import SqliteManifestStore

__all__ = [
    # OpenSearch
    "OpenSearchIndexSink",
    "OpenSearchConfig",
    "OpenSearchSearchBackend",
    "OpenSearchChunksSink",
    "OpenSearchChunksConfig",
    "OpenSearchChunkReader",
    "OpenSearchChunkReaderConfig",
    "OpenSearchEmbeddingSink",
    "OpenSearchEmbeddingConfig",
    # SQLite
    "SqliteManifestStore",
]
