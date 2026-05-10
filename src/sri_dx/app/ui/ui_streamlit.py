"""UI Streamlit integrada con el pipeline completo de SRI-DX."""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200


# ---------------------------------------------------------------------------
# Inicialización lazy de componentes (cacheados en session_state)
# ---------------------------------------------------------------------------

def _build_pipeline(fusion: str, candidates: int, final_k: int, rerank_model: str):
    """Construye el TwoStageRetrievalPipeline conectado a OpenSearch."""
    from sri_dx.adapters.stores.opensearch_search_backend import (
        OpenSearchSearchBackend, OpenSearchSearchConfig,
    )
    from sri_dx.adapters.stores import OpenSearchEmbeddingSink, OpenSearchEmbeddingConfig
    from sri_dx.usecases.search.search_hybrid import SearchHybridUseCase
    from sri_dx.usecases.search.schemas.hybrid_search_config import HybridSearchConfig
    from sri_dx.usecases.search.two_stage_retrieval_pipeline import (
        TwoStageRetrievalPipeline, TwoStageRetrievalConfig,
    )

    lexical_backend = OpenSearchSearchBackend(OpenSearchSearchConfig(
        host=OPENSEARCH_HOST,
        port=OPENSEARCH_PORT,
        index_alias="clinical_chunks",
        search_fields=["section_heading^3", "chunk_text^1"],
    ))
    embedding_store = OpenSearchEmbeddingSink(OpenSearchEmbeddingConfig(
        host=OPENSEARCH_HOST,
        port=OPENSEARCH_PORT,
        index_name="clinical_embeddings_v1",
    ))

    hybrid_config = HybridSearchConfig(
        fusion_method=fusion,
        lexical_k=candidates,
        semantic_k=candidates,
        use_reranking=False,  # reranking lo hace el pipeline de 2 etapas
    )
    hybrid_search = SearchHybridUseCase(
        lexical_backend=lexical_backend,
        embedding_store=embedding_store,
        config=hybrid_config,
    )

    pipeline_config = TwoStageRetrievalConfig(
        hybrid_candidates=candidates,
        final_results=final_k,
        cross_encoder_model=rerank_model,
        device="cpu",
        batch_size=32,
    )
    return TwoStageRetrievalPipeline(hybrid_search=hybrid_search, config=pipeline_config)


def get_pipeline(fusion: str, candidates: int, final_k: int, rerank_model: str):
    """Obtiene pipeline cacheado en session_state."""
    cache_key = f"pipeline_{fusion}_{candidates}_{final_k}_{rerank_model}"
    if cache_key not in st.session_state:
        with st.spinner("Cargando modelos (primera vez ~15s)..."):
            st.session_state[cache_key] = _build_pipeline(fusion, candidates, final_k, rerank_model)
    return st.session_state[cache_key]


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="SRI-DX: Diagnosis Retrieval System",
        page_icon="🩺",
        layout="wide",
    )

    st.title("🩺 SRI-DX — Sistema de Recuperación para Diagnóstico")
    st.caption("Bio_ClinicalBERT + BM25 + Cross-Encoder reranking | MSD Manuals · NHS · Mayo Clinic")

    # ---- Sidebar --------------------------------------------------------
    st.sidebar.header("⚙️ Configuración")

    search_mode = st.sidebar.radio(
        "Modo de búsqueda",
        ["🔬 Híbrido + Reranking", "🦠 Diagnóstico por Enfermedades", "📌 Condiciones posicionadas"],
        help="Híbrido: chunks rankeados. Enfermedades: agregación simple. Posicionadas: ranking clínico multicriterio.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Parámetros")

    fusion_method = st.sidebar.selectbox("Fusión híbrida", ["rrf", "weighted_sum"], index=0)
    k_candidates = st.sidebar.slider("Candidatos híbridos", 20, 200, 100, step=10)
    k_final = st.sidebar.slider("Resultados finales", 3, 20, 10)
    rerank_model = st.sidebar.selectbox(
        "Modelo Cross-Encoder",
        [
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "cross-encoder/ms-marco-MiniLM-L-12-v2",
        ],
        index=0,
    )

    if "Enfermedades" in search_mode or "Condiciones" in search_mode:
        st.sidebar.markdown("---")
        st.sidebar.subheader("NER / Condiciones")
        min_ner_score = st.sidebar.slider("Confianza mínima NER", 0.1, 1.0, 0.5, step=0.05)
        max_diseases = st.sidebar.slider("Máx. enfermedades", 3, 20, 10)
    else:
        min_ner_score = 0.5
        max_diseases = 10

    if "Condiciones" in search_mode:
        positioned_results = st.sidebar.slider("Máx. condiciones posicionadas", 3, 20, 10)
    else:
        positioned_results = 10

    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Índices activos**\n"
        "- `clinical_chunks` (léxica)\n"
        "- `clinical_embeddings_v1` (vectorial)\n\n"
        f"OpenSearch: `{OPENSEARCH_HOST}:{OPENSEARCH_PORT}`"
    )

    # ---- Query input ----------------------------------------------------
    query = st.text_input(
        "🔍 Consulta clínica:",
        placeholder="Ej: chest pain shortness of breath fatigue",
        help="Describe síntomas, signos o condición clínica en inglés.",
    )

    col1, col2 = st.columns([1, 5])
    search_btn = col1.button("Buscar", type="primary", use_container_width=True)

    if search_btn and not query.strip():
        st.error("Por favor, ingrese una consulta.")
        return

    if not search_btn:
        st.markdown(
            """
            **Ejemplos de consultas:**
            - `diabetes mellitus insulin treatment hyperglycemia`
            - `chest pain shortness of breath heart failure`
            - `fever cough pneumonia respiratory infection`
            - `seizures epilepsy anticonvulsant medication`
            - `multiple sclerosis demyelination neurological`
            """
        )
        return

    # ---- Ejecución ------------------------------------------------------
    try:
        pipeline = get_pipeline(fusion_method, k_candidates, k_final, rerank_model)

        # Override config de diseases si aplica
        if "Enfermedades" in search_mode or "Condiciones" in search_mode:
            pipeline.config.min_ner_score = min_ner_score
            pipeline.config.max_diseases = max_diseases
            pipeline.config.positioned_results = positioned_results

        t0 = time.time()

        if "Enfermedades" in search_mode:
            with st.spinner(f"Búsqueda híbrida → reranking → NER → agregación..."):
                diseases = pipeline.search_diseases(query=query)
            elapsed = time.time() - t0
            _render_diseases(diseases, query, elapsed)
        elif "Condiciones" in search_mode:
            with st.spinner(f"Búsqueda híbrida → reranking → NER → posicionamiento..."):
                positioned = pipeline.search_positioned(
                    query=query,
                    positioned_results=positioned_results,
                )
            elapsed = time.time() - t0
            _render_positioned(positioned, query, elapsed)
        else:
            with st.spinner(f"Búsqueda híbrida ({fusion_method}) → reranking..."):
                results = pipeline.search(query=query)
            elapsed = time.time() - t0
            _render_chunks(results, query, elapsed, fusion_method)

    except Exception as e:
        st.error(f"Error ejecutando búsqueda: {e}")
        st.exception(e)

    st.warning(
        "⚠️ Este sistema es una herramienta de apoyo a la investigación. "
        "No sustituye el criterio clínico profesional."
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _render_chunks(results, query: str, elapsed: float, fusion: str):
    """Muestra resultados de chunks rerankeados."""
    st.success(f"✅ {len(results)} resultados en {elapsed:.2f}s — fusión: `{fusion}` + cross-encoder reranking")

    if not results:
        st.info("Sin resultados para esta consulta.")
        return

    for i, r in enumerate(results, 1):
        url = r.metadata.get("url", "")
        title = r.metadata.get("title") or url.split("/")[-1].replace("-", " ").title() or f"Documento {r.doc_id[:8]}"
        source = r.metadata.get("source_domain", url.split("/")[2] if "://" in url else "")
        content = r.content or r.metadata.get("chunk_text", "") or r.metadata.get("content", "")

        with st.expander(f"**#{i}** — {title[:80]} `[{source}]`  score={r.rerank_score:.3f}", expanded=i <= 3):
            col_scores, col_content = st.columns([1, 3])

            with col_scores:
                st.metric("Cross-Encoder", f"{r.rerank_score:.3f}")
                if r.lexical_score:
                    st.metric("BM25", f"{r.lexical_score:.2f}")
                if r.vector_score:
                    st.metric("Semántico", f"{r.vector_score:.3f}")
                if url:
                    st.markdown(f"[🔗 Fuente]({url})")

            with col_content:
                if content:
                    st.markdown(content[:600] + ("..." if len(content) > 600 else ""))
                else:
                    st.caption("Sin contenido disponible.")


def _render_diseases(diseases, query: str, elapsed: float):
    """Muestra resultados agregados por enfermedad."""
    st.success(f"✅ {len(diseases)} enfermedades identificadas en {elapsed:.2f}s")

    if not diseases:
        st.info("No se identificaron enfermedades para esta consulta. Prueba con más síntomas.")
        return

    for d in diseases:
        header = f"**#{d.rank} {d.disease_name_display}** — {d.evidence_count} chunks de evidencia"
        with st.expander(header, expanded=d.rank <= 3):

            col_info, col_evidence = st.columns([1, 2])

            with col_info:
                st.markdown(f"**Chunks de evidencia:** {d.evidence_count}")
                urls = list({ev.url for ev in d.evidence if ev.url})
                if urls:
                    st.markdown("**Fuentes:**")
                    for url in urls[:3]:
                        domain = url.split("/")[2] if "://" in url else url
                        st.markdown(f"- [{domain}]({url})")

            with col_evidence:
                if d.evidence:
                    st.markdown("**Fragmentos de evidencia:**")
                    for ev in d.evidence[:2]:
                        snippet = ev.content_preview
                        st.markdown(f"> {snippet[:300]}{'...' if len(snippet) > 300 else ''}")
                        st.caption(f"rerank={ev.rerank_score:.3f} · ner={ev.ner_score:.3f}")


def _render_positioned(positioned, query: str, elapsed: float):
    """Muestra condiciones clinicas posicionadas."""
    st.success(f"✅ {len(positioned)} condiciones posicionadas en {elapsed:.2f}s")

    if not positioned:
        st.info("No se identificaron condiciones clínicas asociadas para esta consulta.")
        return

    for result in positioned:
        header = (
            f"**#{result.rank} {result.disease_name_display}** — "
            f"{result.relevance_label} · score={result.final_score:.3f}"
        )
        with st.expander(header, expanded=result.rank <= 3):
            col_info, col_evidence = st.columns([1, 2])

            with col_info:
                if result.matched_symptoms:
                    st.markdown("**Coincidencias:**")
                    st.write(", ".join(result.matched_symptoms))

                if result.source_domains:
                    st.markdown("**Fuentes:**")
                    for domain in result.source_domains[:5]:
                        st.markdown(f"- `{domain}`")

                with st.expander("Scores por componente"):
                    st.json(result.component_scores)

            with col_evidence:
                if result.explanation:
                    st.markdown("**Explicación:**")
                    for reason in result.explanation:
                        st.markdown(f"- {reason}")

                if result.evidences:
                    st.markdown("**Evidencias principales:**")
                    for ev in result.evidences[:3]:
                        snippet = ev.content_preview or ev.text
                        st.markdown(f"> {snippet[:300]}{'...' if len(snippet) > 300 else ''}")
                        caption = f"chunk={ev.chunk_id}"
                        if ev.cross_encoder_score is not None:
                            caption += f" · ce={ev.cross_encoder_score:.3f}"
                        if ev.source_domain:
                            caption += f" · {ev.source_domain}"
                        st.caption(caption)
                        if ev.url:
                            st.markdown(f"[Fuente]({ev.url})")


if __name__ == "__main__":
    main()
