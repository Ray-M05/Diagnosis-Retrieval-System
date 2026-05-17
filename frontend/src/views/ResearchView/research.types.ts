export interface HybridResult {
  doc_id: string;
  chunk_id: string;
  score: number;
  lexical_score?: number | null;
  vector_score?: number | null;
  rerank_score?: number;
  fusion_method: string;
  title?: string | null;
  section_heading?: string | null;
  url?: string | null;
  source_domain?: string | null;
  chunk_text_preview?: string;
  /** @deprecated old nested shape — kept for backward compatibility */
  metadata?: {
    doc_id?: string;
    url?: string;
    title?: string;
    chunk_text?: string;
    chunk_text_preview?: string;
    section_heading?: string;
    [key: string]: unknown;
  };
}

export interface DiseaseEvidence {
  chunk_id: string;
  doc_id: string;
  rerank_score: number;
  ner_score: number;
  combined_score: number;
  content_preview: string;
  url: string;
}

export interface DiseaseResult {
  disease_name: string;
  disease_name_display: string;
  aggregated_score: number;
  evidence_count: number;
  evidence: DiseaseEvidence[];
  rank: number;
}

export interface PositionedEvidence {
  chunk_id: string;
  url: string;
  cross_encoder_score?: number;
  content_preview?: string;
}

export interface PositionedResult {
  rank: number;
  disease_name_display: string;
  final_score: number;
  relevance_label: string;
  matched_symptoms: string[];
  source_domains: string[];
  explanation: string[];
  evidences: PositionedEvidence[];
}

export interface WebSearchResult {
  disease_name: string;
  disease_name_display: string;
  aggregated_score: number;
  evidence_count: number;
  rank: number;
  evidence: DiseaseEvidence[];
}

export interface WebSearchResponse {
  diseases: WebSearchResult[];
  web_enriched: boolean;
  docs_added: number;
  api_retrieved: number;
  elapsed_seconds: number;
}

export type SearchMode = 'hybrid' | 'diagnostic' | 'positioned' | 'web';
