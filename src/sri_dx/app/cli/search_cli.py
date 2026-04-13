from __future__ import annotations

import argparse

from sri_dx.adapters.stores.opensearch_search_backend import (
    OpenSearchSearchBackend, OpenSearchSearchConfig
)
from sri_dx.adapters.stores import (
    OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig
)
from sri_dx.core.schemas.search.search_request import SearchFilters
from sri_dx.usecases.search.search_lexical import SearchLexicalUseCase
from sri_dx.usecases.search.search_semantic import SearchSemanticUseCase
from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig

def main() -> None:
    ap = argparse.ArgumentParser(description="CLI unificada para búsqueda Lexical, Semántica e Híbrida")
    ap.add_argument("--q", required=True, help="Consulta de búsqueda")
    ap.add_argument("--type", choices=["lexical", "semantic", "hybrid"], default="lexical", help="Tipo de búsqueda a ejecutar")
    ap.add_argument("--k", type=int, default=10, help="Número de resultados a retornar")
    ap.add_argument("--offset", type=int, default=0, help="Offset para paginación (solo léxico)")
    
    # Parámetros de conexión
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9200)
    ap.add_argument("--index-alias", default="clinical_docs", help="Alias del índice léxico")
    ap.add_argument("--chunks-index", default="clinical_embeddings_v1", help="Índice de embeddings para vectores")
    ap.add_argument("--lexical-chunks-index", default="clinical_chunks", help="Alias del índice léxico de chunks")
    
    # Filtros
    ap.add_argument("--mime", action="append", default=None, help="mime_type filter (repeatable)")
    ap.add_argument("--domain", action="append", default=None, help="source_domain filter (repeatable)")
    ap.add_argument("--seed-group", action="append", default=None, help="seed_group filter (repeatable)")
    ap.add_argument("--concept", action="append", default=None, help="concept_ids filter (repeatable)")

    # Opciones léxicas/híbridas
    ap.add_argument("--no-facets", action="store_true", help="Desactivar generación de facets")
    ap.add_argument("--no-highlights", action="store_true", help="Desactivar generación de highlights")
    
    # Opciones Semánticas/Híbridas
    ap.add_argument("--fusion", choices=["rrf", "weighted_sum"], default="rrf", help="Método de fusión para Híbrida")
    ap.add_argument("--min-score", type=float, default=0.0, help="Score mínimo semántico")
    
    # Opciones de Reranking
    ap.add_argument("--rerank", action="store_true", help="Activar reranking con Cross-Encoder")
    ap.add_argument("--rerank-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2", help="Modelo de Cross-Encoder")
    ap.add_argument("--rerank-threshold", type=float, default=None, help="Umbral de score para reranking")

    # Opciones de diagnóstico por enfermedades
    ap.add_argument("--diseases", action="store_true", help="Agregar chunks por enfermedad (requiere --type hybrid --rerank)")
    ap.add_argument("--max-diseases", type=int, default=10, help="Máximo de enfermedades a retornar")
    ap.add_argument("--min-ner-score", type=float, default=0.5, help="Confianza mínima de NER para enfermedades")

    args = ap.parse_args()

    filters = SearchFilters(
        mime_types=args.mime,
        source_domains=args.domain,
        seed_groups=args.seed_group,
        concept_ids=args.concept,
    )
    
    metadata_filters = {}
    if args.domain: metadata_filters["source_domain"] = args.domain[0]
    if args.seed_group: metadata_filters["seed_group"] = args.seed_group[0]

    if args.type == "lexical":
        backend = OpenSearchSearchBackend(OpenSearchSearchConfig(
            host=args.host, port=args.port, index_alias=args.index_alias
        ))
        uc = SearchLexicalUseCase(backend=backend)
        res = uc.search(
            query=args.q, k=args.k, offset=args.offset, filters=filters,
            with_facets=not args.no_facets, with_highlights=not args.no_highlights,
        )

        print(f"TOTAL: {res.total_hits} (took={res.took_ms}ms)")
        for i, h in enumerate(res.hits, start=1):
            print("-" * 80)
            print(f"{i}) score={h.score:.4f} doc_id={h.doc_id}")
            print(f"   title={h.title}")
            print(f"   url={h.url}")
            if h.highlights:
                for field, frags in h.highlights.items():
                    if frags:
                        print(f"   highlight[{field}]: {frags[0]}")
                        break

        if res.facets:
            print("\nFACETS:")
            for field, buckets in res.facets.items():
                top = ", ".join([f"{b.key}({b.doc_count})" for b in buckets[:10]])
                print(f"  {field}: {top}")

    elif args.type == "semantic":
        store = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
            host=args.host, port=args.port, index_name=args.chunks_index
        ))
        uc = SearchSemanticUseCase(embedding_store=store)
        res = uc.search(
            query=args.q, k=args.k, min_score=args.min_score, filters=metadata_filters if metadata_filters else None
        )

        print(f"TOP {len(res)} RESULTADOS SEMÁNTICOS")
        for i, h in enumerate(res, start=1):
            print("-" * 80)
            print(f"{i}) score={h.score:.4f} doc_id={h.doc_id} chunk_id={h.chunk_id}")
            print(f"   section={h.section_heading}")
            print(f"   text='{h.chunk_text_preview}...'")

    elif args.type == "hybrid":
        backend = OpenSearchSearchBackend(OpenSearchSearchConfig(
            host=args.host, port=args.port, index_alias=args.lexical_chunks_index,
            search_fields=["section_heading^3", "chunk_text^1"]
        ))
        store = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
            host=args.host, port=args.port, index_name=args.chunks_index
        ))

        config = HybridSearchConfig(
            fusion_method=args.fusion,
            min_semantic_score=args.min_score,
            use_reranking=args.rerank or args.diseases,
            rerank_model_name=args.rerank_model,
            rerank_score_threshold=args.rerank_threshold,
            rerank_top_k=args.k
        )

        uc = SearchHybridUseCase(lexical_backend=backend, embedding_store=store, config=config)

        if args.diseases:
            from sri_dx.usecases.search.tow_stage_retrieval_pipeline import (
                TwoStageRetrievalPipeline, TwoStageRetrievalConfig,
            )
            pipeline_config = TwoStageRetrievalConfig(
                hybrid_candidates=100,
                final_results=args.k,
                cross_encoder_model=args.rerank_model,
                score_threshold=args.rerank_threshold,
                min_ner_score=args.min_ner_score,
                max_diseases=args.max_diseases,
            )
            pipeline = TwoStageRetrievalPipeline(
                hybrid_search=uc,
                config=pipeline_config,
            )
            diseases = pipeline.search_diseases(query=args.q)
            pipeline.print_disease_results(diseases)
        else:
            res = uc.search(
                query=args.q, k=args.k, filters=filters, metadata_filters=metadata_filters if metadata_filters else None
            )

            title = f"TOP {len(res)} RESULTADOS HÍBRIDOS"
            if args.rerank:
                title += " + RERANKING"
            print(f"{title} (Fusión: {args.fusion})")

            for i, h in enumerate(res, start=1):
                print("-" * 80)
                print(f"{i}) score={h.score:.4f} doc_id={h.doc_id} chunk_id={h.chunk_id}")
                if h.rerank_score:
                    print(f"   [Cross-Encoder] Score: {h.rerank_score:.4f}")
                if h.lexical_score:
                    print(f"   [Léxico] Score: {h.lexical_score:.4f}")
                if h.vector_score:
                    print(f"   [Semántico] Score: {h.vector_score:.4f}")
                if "chunk_text_preview" in h.metadata:
                    print(f"   chunk='{h.metadata['chunk_text_preview']}...'")
                elif "chunk_text" in h.metadata:
                    print(f"   chunk='{h.metadata['chunk_text'][:200]}...'")
                if "title" in h.metadata:
                    print(f"   title={h.metadata['title']}")
                if "url" in h.metadata:
                    print(f"   url={h.metadata['url']}")

if __name__ == "__main__":
    main()
