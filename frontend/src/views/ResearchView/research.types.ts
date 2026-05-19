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
  doc_id: string;
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
  /** Top-evidence chunk/doc identifiers used by the feedback flow. */
  feedback_chunk_id?: string | null;
  feedback_doc_id?: string | null;
}

export interface WebSearchResponse {
  diseases: WebSearchResult[];
  web_enriched: boolean;
  docs_added: number;
  api_retrieved: number;
  elapsed_seconds: number;
}

export type SearchMode = 'hybrid' | 'diagnostic' | 'positioned' | 'web';

// ---------------------------------------------------------------------------
// Evaluation module — qrels-based IR metric reports
// ---------------------------------------------------------------------------

export interface EvaluationMetrics {
  precision_at_k: number;
  recall_at_k: number;
  f1_at_k: number;
  map: number;
  mrr: number;
  ndcg_at_k: number;
  fallout_at_k: number;
  r_precision: number;
}

export interface PerQueryResult {
  query: string;
  retrieved_disease_names: string[];
  relevant_disease_names: string[];
  disease_metrics: EvaluationMetrics;
  retrieved_chunk_ids?: string[] | null;
  relevant_chunk_ids?: string[] | null;
  chunk_metrics?: EvaluationMetrics | null;
}

export type EvaluationLevel = 'disease' | 'chunk' | 'both';

export interface EvaluationReport {
  run_id: number | null;
  mode: SearchMode;
  k: number;
  level: EvaluationLevel;
  qrels_hash: string;
  corpus_size: number;
  timestamp: string;
  macro: EvaluationMetrics;
  macro_chunk: EvaluationMetrics | null;
  per_query: PerQueryResult[];
  errors: { query: string; error: string }[];
}

export interface EvaluationRunSummary {
  id: number;
  timestamp: string;
  mode: SearchMode;
  k: number;
  level: EvaluationLevel;
  qrels_hash: string;
  corpus_size: number;
  macro: EvaluationMetrics;
  macro_chunk: EvaluationMetrics | null;
}
