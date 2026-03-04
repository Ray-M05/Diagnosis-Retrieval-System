# Adaptadores de almacenamiento
# Conexiones a OpenSearch y SQLite para persistencia

from .opensearch_sink import OpenSearchIndexSink, OpenSearchConfig
from .opensearch_search_backend import OpenSearchSearchBackend
from .opensearch_chunk_sink import OpenSearchChunksSink, OpenSearchChunksConfig
from .opensearch_chunk_reader import OpenSearchChunkReader, OpenSearchChunkReaderConfig
from .opensearch_embedding_sink import OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig
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
