/**
 * API client — all calls to the FastAPI backend go through here.
 * Base URL is configured via VITE_API_BASE env var (default: http://localhost:8000).
 */

import type {
  Disease,
  ParseChartResponse,
  PatientChart,
  RAGResponse,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// /pipeline — composable retrieval + (web) + (positioning) + (RAG generation)
// ---------------------------------------------------------------------------

export interface PipelineStages {
  web_enrichment: boolean;
  positioning: boolean;
  generation: boolean;
}

export interface PositionedResult {
  rank: number;
  disease_name_display: string;
  final_score: number;
  relevance_label: string;
  matched_symptoms: string[];
  explanation: string[];
}

export interface WebEnrichmentSummary {
  triggered: boolean;
  docs_added: number;
  chunks_added: number;
}

export interface SufficiencyInfo {
  sufficient: boolean;
  insufficiency_score: number;
  rank_confidence: number;
  useful_count: number;
  symptom_coverage: number;
  source_diversity: number;
  failed_criteria: string[];
}

export interface PipelineResponse {
  query: string;
  hybrid: Disease[];
  positioned: PositionedResult[] | null;
  web_enriched: WebEnrichmentSummary | null;
  sufficiency: SufficiencyInfo | null;
  elapsed_seconds: number;
}

export interface PipelineRequest {
  query: string;
  stages: PipelineStages;
  chart?: PatientChart | null;
  k?: number;
}

/**
 * Non-streaming call (stages.generation === false).
 * Returns a full PipelineResponse once the server finishes.
 */
export async function runPipeline(req: PipelineRequest): Promise<PipelineResponse> {
  if (req.stages.generation) {
    throw new Error('runPipeline does not support generation. Use streamPipeline instead.');
  }
  const res = await fetch(`${API_BASE}/pipeline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...req, k: req.k ?? 10 }),
  });
  if (!res.ok) throw new Error(`Pipeline failed: ${res.statusText}`);
  return res.json() as Promise<PipelineResponse>;
}

export interface StreamPipelineCallbacks {
  onStages?: (stages: PipelineResponse) => void;
  onToken: (delta: string) => void;
  onDone: (response: RAGResponse) => void;
  onError: (message: string) => void;
}

/**
 * Streaming call (stages.generation === true). Required: req.chart.
 *
 * Server-Sent Event flow:
 *   event: stages    → PipelineResponse (web+positioning results, fired once)
 *   data: <delta>    → LLM text token
 *   event: response  → final RAGResponse (fired once)
 *   event: error     → error message
 */
export async function streamPipeline(
  req: PipelineRequest,
  cb: StreamPipelineCallbacks,
): Promise<void> {
  if (!req.stages.generation) {
    cb.onError('streamPipeline requires stages.generation = true.');
    return;
  }
  if (!req.chart) {
    cb.onError('streamPipeline requires a chart.');
    return;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...req, k: req.k ?? 10 }),
    });
  } catch (err) {
    cb.onError(`Network error: ${String(err)}`);
    return;
  }

  if (!res.ok) {
    const detail = await res.text();
    cb.onError(`Server error ${res.status}: ${detail}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    cb.onError('No response body from server.');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';

    for (const frame of frames) {
      if (!frame.trim()) continue;

      const lines = frame.split('\n');
      const eventLine = lines.find((l) => l.startsWith('event:'));
      const dataLine = lines.find((l) => l.startsWith('data:'));
      const eventType = eventLine?.slice('event:'.length).trim();
      const data = dataLine?.slice('data:'.length).trim() ?? '';

      if (eventType === 'stages') {
        try {
          cb.onStages?.(JSON.parse(data) as PipelineResponse);
        } catch {
          // Non-fatal — stages preview is optional UI sugar
        }
      } else if (eventType === 'response') {
        try {
          cb.onDone(JSON.parse(data) as RAGResponse);
        } catch {
          cb.onError('Failed to parse final response from server.');
        }
      } else if (eventType === 'error') {
        cb.onError(data);
      } else {
        if (data) cb.onToken(data.replace(/\\n/g, '\n'));
      }
    }
  }
}

// ---------------------------------------------------------------------------
// /rag/parse-chart
// ---------------------------------------------------------------------------

export async function parseChart(file: File): Promise<ParseChartResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/rag/parse-chart`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`Parse failed: ${res.statusText}`);
  return res.json() as Promise<ParseChartResponse>;
}
