# modules/indexing/opensearch_embeddings_schema.py
"""Schema del índice de embeddings para OpenSearch."""


def build_embeddings_index_body(
    vector_dim: int = 768,
    shards: int = 1,
    replicas: int = 0,
    ef_construction: int = 256,
    m: int = 16,
) -> dict:
    """
    Construye el body para crear el índice de embeddings en OpenSearch.
    
    Args:
        vector_dim: Dimensión de los vectores (768 para Bio_ClinicalBERT)
        shards: Número de shards primarios
        replicas: Número de réplicas
        ef_construction: Parámetro HNSW (mayor = mejor calidad, más lento)
        m: Parámetro HNSW (número de conexiones por nodo)
        
    Returns:
        Dict con configuración del índice
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
                # Identificadores
                "embedding_id": {
                    "type": "keyword"
                },
                "chunk_id": {
                    "type": "keyword"
                },
                "doc_id": {
                    "type": "keyword"
                },
                
                # Vector embedding con kNN
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
                
                # Información del modelo
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
                
                # Metadata del chunk (desnormalizada para filtros)
                "chunk_text_preview": {
                    "type": "text",
                    "analyzer": "standard",
                    "index": False  # Solo para display, no búsqueda
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
                    "type": "keyword"  # Array de keywords
                },
                
                # Control
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
