from __future__ import annotations

import argparse

from sri_dx.adapters.stores.opensearch_search_backend import (
    OpenSearchSearchBackend, OpenSearchSearchConfig
)
from sri_dx.core.schemas.search_request import SearchFilters
from sri_dx.usecases.search_lexical import SearchLexicalUseCase


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True, help="consulta")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9200)
    ap.add_argument("--index-alias", default="clinical_docs")

    ap.add_argument("--mime", action="append", default=None, help="mime_type filter (repeatable)")
    ap.add_argument("--domain", action="append", default=None, help="source_domain filter (repeatable)")
    ap.add_argument("--seed-group", action="append", default=None, help="seed_group filter (repeatable)")
    ap.add_argument("--concept", action="append", default=None, help="concept_ids filter (repeatable)")

    ap.add_argument("--no-facets", action="store_true")
    ap.add_argument("--no-highlights", action="store_true")
    args = ap.parse_args()

    backend = OpenSearchSearchBackend(OpenSearchSearchConfig(
        host=args.host,
        port=args.port,
        index_alias=args.index_alias,
    ))
    uc = SearchLexicalUseCase(backend=backend)

    filters = SearchFilters(
        mime_types=args.mime,
        source_domains=args.domain,
        seed_groups=args.seed_group,
        concept_ids=args.concept,
    )

    res = uc.search(
        query=args.q,
        k=args.k,
        offset=args.offset,
        filters=filters,
        with_facets=not args.no_facets,
        with_highlights=not args.no_highlights,
    )

    print(f"TOTAL: {res.total_hits} (took={res.took_ms}ms)")
    for i, h in enumerate(res.hits, start=1):
        print("-" * 80)
        print(f"{i}) score={h.score:.4f} doc_id={h.doc_id}")
        print(f"   title={h.title}")
        print(f"   url={h.url}")
        if h.highlights:
            # imprime 1 highlight corto
            for field, frags in h.highlights.items():
                if frags:
                    print(f"   highlight[{field}]: {frags[0]}")
                    break

    if res.facets:
        print("\nFACETS:")
        for field, buckets in res.facets.items():
            top = ", ".join([f"{b.key}({b.doc_count})" for b in buckets[:10]])
            print(f"  {field}: {top}")


if __name__ == "__main__":
    main()
