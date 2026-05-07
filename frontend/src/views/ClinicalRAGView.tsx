import React, { useRef, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  ExternalLink,
  FileText,
  Loader2,
  Stethoscope,
  Upload,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { parseChart, streamClinicalRAG } from '../api/client';
import type { Citation, DifferentialDiagnosis, PatientChart, RAGResponse } from '../types';
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

  const [chart, setChart] = useState<PatientChart>(emptyChart());
  const [query, setQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
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

  // -- generate --
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsGenerating(true);
    setStreamedText('');
    setRagResponse(null);
    setError(null);

    await streamClinicalRAG(
      chart,
      query,
      (delta) => setStreamedText((prev) => prev + delta),
      (response) => {
        if (response.error && !response.answer_markdown) {
          setError(response.error);
        } else {
          setRagResponse(response);
        }
        setIsGenerating(false);
      },
      (msg) => {
        setError(msg);
        setIsGenerating(false);
      },
    );
  };

  const displayText = ragResponse?.answer_markdown ?? streamedText;

  return (
    <div className="flex flex-col gap-8">

      {/* Upload + form */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-indigo-500" />
          <h2 className="font-bold text-gray-900">Patient Chart</h2>
          <span className="text-xs text-gray-400">Fill manually or upload a PDF/TXT</span>
        </div>

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

      {/* Query + generate */}
      <form onSubmit={handleGenerate} className="flex gap-3">
        <input
          type="text"
          placeholder="What is your clinical question? e.g. Most likely diagnoses and urgent workup?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1 border border-gray-200 rounded-2xl px-5 py-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 shadow-sm"
        />
        <button
          type="submit"
          disabled={isGenerating || !query.trim()}
          className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-2xl hover:bg-indigo-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-100"
        >
          {isGenerating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Stethoscope className="w-4 h-4" />
          )}
          {isGenerating ? 'Generating...' : 'Generate'}
        </button>
      </form>

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
                {ragResponse.usage.model || 'ollama'}
              </p>
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
