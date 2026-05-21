/**
 * ResearchView API — thin wrappers over the unified /pipeline endpoint.
 *
 * All four "modes" (hybrid, diagnostic, positioned, web) ultimately call
 * POST /pipeline with different stages. Hybrid retrieval always runs;
 * positioning and web_enrichment are activated per mode.
 */

import { runPipeline } from '../../api/client';
import type { HybridChunk, PipelineResponse, PositionedResult, SufficiencyInfo, WebEnrichmentSummary } from '../../api/client';
import type { DiseaseResult } from './research.types';

export async function researchSearchHybrid(
  query: string,
  k: number,
): Promise<{ chunks: HybridChunk[]; sufficiency: SufficiencyInfo | null }> {
  const res = await runPipeline({
    query,
    k,
    stages: { web_enrichment: false, positioning: false, generation: false, raw_hybrid: true },
  });
  return { chunks: res.hybrid_chunks ?? [], sufficiency: res.sufficiency };
}

export async function researchSearchDiseases(
  query: string,
  k: number,
): Promise<{ diseases: DiseaseResult[]; sufficiency: SufficiencyInfo | null }> {
  const res = await runPipeline({
    query,
    k,
    stages: { web_enrichment: false, positioning: false, generation: false },
  });
  const diseases: DiseaseResult[] = res.hybrid.map((d, idx) => {
    const chunkId = d.feedback_chunk_id ?? '';
    const docId = d.feedback_doc_id ?? '';
    return {
      disease_name: d.name,
      disease_name_display: d.doc_title ?? d.name,
      aggregated_score: d.score ?? 0,
      evidence_count: d.evidence_count,
      rank: d.rank ?? idx + 1,
      evidence: chunkId && docId
        ? [{
            chunk_id: chunkId,
            doc_id: docId,
            rerank_score: 0,
            ner_score: 0,
            combined_score: d.score ?? 0,
            content_preview: d.description ?? '',
            url: d.sourceUrl ?? '',
          }]
        : [],
    };
  });
  return { diseases, sufficiency: res.sufficiency };
}

export async function researchSearchPositioned(
  query: string,
  k: number,
): Promise<{ positioned: PositionedResult[]; sufficiency: SufficiencyInfo | null }> {
  const res = await runPipeline({
    query,
    k,
    stages: { web_enrichment: false, positioning: true, generation: false },
  });
  return { positioned: (res.positioned ?? []) as PositionedResult[], sufficiency: res.sufficiency };
}

export interface WebSearchResult {
  hybrid: PipelineResponse['hybrid'];
  web_enriched: WebEnrichmentSummary | null;
}

export async function researchWebSearch(query: string, k: number): Promise<WebSearchResult> {
  const res = await runPipeline({
    query,
    k,
    stages: { web_enrichment: true, positioning: false, generation: false },
  });
  return { hybrid: res.hybrid, web_enriched: res.web_enriched };
}
