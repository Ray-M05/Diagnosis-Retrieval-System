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
// /search/diseases
// ---------------------------------------------------------------------------

export async function searchDiseases(query: string, k = 10): Promise<Disease[]> {
  const res = await fetch(`${API_BASE}/search/diseases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  const data = await res.json();
  return (data.diseases ?? []) as Disease[];
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

// ---------------------------------------------------------------------------
// /rag/clinical  (SSE streaming)
// ---------------------------------------------------------------------------

/**
 * Stream a clinical RAG response.
 *
 * @param chart     PatientChart to send
 * @param query     Physician's clinical question
 * @param onToken   Called for each text delta as it streams in
 * @param onDone    Called once with the final RAGResponse
 * @param onError   Called on network / server error
 */
export async function streamClinicalRAG(
  chart: PatientChart,
  query: string,
  onToken: (delta: string) => void,
  onDone: (response: RAGResponse) => void,
  onError: (message: string) => void,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/rag/clinical`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chart, query }),
    });
  } catch (err) {
    onError(`Network error: ${String(err)}`);
    return;
  }

  if (!res.ok) {
    const detail = await res.text();
    onError(`Server error ${res.status}: ${detail}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError('No response body from server.');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by \n\n
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? ''; // keep incomplete frame

    for (const frame of frames) {
      if (!frame.trim()) continue;

      const lines = frame.split('\n');
      const eventLine = lines.find((l) => l.startsWith('event:'));
      const dataLine = lines.find((l) => l.startsWith('data:'));
      const eventType = eventLine?.slice('event:'.length).trim();
      const data = dataLine?.slice('data:'.length).trim() ?? '';

      if (eventType === 'response') {
        try {
          onDone(JSON.parse(data) as RAGResponse);
        } catch {
          onError('Failed to parse final response from server.');
        }
      } else if (eventType === 'error') {
        onError(data);
      } else {
        // Plain data frame = text delta; unescape \n back to newlines
        if (data) onToken(data.replace(/\\n/g, '\n'));
      }
    }
  }
}
