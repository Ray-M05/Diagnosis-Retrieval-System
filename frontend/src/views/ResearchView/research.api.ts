/**
 * ResearchView API — thin wrappers over the unified /pipeline endpoint.
 *
 * All four "modes" (hybrid, diagnostic, positioned, web) ultimately call
 * POST /pipeline with different stages. Hybrid retrieval always runs;
 * positioning and web_enrichment are activated per mode.
 */

import { runPipeline } from '../../api/client';
import type { PipelineResponse, PositionedResult, WebEnrichmentSummary } from '../../api/client';
import type { DiseaseResult } from './research.types';

export async function researchSearchHybrid(query: string, k: number): Promise<PipelineResponse> {
  return runPipeline({
    query,
    k,
    stages: { web_enrichment: false, positioning: false, generation: false },
  });
}

export async function researchSearchDiseases(query: string, k: number): Promise<DiseaseResult[]> {
  const res = await runPipeline({
    query,
    k,
    stages: { web_enrichment: false, positioning: false, generation: false },
  });
  // The /pipeline endpoint returns DiseaseDTO[] in `hybrid`; map to DiseaseResult shape
  return res.hybrid.map((d, idx) => ({
    disease_name: d.name,
    disease_name_display: d.name,
    aggregated_score: 0,
    evidence_count: d.evidence_count,
    rank: d.rank ?? idx + 1,
    evidence: [],
  }));
}

export async function researchSearchPositioned(query: string, k: number): Promise<PositionedResult[]> {
  const res = await runPipeline({
    query,
    k,
    stages: { web_enrichment: false, positioning: true, generation: false },
  });
  return (res.positioned ?? []) as PositionedResult[];
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
