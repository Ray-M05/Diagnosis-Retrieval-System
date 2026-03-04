from __future__ import annotations

from dataclasses import dataclass
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


class OpenSearchSearchBackend(SearchBackendPort):
    """
    Backend de búsqueda léxica BM25 sobre OpenSearch.
    Usa el alias (p.ej. clinical_docs) para desacoplar versiones de índice.
    """
    def __init__(self, cfg: OpenSearchSearchConfig) -> None:
        self.cfg = cfg
        self.client = OpenSearch(
            hosts=[{"host": cfg.host, "port": cfg.port}],
            use_ssl=cfg.use_ssl,
            verify_certs=cfg.verify_certs,
            http_compress=True,
            timeout=cfg.request_timeout,
        )

    def search(self, req: SearchRequest) -> SearchResponse:
        body = self._build_query(req)
        raw = self.client.search(index=self.cfg.index_alias, body=body)

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
            doc_id = str(h.get("_id", ""))
            score = float(h.get("_score") or 0.0)

            highlights = h.get("highlight", {}) or {}
            concept_ids = src.get("concept_ids") or []

            hits.append(SearchHit(
                doc_id=doc_id,
                score=score,
                url=str(src.get("url", "")),
                title=str(src.get("title", "")),
                source_domain=str(src.get("source_domain", "")),
                mime_type=str(src.get("mime_type", "")),
                fetched_at=str(src.get("fetched_at", "")),
                highlights={k: list(v) for k, v in highlights.items()},
                concept_ids=list(concept_ids) if isinstance(concept_ids, list) else [],
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
        must_clause: dict[str, Any]
        q = (req.query or "").strip()

        if q:
            must_clause = {
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "sections_text^2", "body"],
                    "type": "best_fields",
                    "operator": req.operator,
                }
            }
        else:
            must_clause = {"match_all": {}}

        filters = []
        f = req.filters

        def terms(field: str, values: Optional[list[str]]) -> None:
            if values:
                filters.append({"terms": {field: values}})

        terms("source_domain", f.source_domains)
        terms("mime_type", f.mime_types)
        terms("seed_group", f.seed_groups)
        terms("seed_id", f.seed_ids)
        terms("concept_ids", f.concept_ids)

        if f.fetched_from or f.fetched_to:
            r: dict[str, Any] = {}
            if f.fetched_from:
                r["gte"] = f.fetched_from
            if f.fetched_to:
                r["lte"] = f.fetched_to
            filters.append({"range": {"fetched_at": r}})

        body: dict[str, Any] = {
            "from": max(0, req.offset),
            "size": max(1, req.k),
            "query": {"bool": {"must": [must_clause], "filter": filters}},
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
