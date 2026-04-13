from __future__ import annotations

def build_chunks_index_body(*, vector_dim: int = 768, shards: int = 1, replicas: int = 0) -> dict:
    """
    Define el mapping de OpenSearch para el índice de chunks.
    Incluye soporte para kNN (vector search).
    """
    return {
        "settings": {
            "number_of_shards": shards,
            "number_of_replicas": replicas,
            "index.knn": True,  # Habilita kNN en el índice
            "analysis": {
                "analyzer": {
                    "folding_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    }
                }
            },
        },
        "mappings": {
            "properties": {
                # Identificadores
                "chunk_id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                
                # Origen y Metadatos
                "url": {"type": "keyword"},
                "source_domain": {"type": "keyword"},
                "fetched_at": {"type": "date"},
                "mime_type": {"type": "keyword"},
                "seed_group": {"type": "keyword"},
                "seed_id": {"type": "keyword"},
                "depth": {"type": "integer"},

                # Trazabilidad Sección/Chunk
                "section_heading": {
                    "type": "text", 
                    "analyzer": "folding_analyzer",
                    "fields": {
                        "raw": {"type": "keyword"}
                    }
                },
                "section_index": {"type": "integer"},
                "chunk_index": {"type": "integer"},
                "start_char": {"type": "integer"},
                "end_char": {"type": "integer"},

                # Texto y Lenguaje
                "chunk_text": {"type": "text", "analyzer": "folding_analyzer"},
                "language": {"type": "keyword"},

                # Contenido y Versión
                "content_hash": {"type": "keyword"},
                "chunk_hash": {"type": "keyword"},

                # Enriquecimiento (Fase D)
                "concept_ids": {"type": "keyword"},
                
                # Entidades Named Entity Recognition
                "ner_entities": {
                    "type": "nested",
                    "properties": {
                        "label": {"type": "keyword"},
                        "text": {
                            "type": "text",
                            "analyzer": "folding_analyzer",
                            "fields": {
                                "raw": {"type": "keyword"}
                            }
                        },
                        "start_char": {"type": "integer"},
                        "end_char": {"type": "integer"},
                        "score": {"type": "float"}
                    }
                },

                # Vectorial (Fase 4: RAG/ANN)
                "embedding": {
                    "type": "knn_vector",
                    "dimension": vector_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "l2",
                        "engine": "nmslib",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 16
                        }
                    }
                }
            }
        }
    }
