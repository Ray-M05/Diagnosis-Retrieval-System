// ---------------------------------------------------------------------------
// Domain types — mirror the Python pydantic schemas
// ---------------------------------------------------------------------------

export interface VitalSigns {
  temperature_c?: number | null;
  heart_rate_bpm?: number | null;
  blood_pressure?: string | null;
  respiratory_rate?: number | null;
  spo2_percent?: number | null;
}

export interface Demographics {
  age?: number | null;
  sex: 'M' | 'F' | 'other' | 'unknown';
  pregnancy_status?: boolean | null;
  comorbidities: string[];
}

export interface PatientChart {
  demographics: Demographics;
  chief_complaint: string;
  symptoms: string[];
  physical_findings: string;
  vital_signs?: VitalSigns | null;
  lab_results: string;
  imaging: string;
  current_medications: string[];
  allergies: string[];
  additional_notes: string;
  language: 'en' | 'es';
}

export interface Citation {
  chunk_index: number;
  chunk_id: string;
  doc_id: string;
  url: string;
  source_domain: string;
  section_heading: string;
  text_preview: string;
  valid: boolean;
}

export interface DifferentialDiagnosis {
  name: string;
  rank: number;
  evidence_count: number;
  urls: string[];
}

export interface RAGUsage {
  input_tokens: number;
  output_tokens: number;
  eval_duration_ms: number;
  model: string;
}

export interface RAGResponse {
  answer_markdown: string;
  citations: Citation[];
  candidate_diseases: DifferentialDiagnosis[];
  composed_query: string;
  elapsed_seconds: number;
  usage: RAGUsage;
  error?: string | null;
}

// Shape the React DiseaseCard expects (mirrors DiseaseDTO from dto.py)
export interface Disease {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  source: string;
  sourceUrl: string;
  evidence_count: number;
  rank: number;
}

export interface ParseChartResponse {
  chart: PatientChart;
  extraction_failed: boolean;
  warning?: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  llm: 'ready' | 'unreachable';
  opensearch: 'ready' | 'unreachable';
  version: string;
}

export const emptyChart = (): PatientChart => ({
  demographics: { sex: 'unknown', comorbidities: [] },
  chief_complaint: '',
  symptoms: [],
  physical_findings: '',
  vital_signs: null,
  lab_results: '',
  imaging: '',
  current_medications: [],
  allergies: [],
  additional_notes: '',
  language: 'en',
});
