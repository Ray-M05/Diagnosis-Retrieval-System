"""ClinicalRAGUseCase — end-to-end clinical RAG pipeline.

Flow (both sync and streaming):
  1. Enrich patient chart (NER + concept extraction)
  2. Compose retrieval query from chart entities + physician's query
  3. Retrieve top-K chunks via TwoStageRetrievalPipeline.search()
  4. (Optional) Get candidate diseases via pipeline.search_diseases()
  5. Build context blocks (dedup, truncate, budget)
  6. Build prompt (system + user message)
  7. Call LLM (generate or stream)
  8. Parse [CHUNK n] citations from generated text → validate → RAGResponse

Streaming variant (run_streaming):
  Yields str deltas while the LLM generates, then yields a final RAGResponse
  object once generation is complete. Callers can detect the RAGResponse by
  checking isinstance(item, RAGResponse).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Iterator

from sri_dx.core.ports.generation.llm_port import GenerationRequest, LLMMessage, LLMPort
from sri_dx.core.schemas.rag.patient_chart import PatientChart
from sri_dx.core.schemas.rag.rag_response import (
    Citation,
    DifferentialDiagnosis,
    RAGResponse,
    RAGUsage,
)
from sri_dx.modules.rag.context_builder import ContextBlock, ContextBuilder
from sri_dx.modules.rag.patient_chart_enricher import PatientChartEnricher
from sri_dx.modules.rag.prompt_builder import ClinicalPromptBuilder
from sri_dx.modules.rag.query_composer import QueryComposer
from sri_dx.usecases.search.two_stage_retrieval_pipeline import TwoStageRetrievalPipeline

logger = logging.getLogger(__name__)

# Matches [CHUNK 1], [CHUNK 12], etc. in generated text
_CHUNK_REF_RE = re.compile(r"\[CHUNK\s+(\d+)\]", re.IGNORECASE)


@dataclass
class ClinicalRAGConfig:
    max_context_chunks: int = 10
    max_output_tokens: int = 1500
    temperature: float = 0.2
    include_disease_hints: bool = True


@dataclass
class ClinicalRAGUseCase:
    pipeline: TwoStageRetrievalPipeline
    llm: LLMPort
    enricher: PatientChartEnricher = field(default_factory=PatientChartEnricher)
    composer: QueryComposer = field(default_factory=QueryComposer)
    context_builder: ContextBuilder = field(default_factory=ContextBuilder)
    prompt_builder: ClinicalPromptBuilder = field(default_factory=ClinicalPromptBuilder)
    config: ClinicalRAGConfig = field(default_factory=ClinicalRAGConfig)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        chart: PatientChart,
        user_query: str,
        *,
        preretrieved_chunks: list | None = None,
        preretrieved_diseases: list | None = None,
    ) -> RAGResponse:
        """Blocking call — returns the complete RAGResponse.

        If `preretrieved_chunks` is provided, skips the internal pipeline.search()
        and uses those chunks as context. Same for `preretrieved_diseases` (skips
        pipeline.search_diseases). This lets callers compose web-enrichment +
        positioning + RAG without re-doing retrieval.
        """
        t0 = time.monotonic()

        retrieval = self._retrieve(
            chart, user_query,
            preretrieved_chunks=preretrieved_chunks,
            preretrieved_diseases=preretrieved_diseases,
        )
        if retrieval is None:
            return self._no_evidence_response(time.monotonic() - t0)

        blocks, diseases, composed_query = retrieval
        prompt = self.prompt_builder.build(
            chart, self.enricher.enrich(chart), user_query, blocks, diseases
        )

        req = self._build_gen_request(prompt.system, prompt.user_message)
        try:
            result = self.llm.generate(req)
        except RuntimeError as exc:
            return RAGResponse(
                answer_markdown="",
                error=str(exc),
                elapsed_seconds=time.monotonic() - t0,
            )

        citations = self._parse_citations(result.text, blocks)
        return RAGResponse(
            answer_markdown=result.text,
            citations=citations,
            candidate_diseases=self._to_differential(diseases),
            composed_query=composed_query,
            elapsed_seconds=time.monotonic() - t0,
            usage=RAGUsage(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                eval_duration_ms=result.eval_duration_ms,
                model=result.model,
            ),
        )

    def run_streaming(
        self,
        chart: PatientChart,
        user_query: str,
        *,
        preretrieved_chunks: list | None = None,
        preretrieved_diseases: list | None = None,
    ) -> Iterator[str | RAGResponse]:
        """
        Streaming call.

        Yields str deltas as the LLM generates text, then yields a final
        RAGResponse (check with isinstance(item, RAGResponse)).

        See `run()` for the meaning of preretrieved_chunks/diseases.
        """
        t0 = time.monotonic()

        retrieval = self._retrieve(
            chart, user_query,
            preretrieved_chunks=preretrieved_chunks,
            preretrieved_diseases=preretrieved_diseases,
        )
        if retrieval is None:
            msg = "No relevant evidence found in the corpus for this query."
            yield msg
            yield RAGResponse(
                answer_markdown=msg,
                error="no_evidence",
                elapsed_seconds=time.monotonic() - t0,
            )
            return

        blocks, diseases, composed_query = retrieval

        # Re-enrich for prompt (already done inside _retrieve for query composition)
        entities = self.enricher.enrich(chart)
        prompt = self.prompt_builder.build(chart, entities, user_query, blocks, diseases)

        req = self._build_gen_request(prompt.system, prompt.user_message)

        buffer = ""
        try:
            for delta in self.llm.stream(req):
                buffer += delta
                yield delta
        except RuntimeError as exc:
            yield RAGResponse(
                answer_markdown=buffer,
                error=str(exc),
                elapsed_seconds=time.monotonic() - t0,
            )
            return

        citations = self._parse_citations(buffer, blocks)
        yield RAGResponse(
            answer_markdown=buffer,
            citations=citations,
            candidate_diseases=self._to_differential(diseases),
            composed_query=composed_query,
            elapsed_seconds=time.monotonic() - t0,
            usage=RAGUsage(model=self.llm.__class__.__name__),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _retrieve(
        self,
        chart: PatientChart,
        user_query: str,
        *,
        preretrieved_chunks: list | None = None,
        preretrieved_diseases: list | None = None,
    ) -> tuple[list[ContextBlock], list, str] | None:
        """Run enrichment → compose → retrieve. Returns (blocks, diseases, query) or None.

        When preretrieved_* are passed, skips the corresponding pipeline calls.
        """
        entities = self.enricher.enrich(chart)
        composed = self.composer.compose(user_query, entities, chart.language)

        logger.info("RAG query: %s", composed.semantic_query[:120])

        if preretrieved_chunks is not None:
            chunks = preretrieved_chunks
        else:
            chunks = self.pipeline.search(
                query=composed.semantic_query,
                final_results=self.config.max_context_chunks,
            )

        if not chunks:
            logger.warning("No chunks retrieved for query: %s", composed.semantic_query[:80])
            return None

        if preretrieved_diseases is not None:
            diseases = preretrieved_diseases
        else:
            diseases = []
            if self.config.include_disease_hints:
                try:
                    diseases = self.pipeline.search_diseases(
                        query=composed.semantic_query,
                        final_results=self.config.max_context_chunks,
                    )
                except Exception as exc:
                    logger.warning("Disease aggregation failed (non-fatal): %s", exc)

        blocks = self.context_builder.build(chunks)
        return blocks, diseases, composed.semantic_query

    def _build_gen_request(self, system: str, user_message: str) -> GenerationRequest:
        return GenerationRequest(
            system=system,
            messages=[LLMMessage(role="user", content=user_message)],
            max_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature,
        )

    @staticmethod
    def _parse_citations(text: str, blocks: list[ContextBlock]) -> list[Citation]:
        """Extract and validate [CHUNK n] references from generated text."""
        block_map = {b.index: b for b in blocks}
        seen: set[int] = set()
        citations: list[Citation] = []

        for m in _CHUNK_REF_RE.finditer(text):
            idx = int(m.group(1))
            if idx in seen:
                continue
            seen.add(idx)
            block = block_map.get(idx)
            if block:
                citations.append(Citation(
                    chunk_index=idx,
                    chunk_id=block.chunk_id,
                    doc_id=block.doc_id,
                    url=block.url,
                    source_domain=block.source_domain,
                    section_heading=block.section_heading,
                    text_preview=block.text[:200],
                    valid=True,
                ))
            else:
                # LLM referenced a non-existent chunk
                citations.append(Citation(
                    chunk_index=idx,
                    chunk_id="",
                    doc_id="",
                    url="",
                    source_domain="",
                    section_heading="",
                    text_preview="",
                    valid=False,
                ))

        return citations

    @staticmethod
    def _to_differential(diseases: list) -> list[DifferentialDiagnosis]:
        result: list[DifferentialDiagnosis] = []
        for d in diseases:
            urls = list({ev.url for ev in d.evidence if ev.url})
            result.append(DifferentialDiagnosis(
                name=d.disease_name_display,
                rank=d.rank,
                evidence_count=d.evidence_count,
                urls=urls[:3],
            ))
        return result

    @staticmethod
    def _no_evidence_response(elapsed: float) -> RAGResponse:
        return RAGResponse(
            answer_markdown="No relevant evidence found in the corpus for this query. "
                            "Try rephrasing with more specific clinical terms.",
            error="no_evidence",
            elapsed_seconds=elapsed,
        )
