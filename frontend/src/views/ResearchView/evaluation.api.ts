/**
 * Evaluation API — qrels upload, batch run, history.
 *
 * Talks to the FastAPI `/evaluation/*` endpoints. Base URL is taken from
 * VITE_API_BASE (same as the main client).
 */

import type {
  EvaluationReport,
  EvaluationRunSummary,
  SearchMode,
} from './research.types';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000';

export async function runEvaluation(
  qrelsContent: string,
  mode: SearchMode,
  k: number,
): Promise<EvaluationReport> {
  const form = new FormData();
  const blob = new Blob([qrelsContent], { type: 'application/jsonl' });
  form.append('qrels', blob, 'qrels.jsonl');
  form.append('mode', mode);
  form.append('k', String(k));

  const res = await fetch(`${API_BASE}/evaluation/run`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Evaluation failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchSeedQrels(): Promise<string> {
  const res = await fetch(`${API_BASE}/evaluation/seed-qrels`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Could not load seed qrels (${res.status}): ${text}`);
  }
  return res.text();
}

export async function listEvaluationRuns(): Promise<EvaluationRunSummary[]> {
  const res = await fetch(`${API_BASE}/evaluation/runs`);
  if (!res.ok) throw new Error(`Could not list runs: ${res.status}`);
  const data = await res.json();
  return data.runs ?? [];
}

export async function getEvaluationRun(runId: number): Promise<EvaluationReport> {
  const res = await fetch(`${API_BASE}/evaluation/runs/${runId}`);
  if (!res.ok) throw new Error(`Could not fetch run ${runId}: ${res.status}`);
  return res.json();
}
