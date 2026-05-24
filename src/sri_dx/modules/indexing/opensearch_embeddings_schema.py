# modules/indexing/opensearch_embeddings_schema.py
"""Index schema for the embeddings index in OpenSearch."""


def build_embeddings_index_body(
    vector_dim: int = 768,
    shards: int = 1,
    replicas: int = 0,
    ef_construction: int = 128,
    m: int = 16,
) -> dict:
    """
    Builds the request body for creating the embeddings index in OpenSearch.

    Args:
        vector_dim: Vector dimension (768 for Bio_ClinicalBERT)
        shards: Number of primary shards
        replicas: Number of replicas
        ef_construction: HNSW parameter (higher = better quality, slower)
        m: HNSW parameter (number of connections per node)

    Returns:
        Dict with index configuration
    """
    return {
        "settings": {
            "index": {
                "number_of_shards": shards,
                "number_of_replicas": replicas,
                "knn": True,
                "knn.algo_param.ef_search": 100,
            }
        },
        "mappings": {
            "properties": {
                # Identifiers
                "embedding_id": {
                    "type": "keyword"
                },
                "chunk_id": {
                    "type": "keyword"
                },
                "doc_id": {
                    "type": "keyword"
                },

                # kNN embedding vector
                "vector": {
                    "type": "knn_vector",
                    "dimension": vector_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",  # Cosine similarity
                        "engine": "nmslib",
                        "parameters": {
                            "ef_construction": ef_construction,
                            "m": m
                        }
                    }
                },

                # Model information
                "model_name": {
                    "type": "keyword"
                },
                "model_version": {
                    "type": "keyword"
                },
                "embedding_dim": {
                    "type": "integer"
                },
                "similarity_metric": {
                    "type": "keyword"
                },

                # Chunk metadata (denormalized for filtering)
                "chunk_text_preview": {
                    "type": "text",
                    "analyzer": "standard",
                    "index": False  # Display only, not searchable
                },
                "chunk_index": {
                    "type": "integer"
                },
                "section_heading": {
                    "type": "keyword"
                },
                "seed_group": {
                    "type": "keyword"
                },
                "source_domain": {
                    "type": "keyword"
                },
                "concept_ids": {
                    "type": "keyword"  # Array of keywords
                },

                # Control fields
                "chunk_hash": {
                    "type": "keyword"
                },
                "created_at": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis"
                }
            }
        }
    }
