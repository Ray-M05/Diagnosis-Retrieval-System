export interface SearchParams {
  query: string;
  k?: number;
  fusion_method?: string;
  use_reranking?: boolean;
  rerank_model?: string;
  hybrid_candidates?: number;
}

export interface DiagnoseParams {
  query: string;
  max_diseases?: number;
  min_ner_score?: number;
  hybrid_candidates?: number;
}

export interface PositionedParams {
  query: string;
  k?: number;
  min_ner_score?: number;
  hybrid_candidates?: number;
  final_results?: number;
}

const API_BASE_URL = 'http://localhost:8000/api';

export const apiService = {
  async searchHybrid(params: SearchParams) {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
    if (!response.ok) throw new Error('Error in hybrid search');
    return response.json();
  },

  async searchDiseases(params: DiagnoseParams) {
    const response = await fetch(`${API_BASE_URL}/diagnose`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
    if (!response.ok) throw new Error('Error in disease diagnosis');
    return response.json();
  },

  async searchPositioned(params: PositionedParams) {
    const response = await fetch(`${API_BASE_URL}/positioned`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
    if (!response.ok) throw new Error('Error in positioned search');
    return response.json();
  },
};
