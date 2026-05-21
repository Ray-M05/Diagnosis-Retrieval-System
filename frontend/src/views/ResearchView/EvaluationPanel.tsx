import React, { useEffect, useMemo, useState } from 'react';
import {
  Upload,
  Download,
  Play,
  BarChart3,
  History,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Database,
} from 'lucide-react';
import {
  runEvaluation,
  fetchSeedQrels,
  listEvaluationRuns,
  getEvaluationRun,
} from './evaluation.api';
import type {
  EvaluationMetrics,
  EvaluationReport,
  EvaluationRunSummary,
  SearchMode,
} from './research.types';

interface EvaluationPanelProps {
  mode: SearchMode;
}

const METRIC_LABELS: { key: keyof EvaluationMetrics; label: string; tooltip: string }[] = [
  { key: 'precision_at_k', label: 'P@k', tooltip: 'Precisión en los top-k recuperados' },
  { key: 'recall_at_k', label: 'R@k', tooltip: 'Fracción de relevantes recuperados en top-k' },
  { key: 'f1_at_k', label: 'F1@k', tooltip: 'Media armónica de P@k y R@k' },
  { key: 'map', label: 'MAP', tooltip: 'Mean Average Precision' },
  { key: 'mrr', label: 'MRR', tooltip: 'Mean Reciprocal Rank' },
  { key: 'ndcg_at_k', label: 'NDCG@k', tooltip: 'Normalized Discounted Cumulative Gain' },
  { key: 'fallout_at_k', label: 'Fallout@k', tooltip: 'Proporción de irrelevantes en el top-k (closed-world)' },
  { key: 'r_precision', label: 'R-Precision', tooltip: 'P@R, con R = |relevantes|' },
];

const fmt = (n: number | undefined) =>
  n === undefined || Number.isNaN(n) ? '—' : n.toFixed(3);

export const EvaluationPanel: React.FC<EvaluationPanelProps> = ({ mode }) => {
  const [qrelsContent, setQrelsContent] = useState<string>('');
  const [qrelsName, setQrelsName] = useState<string>('');
  const [k, setK] = useState<number>(10);
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingSeed, setIsLoadingSeed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [pastRuns, setPastRuns] = useState<EvaluationRunSummary[]>([]);
  const [expandedQueries, setExpandedQueries] = useState<Set<number>>(new Set());

  useEffect(() => {
    listEvaluationRuns().then(setPastRuns).catch(() => { /* ignore */ });
  }, [report]);

  const qrelsLineCount = useMemo(() => {
    return qrelsContent.split('\n').filter((l) => l.trim()).length;
  }, [qrelsContent]);

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setQrelsContent(text);
    setQrelsName(file.name);
    setError(null);
  };

  const onLoadSeed = async () => {
    if (isLoadingSeed) return;
    try {
      setIsLoadingSeed(true);
      setError(null);
      const text = await fetchSeedQrels();
      setQrelsContent(text);
      setQrelsName('test_cases.jsonl (default)');
    } catch (e: any) {
      setError(e?.message ?? 'Could not load seed qrels');
    } finally {
      setIsLoadingSeed(false);
    }
  };

  const onRun = async () => {
    if (!qrelsContent.trim()) {
      setError('Carga un archivo de qrels o usa el seed por defecto.');
      return;
    }
    setIsRunning(true);
    setError(null);
    setExpandedQueries(new Set());
    try {
      const result = await runEvaluation(qrelsContent, mode, k);
      setReport(result);
    } catch (e: any) {
      setError(e?.message ?? 'Evaluation failed');
    } finally {
      setIsRunning(false);
    }
  };

  const onLoadPastRun = async (runId: number) => {
    try {
      const rpt = await getEvaluationRun(runId);
      setReport(rpt);
      setExpandedQueries(new Set());
    } catch (e: any) {
      setError(e?.message ?? `Could not load run ${runId}`);
    }
  };

  const toggleExpand = (idx: number) => {
    setExpandedQueries((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const hasChunkLevel = !!report?.macro_chunk;

  return (
    <main className="flex-1 overflow-y-auto bg-gray-50/30 p-6 md:p-10 space-y-6">
      {/* Header strip — mode + qrels controls */}
      <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-xs">
        <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
          <div>
            <h2 className="text-lg font-extrabold text-gray-900 tracking-tight flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-600" />
              Evaluación IR
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Evaluando modo <span className="font-bold text-indigo-600 uppercase">{mode}</span> contra
              juicios de relevancia (qrels).
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 cursor-pointer hover:border-indigo-300 transition-colors">
              <Upload className="w-3.5 h-3.5" />
              Subir qrels JSONL
              <input
                type="file"
                accept=".jsonl,application/jsonl,text/plain"
                onChange={onFileChange}
                className="hidden"
              />
            </label>
            <button
              type="button"
              onClick={onLoadSeed}
              disabled={isLoadingSeed}
              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:border-indigo-300 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isLoadingSeed ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Download className="w-3.5 h-3.5" />
              )}
              {isLoadingSeed ? 'Cargando…' : 'Cargar seed'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
            <Database className="w-4 h-4 text-gray-400" />
            <div className="text-xs">
              <p className="text-gray-400 font-bold uppercase tracking-tighter leading-none">Qrels</p>
              <p className="text-gray-900 font-bold">
                {qrelsName || 'Ninguno cargado'}{' '}
                {qrelsLineCount > 0 && (
                  <span className="text-gray-500">· {qrelsLineCount} consultas</span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
            <label className="text-xs font-semibold text-gray-600 flex-1 flex justify-between">
              <span>k (cut-off)</span>
              <span className="text-indigo-600 font-bold">{k}</span>
            </label>
            <input
              type="range"
              min={1}
              max={30}
              step={1}
              value={k}
              onChange={(e) => setK(parseInt(e.target.value, 10))}
              className="w-32 accent-indigo-600 cursor-pointer"
            />
          </div>
          <button
            type="button"
            onClick={onRun}
            disabled={isRunning || !qrelsContent.trim()}
            className="inline-flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {isRunning ? 'Evaluando…' : 'Ejecutar evaluación'}
          </button>
        </div>

        {error && (
          <div className="mt-4 px-4 py-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-2 text-xs text-red-800">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {qrelsContent && !report && (
          <div className="mt-3 text-[11px] text-gray-500">
            <span className="font-semibold">Nota:</span> el modo <b>web</b> es no determinista (depende
            de APIs externas) y puede ser más lento. Los demás modos son reproducibles.
          </div>
        )}
      </div>

      {/* Report — macro metrics + per-query table */}
      {report && (
        <>
          {/* Run metadata */}
          <div className="bg-white border border-gray-100 rounded-2xl p-4 text-xs text-gray-600 flex flex-wrap gap-4">
            <span><b>Run:</b> #{report.run_id ?? '—'}</span>
            <span><b>Modo:</b> {report.mode}</span>
            <span><b>k:</b> {report.k}</span>
            <span><b>Nivel:</b> {report.level}</span>
            <span><b>Corpus:</b> {report.corpus_size.toLocaleString()} docs</span>
            <span><b>qrels SHA256:</b> {report.qrels_hash.slice(0, 12)}…</span>
            <span><b>Timestamp:</b> {new Date(report.timestamp).toLocaleString()}</span>
            {report.errors.length > 0 && (
              <span className="text-red-700"><b>Errores:</b> {report.errors.length}</span>
            )}
          </div>

          {/* Macro metric cards — disease level */}
          <MetricGrid title="Macro métricas (a nivel de enfermedad)" metrics={report.macro} />

          {/* Chunk-level metrics */}
          {hasChunkLevel && report.macro_chunk && (
            <MetricGrid title="Macro métricas (a nivel de chunk/documento)" metrics={report.macro_chunk} accent="emerald" />
          )}

          {/* Per-query table */}
          <div className="bg-white border border-gray-100 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 text-sm font-extrabold text-gray-900">
              Detalle por consulta ({report.per_query.length})
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-50/60 text-gray-500 uppercase tracking-tighter font-bold">
                  <tr>
                    <th className="px-3 py-2 text-left">#</th>
                    <th className="px-3 py-2 text-left">Consulta</th>
                    <th className="px-3 py-2 text-right">P@k</th>
                    <th className="px-3 py-2 text-right">R@k</th>
                    <th className="px-3 py-2 text-right">F1@k</th>
                    <th className="px-3 py-2 text-right">MRR</th>
                    <th className="px-3 py-2 text-right">AP</th>
                    <th className="px-3 py-2 text-right">NDCG@k</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {report.per_query.map((row, idx) => {
                    const expanded = expandedQueries.has(idx);
                    return (
                      <React.Fragment key={idx}>
                        <tr className="border-t border-gray-100 hover:bg-gray-50/40">
                          <td className="px-3 py-2 text-gray-400 font-bold">{idx + 1}</td>
                          <td className="px-3 py-2 text-gray-700 max-w-md truncate" title={row.query}>
                            {row.query}
                          </td>
                          <td className="px-3 py-2 text-right font-mono">{fmt(row.disease_metrics.precision_at_k)}</td>
                          <td className="px-3 py-2 text-right font-mono">{fmt(row.disease_metrics.recall_at_k)}</td>
                          <td className="px-3 py-2 text-right font-mono">{fmt(row.disease_metrics.f1_at_k)}</td>
                          <td className="px-3 py-2 text-right font-mono">{fmt(row.disease_metrics.mrr)}</td>
                          <td className="px-3 py-2 text-right font-mono">{fmt(row.disease_metrics.map)}</td>
                          <td className="px-3 py-2 text-right font-mono">{fmt(row.disease_metrics.ndcg_at_k)}</td>
                          <td className="px-3 py-2 text-right">
                            <button
                              type="button"
                              onClick={() => toggleExpand(idx)}
                              className="p-1 text-gray-400 hover:text-indigo-600"
                              aria-label="Expandir detalle"
                            >
                              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>
                          </td>
                        </tr>
                        {expanded && (
                          <tr className="border-t border-gray-100 bg-gray-50/40">
                            <td></td>
                            <td colSpan={8} className="px-3 py-3">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
                                <div>
                                  <p className="font-bold text-gray-500 uppercase tracking-tighter mb-1">
                                    Recuperados (enfermedades)
                                  </p>
                                  {row.retrieved_disease_names.length === 0 ? (
                                    <p className="text-gray-400 italic">— vacío —</p>
                                  ) : (
                                    <ol className="list-decimal list-inside space-y-0.5 text-gray-700">
                                      {row.retrieved_disease_names.map((d, i) => (
                                        <li
                                          key={i}
                                          className={
                                            row.relevant_disease_names.includes(d)
                                              ? 'font-bold text-emerald-700'
                                              : ''
                                          }
                                        >
                                          {d}
                                        </li>
                                      ))}
                                    </ol>
                                  )}
                                </div>
                                <div>
                                  <p className="font-bold text-gray-500 uppercase tracking-tighter mb-1">
                                    Relevantes (qrels)
                                  </p>
                                  <ul className="space-y-0.5 text-gray-700">
                                    {row.relevant_disease_names.map((d, i) => (
                                      <li key={i}>· {d}</li>
                                    ))}
                                  </ul>
                                </div>
                                {row.chunk_metrics && (
                                  <div className="md:col-span-2 mt-1 p-2 bg-emerald-50/50 rounded-lg">
                                    <p className="font-bold text-emerald-700 uppercase tracking-tighter mb-1">
                                      Métricas a nivel de chunk
                                    </p>
                                    <div className="grid grid-cols-4 gap-2 text-emerald-900">
                                      <span>P@k: <b>{fmt(row.chunk_metrics.precision_at_k)}</b></span>
                                      <span>R@k: <b>{fmt(row.chunk_metrics.recall_at_k)}</b></span>
                                      <span>F1@k: <b>{fmt(row.chunk_metrics.f1_at_k)}</b></span>
                                      <span>MRR: <b>{fmt(row.chunk_metrics.mrr)}</b></span>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Past runs */}
      {pastRuns.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-2xl overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 text-sm font-extrabold text-gray-900 flex items-center gap-2">
            <History className="w-4 h-4 text-gray-400" />
            Runs anteriores ({pastRuns.length})
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50/60 text-gray-500 uppercase tracking-tighter font-bold">
                <tr>
                  <th className="px-3 py-2 text-left">#</th>
                  <th className="px-3 py-2 text-left">Timestamp</th>
                  <th className="px-3 py-2 text-left">Modo</th>
                  <th className="px-3 py-2 text-right">k</th>
                  <th className="px-3 py-2 text-right">P@k</th>
                  <th className="px-3 py-2 text-right">MAP</th>
                  <th className="px-3 py-2 text-right">NDCG@k</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {pastRuns.map((run) => (
                  <tr key={run.id} className="border-t border-gray-100 hover:bg-gray-50/40">
                    <td className="px-3 py-2 text-gray-400 font-bold">#{run.id}</td>
                    <td className="px-3 py-2 text-gray-700">{new Date(run.timestamp).toLocaleString()}</td>
                    <td className="px-3 py-2 text-gray-700 uppercase font-semibold">{run.mode}</td>
                    <td className="px-3 py-2 text-right">{run.k}</td>
                    <td className="px-3 py-2 text-right font-mono">{fmt(run.macro?.precision_at_k)}</td>
                    <td className="px-3 py-2 text-right font-mono">{fmt(run.macro?.map)}</td>
                    <td className="px-3 py-2 text-right font-mono">{fmt(run.macro?.ndcg_at_k)}</td>
                    <td className="px-3 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => onLoadPastRun(run.id)}
                        className="text-indigo-600 hover:underline font-semibold"
                      >
                        Cargar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
};

interface MetricGridProps {
  title: string;
  metrics: EvaluationMetrics;
  accent?: 'indigo' | 'emerald';
}

const MetricGrid: React.FC<MetricGridProps> = ({ title, metrics, accent = 'indigo' }) => {
  const ring = accent === 'emerald' ? 'border-emerald-100' : 'border-gray-100';
  const valueColor = accent === 'emerald' ? 'text-emerald-700' : 'text-indigo-700';
  return (
    <div className={`bg-white border ${ring} rounded-2xl p-5 shadow-xs`}>
      <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">{title}</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {METRIC_LABELS.map(({ key, label, tooltip }) => (
          <div
            key={key}
            title={tooltip}
            className="p-3 bg-gray-50/60 rounded-xl flex flex-col gap-1"
          >
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
              {label}
            </span>
            <span className={`text-xl font-extrabold font-mono ${valueColor}`}>
              {fmt(metrics[key])}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
