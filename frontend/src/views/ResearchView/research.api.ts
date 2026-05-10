import type { HybridResult, DiseaseResult, PositionedResult, WebSearchResponse } from './research.types';

const API_BASE = 'http://localhost:8000/api';

export interface HybridSearchParams {
  query: string;
  k: number;
  fusion_method: string;
  use_reranking: boolean;
  hybrid_candidates: number;
}

export interface DiagnoseParams {
  query: string;
  max_diseases: number;
  min_ner_score: number;
  hybrid_candidates: number;
}

export async function researchSearchHybrid(params: HybridSearchParams): Promise<HybridResult[]> {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Error en búsqueda híbrida: ${res.statusText}`);
  return res.json();
}

export async function researchSearchDiseases(params: DiagnoseParams): Promise<DiseaseResult[]> {
  const res = await fetch(`${API_BASE}/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Error en diagnóstico: ${res.statusText}`);
  return res.json();
}

export interface PositioningParams {
  query: string;
  k: number;
  hybrid_candidates: number;
  final_results: number;
  min_ner_score: number;
}

export async function researchSearchPositioned(params: PositioningParams): Promise<PositionedResult[]> {
  const res = await fetch(`http://localhost:8000/search/positioned`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Error en posicionamiento: ${res.statusText}`);
  return res.json();
}

export interface WebSearchParams {
  query: string;
  k: number;
  hybrid_candidates: number;
  final_results: number;
  min_ner_score: number;
}

export async function researchWebSearch(params: WebSearchParams): Promise<WebSearchResponse> {
  const res = await fetch(`http://localhost:8000/search/web`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Error en búsqueda web: ${res.statusText}`);
  return res.json();
}
