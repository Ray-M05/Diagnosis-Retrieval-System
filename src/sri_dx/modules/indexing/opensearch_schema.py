# src/sri_dx/modules/indexing/opensearch_schema.py
from __future__ import annotations

def build_index_body(*, shards: int = 1, replicas: int = 0) -> dict:
    """
    Índice léxico (BM25 por defecto) + analyzer sencillo (lowercase + asciifolding).
    Compatible con ES-style mapping y OpenSearch.
    """
    return {
        "settings": {
            "number_of_shards": shards,
            "number_of_replicas": replicas,
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
                "url": {"type": "keyword"},
                "source_domain": {"type": "keyword"},
                "fetched_at": {"type": "date"},
                "mime_type": {"type": "keyword"},
                "seed_group": {"type": "keyword"},
                "seed_id": {"type": "keyword"},
                "depth": {"type": "integer"},

                "title": {"type": "text", "analyzer": "folding_analyzer"},
                "sections_text": {"type": "text", "analyzer": "folding_analyzer"},
                "body": {"type": "text", "analyzer": "folding_analyzer"},

                "language": {"type": "keyword"},
                "published_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "author": {"type": "keyword"},

                "content_hash": {"type": "keyword"},
                "char_len": {"type": "integer"},
                "word_count": {"type": "integer"},
                "section_count": {"type": "integer"},

                # Fase D: conceptos clínicos como keywords (array)
                "concept_ids": {"type": "keyword"},
            }
        },
    }
