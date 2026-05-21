import React, { useRef, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ExternalLink,
  FileText,
  Globe,
  Loader2,
  MapPin,
  Sparkles,
  Stethoscope,
  Upload,
} from 'lucide-react';
import { SearchBar } from '../components/SearchBar';
import { InsufficiencyBanner } from '../components/InsufficiencyBanner';
import { WebEnrichmentBanner } from '../components/WebEnrichmentBanner';
import { WebDocumentCard } from '../components/WebDocumentCard';
import { motion, AnimatePresence } from 'motion/react';
import { parseChart, streamPipeline } from '../api/client';
import type { Citation, DifferentialDiagnosis, PatientChart, RAGResponse, Disease } from '../types';
import type { PositionedResult, SufficiencyInfo, WebEnrichmentSummary } from '../api/client';
import type { SearchBarModifier, SearchBarModifiers } from '../components/SearchBar';
import { emptyChart } from '../types';

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function splitCSV(raw: string): string[] {
  return raw
    .split(/[,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function joinCSV(arr: string[]): string {
  return arr.join(', ');
}

// Input that lets the user type freely (including commas) and only converts
// to array on blur — avoids losing the cursor mid-word on every keystroke.
const CSVInput: React.FC<{
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  className?: string;
}> = ({ value, onChange, placeholder, className }) => {
  const [raw, setRaw] = React.useState(() => joinCSV(value));

  // Keep local state in sync when the parent resets the chart (e.g. file upload)
  React.useEffect(() => {
    setRaw(joinCSV(value));
  }, [value.join(',')]);

  return (
    <input
      type="text"
      placeholder={placeholder}
      value={raw}
      onChange={(e) => setRaw(e.target.value)}
      onBlur={() => onChange(splitCSV(raw))}
      className={className}
    />
  );
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const CitationCard: React.FC<{ cite: Citation }> = ({ cite }) => {
  if (!cite.valid) return null;
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 flex flex-col gap-1 shadow-sm">
      <div className="flex items-center gap-2 text-xs text-gray-400 font-medium">
        <span className="bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-bold">
          CHUNK {cite.chunk_index}
        </span>
        <span>{cite.source_domain}</span>
        {cite.section_heading && <span>· {cite.section_heading}</span>}
      </div>
      <p className="text-sm text-gray-600 leading-relaxed">{cite.text_preview}</p>
      {cite.url && (
        <a
          href={cite.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-indigo-500 hover:text-indigo-700 flex items-center gap-1 mt-1"
        >
          <ExternalLink className="w-3 h-3" /> {cite.url.slice(0, 70)}
        </a>
      )}
    </div>
  );
};

const DiseaseChip: React.FC<{ d: DifferentialDiagnosis }> = ({ d }) => (
  <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3 flex flex-col gap-1">
    <div className="flex items-center gap-2">
      <span className="text-indigo-600 font-bold text-sm">#{d.rank}</span>
      <span className="font-semibold text-gray-800 text-sm">{d.name}</span>
      <span className="ml-auto text-xs text-gray-400">{d.evidence_count} chunks</span>
    </div>
    {d.urls[0] && (
      <a
        href={d.urls[0]}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-indigo-400 hover:text-indigo-600 flex items-center gap-1"
      >
        <ExternalLink className="w-3 h-3" /> {d.urls[0].slice(0, 60)}
      </a>
    )}
  </div>
);

// Render markdown-ish text with basic newline → <br> support
const MarkdownAnswer: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.split('\n');
  return (
    <div className="prose prose-indigo max-w-none text-gray-800 text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) {
          return (
            <h3 key={i} className="text-base font-bold text-gray-900 mt-4 mb-1">
              {line.slice(3)}
            </h3>
          );
        }
        if (line.startsWith('### ')) {
          return (
            <h4 key={i} className="text-sm font-semibold text-gray-700 mt-3 mb-0.5">
              {line.slice(4)}
            </h4>
          );
        }
        if (line.trim() === '') return <br key={i} />;
        return <p key={i} className="my-0">{line}</p>;
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

export const ClinicalRAGView: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [chartOpen, setChartOpen] = useState(false);
  const [chart, setChart] = useState<PatientChart>(emptyChart());
  const [query, setQuery] = useState('');
  const [modifiers, setModifiers] = useState<SearchBarModifiers>({ web: false, positioned: false });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
  const [positionedResults, setPositionedResults] = useState<PositionedResult[] | null>(null);
  const [hybridResults, setHybridResults] = useState<Disease[] | null>(null);
  const [webEnrichment, setWebEnrichment] = useState<WebEnrichmentSummary | null>(null);
  const [sufficiency, setSufficiency] = useState<SufficiencyInfo | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -- helpers to update nested chart fields --
  const setField = <K extends keyof PatientChart>(key: K, value: PatientChart[K]) =>
    setChart((c) => ({ ...c, [key]: value }));

  const setDemoField = <K extends keyof PatientChart['demographics']>(
    key: K,
    value: PatientChart['demographics'][K],
  ) => setChart((c) => ({ ...c, demographics: { ...c.demographics, [key]: value } }));

  const setVS = <K extends keyof NonNullable<PatientChart['vital_signs']>>(
    key: K,
    value: NonNullable<PatientChart['vital_signs']>[K],
  ) =>
    setChart((c) => ({
      ...c,
      vital_signs: { ...(c.vital_signs ?? {}), [key]: value } as PatientChart['vital_signs'],
    }));

  // -- file upload --
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setUploadWarning(null);
    try {
      const result = await parseChart(file);
      setChart(result.chart);
      if (result.warning) setUploadWarning(result.warning);
    } catch (err) {
      setUploadWarning(`Could not parse file: ${String(err)}`);
    } finally {
      setIsUploading(false);
      // reset input so same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const clearResults = () => {
    setStreamedText('');
    setRagResponse(null);
    setPositionedResults(null);
    setHybridResults(null);
    setWebEnrichment(null);
    setSufficiency(null);
    setEvidenceOpen(false);
    setError(null);
  };

  const handleModifierToggle = (m: SearchBarModifier) => {
    setModifiers((prev) => ({ ...prev, [m]: !prev[m] }));
    clearResults();
  };

  // -- generate --
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsGenerating(true);
    clearResults();

    await streamPipeline(
      {
        query,
        chart,
        k: 10,
        stages: {
          web_enrichment: modifiers.web,
          positioning: modifiers.positioned,
          generation: true,
        },
      },
      {
        onStages: (stages) => {
          setHybridResults(stages.hybrid);
          setPositionedResults(stages.positioned);
          setWebEnrichment(stages.web_enriched);
          setSufficiency(stages.sufficiency);
        },
        onToken: (delta) => setStreamedText((prev) => prev + delta),
        onDone: (response) => {
          if (response.error && !response.answer_markdown) {
            setError(response.error);
          } else {
            setRagResponse(response);
          }
          setIsGenerating(false);
        },
        onError: (msg) => {
          setError(msg);
          setIsGenerating(false);
        },
      },
    );
  };

  const displayText = ragResponse?.answer_markdown ?? streamedText;

  return (
    <div className="flex flex-col gap-8">

      {/* Upload + form */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
        {/* Accordion header */}
        <button
          type="button"
          onClick={() => setChartOpen((v) => !v)}
          className="w-full flex items-center gap-3 p-6 text-left hover:bg-gray-50/50 transition-colors cursor-pointer"
        >
          <FileText className="w-5 h-5 text-indigo-500 shrink-0" />
          <h2 className="font-bold text-gray-900 flex-1">Patient Chart</h2>
          <span className="text-xs text-gray-400 hidden sm:block">
            {chartOpen ? 'Hide chart' : 'Show patient chart'}
          </span>
          <ChevronDown
            className={`w-4 h-4 text-gray-400 transition-transform shrink-0 ${chartOpen ? 'rotate-180' : ''}`}
          />
        </button>

        <AnimatePresence initial={false}>
          {chartOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
        <div className="px-6 pb-6 flex flex-col gap-6 border-t border-gray-50">

        {/* Upload button */}
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            className="hidden"
            onChange={handleFileUpload}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 rounded-xl text-sm font-medium hover:bg-indigo-100 transition-colors disabled:opacity-50"
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {isUploading ? 'Parsing...' : 'Upload PDF or TXT'}
          </button>
          {uploadWarning && (
            <p className="mt-2 text-xs text-amber-700 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> {uploadWarning}
            </p>
          )}
        </div>

        {/* Demographics row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-gray-500 font-medium">Age</label>
            <input
              type="number"
              min={0}
              max={130}
              placeholder="—"
              value={chart.demographics.age ?? ''}
              onChange={(e) =>
                setDemoField('age', e.target.value ? Number(e.target.value) : null)
              }
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 font-medium">Sex</label>
            <select
              value={chart.demographics.sex}
              onChange={(e) =>
                setDemoField('sex', e.target.value as PatientChart['demographics']['sex'])
              }
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            >
              <option value="unknown">—</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-500 font-medium">Comorbidities (comma-separated)</label>
            <CSVInput
              value={chart.demographics.comorbidities}
              onChange={(v) => setDemoField('comorbidities', v)}
              placeholder="DM2, HTN, CKD..."
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
        </div>

        {/* Chief complaint — full width, symptoms embedded in query */}
        <div>
          <label className="text-xs text-gray-500 font-medium">Chief Complaint</label>
          <input
            type="text"
            placeholder="e.g. Frequent urination and excessive thirst for 6 weeks"
            value={chart.chief_complaint}
            onChange={(e) => setField('chief_complaint', e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
        </div>

        {/* Vitals row */}
        <div>
          <label className="text-xs text-gray-500 font-medium">Vital Signs</label>
          <div className="mt-1 grid grid-cols-2 md:grid-cols-5 gap-2">
            {(
              [
                { key: 'heart_rate_bpm', label: 'HR (bpm)', type: 'number' },
                { key: 'blood_pressure', label: 'BP (mmHg)', type: 'text' },
                { key: 'respiratory_rate', label: 'RR (/min)', type: 'number' },
                { key: 'spo2_percent', label: 'SpO2 (%)', type: 'number' },
                { key: 'temperature_c', label: 'Temp (°C)', type: 'number' },
              ] as const
            ).map(({ key, label, type }) => (
              <div key={key}>
                <label className="text-[11px] text-gray-400">{label}</label>
                <input
                  type={type}
                  placeholder="—"
                  value={(chart.vital_signs?.[key] as string | number | undefined) ?? ''}
                  onChange={(e) =>
                    setVS(key, e.target.value ? (type === 'number' ? Number(e.target.value) : e.target.value) : null)
                  }
                  className="mt-0.5 w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Physical exam + Labs + Imaging */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {(
            [
              { key: 'physical_findings', label: 'Physical Findings' },
              { key: 'lab_results', label: 'Lab Results' },
              { key: 'imaging', label: 'Imaging' },
            ] as const
          ).map(({ key, label }) => (
            <div key={key}>
              <label className="text-xs text-gray-500 font-medium">{label}</label>
              <textarea
                rows={3}
                placeholder="—"
                value={chart[key]}
                onChange={(e) => setField(key, e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
              />
            </div>
          ))}
        </div>

        {/* Medications + Allergies */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 font-medium">Current Medications (comma-separated)</label>
            <CSVInput
              value={chart.current_medications}
              onChange={(v) => setField('current_medications', v)}
              placeholder="metformin 1g BID, lisinopril 20mg..."
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 font-medium">Allergies (comma-separated)</label>
            <CSVInput
              value={chart.allergies}
              onChange={(v) => setField('allergies', v)}
              placeholder="NKDA or penicillin..."
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
        </div>

        {/* Social History + Family History */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 font-medium">Social History</label>
            <textarea
              rows={3}
              placeholder="Smoking, alcohol, occupation, diet, physical activity..."
              value={chart.social_history}
              onChange={(e) => setField('social_history', e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 font-medium">Family History</label>
            <textarea
              rows={3}
              placeholder="Father: MI at 58. Mother: HTN, stroke. Uncle: kidney disease..."
              value={chart.family_history}
              onChange={(e) => setField('family_history', e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
            />
          </div>
        </div>

        {/* Additional notes */}
        <div>
          <label className="text-xs text-gray-500 font-medium">Additional Notes</label>
          <textarea
            rows={3}
            placeholder="Free text — anything not captured above"
            value={chart.additional_notes}
            onChange={(e) => setField('additional_notes', e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
          />
        </div>
        </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Query + generate */}
      <SearchBar
        value={query}
        onChange={setQuery}
        onSubmit={handleGenerate}
        onClear={() => { setQuery(''); clearResults(); }}
        isLoading={isGenerating}
        placeholder="What is your clinical question? e.g. Most likely diagnoses and urgent workup?"
        submitLabel={!modifiers.web && !modifiers.positioned ? 'Generate' : 'Search'}
        showModeToggles
        modifiers={modifiers}
        onModifierToggle={handleModifierToggle}
      />

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-2xl px-5 py-4 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Streaming / final answer */}
      <AnimatePresence>
        {displayText && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col gap-4"
          >
            <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm">
              <Stethoscope className="w-4 h-4" />
              Clinical Assessment
              {isGenerating && (
                <span className="ml-2 w-2 h-4 bg-indigo-400 animate-pulse rounded-sm" />
              )}
            </div>

            <MarkdownAnswer text={displayText} />

            {/* Stats */}
            {ragResponse && (
              <p className="text-xs text-gray-400 mt-2">
                {ragResponse.elapsed_seconds.toFixed(1)}s ·{' '}
                {ragResponse.usage.output_tokens} tokens ·{' '}
                {ragResponse.usage.model || 'groq'}
              </p>
            )}

            {/* Insufficiency banner — shown when generation completed and knowledge was insufficient */}
            {!isGenerating && sufficiency && !sufficiency.sufficient && !modifiers.web && (
              <InsufficiencyBanner
                sufficiency={sufficiency}
                onActivateWeb={() => setModifiers((prev) => ({ ...prev, web: true }))}
              />
            )}

            {/* Evidence tag — only when web or positioning stages produced results */}
            {!isGenerating && (positionedResults || webEnrichment?.triggered) && (
              <div className="border-t border-gray-100 pt-3 mt-1">
                <button
                  type="button"
                  onClick={() => setEvidenceOpen((v) => !v)}
                  className="group inline-flex items-center gap-2 px-3 py-1.5 bg-linear-to-r from-indigo-50 to-blue-50 border border-indigo-100 rounded-xl text-xs font-semibold text-indigo-700 hover:from-indigo-100 hover:to-blue-100 transition-all cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {evidenceOpen ? 'Hide evidence' : 'View expanded evidence'}
                  {webEnrichment?.triggered && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-600/90 text-white rounded-full text-[10px]">
                      <Globe className="w-2.5 h-2.5" /> Web · {webEnrichment.api_retrieved}
                    </span>
                  )}
                  {positionedResults && positionedResults.length > 0 && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-indigo-600/90 text-white rounded-full text-[10px]">
                      <MapPin className="w-2.5 h-2.5" /> {positionedResults.length} positioned
                    </span>
                  )}
                  <ChevronDown className={`w-3 h-3 transition-transform ${evidenceOpen ? 'rotate-180' : ''}`} />
                </button>

                <AnimatePresence initial={false}>
                  {evidenceOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="pt-4 flex flex-col gap-5">
                        {positionedResults && positionedResults.length > 0 && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2 text-gray-600 font-semibold text-xs uppercase tracking-wide">
                              <MapPin className="w-3.5 h-3.5 text-indigo-500" /> Clinical positioning
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {positionedResults.map((r) => {
                                const colorMap: Record<string, string> = { high: 'bg-green-100 text-green-700', alta: 'bg-green-100 text-green-700', medium: 'bg-amber-100 text-amber-700', media: 'bg-amber-100 text-amber-700', low: 'bg-gray-100 text-gray-500', baja: 'bg-gray-100 text-gray-500' };
                                const color = colorMap[r.relevance_label?.toLowerCase()] ?? 'bg-gray-100 text-gray-500';
                                return (
                                  <div key={r.rank} className="bg-gray-50 border border-gray-100 rounded-xl p-3 text-xs flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-[10px] font-black flex items-center justify-center shrink-0">{r.rank}</span>
                                      <span className="font-semibold text-gray-800 truncate">{r.disease_name_display}</span>
                                    </div>
                                    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full shrink-0 ${color}`}>{r.relevance_label}</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {webEnrichment?.triggered && (
                          <div className="space-y-3">
                            <div className="flex items-center gap-2 text-gray-600 font-semibold text-xs uppercase tracking-wide">
                              <Globe className="w-3.5 h-3.5 text-blue-500" /> Indexed web documents
                            </div>
                            <WebEnrichmentBanner summary={webEnrichment} />
                            {hybridResults && hybridResults.length > 0 && webEnrichment.docs_added > 0 && (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {hybridResults.map((d, idx) => (
                                  <WebDocumentCard
                                    key={`${d.id}|${idx}`}
                                    disease={d}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Citations */}
      {ragResponse && ragResponse.citations.filter((c) => c.valid).length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-gray-700 font-semibold text-sm">
            <BookOpen className="w-4 h-4 text-indigo-500" />
            Evidence Citations ({ragResponse.citations.filter((c) => c.valid).length})
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {ragResponse.citations.filter((c) => c.valid).map((cite) => (
              <CitationCard key={cite.chunk_index} cite={cite} />
            ))}
          </div>
        </motion.div>
      )}

      {/* Candidate diseases */}
      {ragResponse && ragResponse.candidate_diseases.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-gray-700 font-semibold text-sm">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Candidate Diseases (NER aggregator)
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {ragResponse.candidate_diseases.map((d) => (
              <DiseaseChip key={d.rank} d={d} />
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};
