from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any

from opensearchpy import OpenSearch

from sri_dx.core.ports.search.search_backend import SearchBackendPort
from sri_dx.core.schemas.search.search_request import SearchRequest
from sri_dx.core.schemas.search.search_response import (
    SearchResponse, SearchHit, FacetBucket, DocumentRecord
)


@dataclass(frozen=True)
class OpenSearchSearchConfig:
    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    verify_certs: bool = False
    index_alias: str = "clinical_docs"
    request_timeout: int = 30
    search_fields: list[str] = field(default_factory=lambda: ["title^3", "sections_text^2", "body"])


class OpenSearchSearchBackend(SearchBackendPort):
    """
    Backend de búsqueda léxica BM25 sobre OpenSearch.
    Usa el alias (p.ej. clinical_docs) para desacoplar versiones de índice.
    """
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        self.client = OpenSearch(
            hosts=[{"host": cfg.host, "port": cfg.port}],
            use_ssl=getattr(cfg, "use_ssl", False),
            verify_certs=getattr(cfg, "verify_certs", False),
            http_compress=True,
            timeout=getattr(cfg, "request_timeout", 30),
        )

    def search(self, req: SearchRequest) -> SearchResponse:
        body = self._build_query(req)
        index = getattr(self.cfg, "index_alias", getattr(self.cfg, "alias_name", "clinical_docs"))
        raw = self.client.search(index=index, body=body)

        took = raw.get("took")
        hits_block = raw.get("hits", {})
        total = hits_block.get("total", 0)
        if isinstance(total, dict):
            total_hits = int(total.get("value", 0))
        else:
            total_hits = int(total)

        hits: list[SearchHit] = []
        for h in hits_block.get("hits", []):
            src = h.get("_source", {}) or {}
            
            _id_val = str(h.get("_id", ""))
            inner_doc_id = src.get("doc_id")
            if inner_doc_id and inner_doc_id != _id_val:
                doc_id = str(inner_doc_id)
                chunk_id = _id_val
            else:
                doc_id = _id_val
                chunk_id = None
                
            score = float(h.get("_score") or 0.0)

            highlights = h.get("highlight", {}) or {}
            concept_ids = src.get("concept_ids") or []
            ner_entities = src.get("ner_entities") or []

            hits.append(SearchHit(
                doc_id=doc_id,
                chunk_id=chunk_id,
                score=score,
                url=str(src.get("url", "")),
                title=str(src.get("title", "")),
                source_domain=str(src.get("source_domain", "")),
                mime_type=str(src.get("mime_type", "")),
                fetched_at=str(src.get("fetched_at", "")),
                content=str(src.get("body", src.get("sections_text", src.get("chunk_text", "")))),
                highlights={k: list(v) for k, v in highlights.items()},
                concept_ids=list(concept_ids) if isinstance(concept_ids, list) else [],
                ner_entities=list(ner_entities) if isinstance(ner_entities, list) else [],
            ))

        facets: dict[str, list[FacetBucket]] = {}
        aggs = raw.get("aggregations") or {}
        for field, agg in aggs.items():
            buckets = agg.get("buckets") or []
            facets[field] = [
                FacetBucket(key=str(b.get("key")), doc_count=int(b.get("doc_count", 0)))
                for b in buckets
            ]

        return SearchResponse(
            total_hits=total_hits,
            hits=hits,
            facets=facets,
            took_ms=int(took) if took is not None else None,
        )

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        try:
            raw = self.client.get(index=self.cfg.index_alias, id=doc_id)
        except Exception:
            return None
        src = raw.get("_source")
        if not isinstance(src, dict):
            return None
        return DocumentRecord(doc_id=doc_id, source=src)

    # -------------------- internals --------------------

    def _build_query(self, req: SearchRequest) -> dict[str, Any]:
        q = (req.query or "").strip()
        f = req.filters
        
        # Construir la cláusula principal (must_clause o should_expansion)
        if q and f.concept_ids:
            # Expansión: match por texto O por concepto
            main_clause = {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": q,
                                "fields": getattr(self.cfg, "search_fields", ["title", "body"]),
                                "type": "best_fields",
                                "operator": req.operator,
                                "boost": 1.0
                            }
                        },
                        {
                            "terms": {
                                "concept_ids": f.concept_ids,
                                "boost": 3.0  # Boost alto para matches exactos de concepto
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        elif q:
            main_clause = {
                "multi_match": {
                    "query": q,
                    "fields": getattr(self.cfg, "search_fields", ["title", "body"]),
                    "type": "best_fields",
                    "operator": req.operator,
                }
            }
        else:
            main_clause = {"match_all": {}}

        # Filtros estrictos (concept_ids se mueve a main_clause si hay q, sino se queda aquí)
        filtering_clauses = []
        
        def terms_filter(field: str, values: Optional[list[str]]) -> None:
            if values:
                filtering_clauses.append({"terms": {field: values}})

        terms_filter("source_domain", f.source_domains)
        terms_filter("mime_type", f.mime_types)
        terms_filter("seed_group", f.seed_groups)
        terms_filter("seed_id", f.seed_ids)
        
        # Si NO hay query, concept_ids actúan como filtro estricto
        if not q:
            terms_filter("concept_ids", f.concept_ids)

        if f.fetched_from or f.fetched_to:
            r: dict[str, Any] = {}
            if f.fetched_from:
                r["gte"] = f.fetched_from
            if f.fetched_to:
                r["lte"] = f.fetched_to
            filtering_clauses.append({"range": {"fetched_at": r}})

        body: dict[str, Any] = {
            "from": max(0, req.offset),
            "size": max(1, req.k),
            "query": {"bool": {"must": [main_clause], "filter": filtering_clauses}},
        }

        if req.return_highlights:
            body["highlight"] = {
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
                "fields": {
                    "title": {"number_of_fragments": 0},
                    "sections_text": {"fragment_size": 160, "number_of_fragments": 2},
                    "body": {"fragment_size": 160, "number_of_fragments": 3},
                },
            }

        # Facets (aggs)
        if req.facet_fields:
            body["aggs"] = {
                field: {"terms": {"field": field, "size": req.facet_size}}
                for field in req.facet_fields
            }

        return body
