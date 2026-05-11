import React, { useState } from 'react';
import { Search, Globe } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { DiseaseCard } from '../components/DiseaseCard';
import { SearchBar } from '../components/SearchBar';
import { runPipeline } from '../api/client';
import type { Disease } from '../types';
import type { PipelineResponse, PositionedResult } from '../api/client';
import type { SearchBarMode } from '../components/SearchBar';

const relevanceColor: Record<string, string> = {
  alta: 'bg-green-100 text-green-700',
  media: 'bg-amber-100 text-amber-700',
  baja: 'bg-gray-100 text-gray-500',
};

const PositionedCard: React.FC<{ result: PositionedResult }> = ({ result }) => {
  const [open, setOpen] = useState(false);
  const color = relevanceColor[result.relevance_label?.toLowerCase()] ?? 'bg-gray-100 text-gray-500';

  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-indigo-50 text-indigo-600 text-xs font-black flex items-center justify-center shrink-0">
            {result.rank}
          </span>
          <h3 className="font-bold text-gray-900 text-base leading-tight">
            {result.disease_name_display}
          </h3>
        </div>
        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${color}`}>
          {result.relevance_label}
        </span>
      </div>

      {result.matched_symptoms?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {result.matched_symptoms.map((s) => (
            <span key={s} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
              {s}
            </span>
          ))}
        </div>
      )}

      {result.explanation?.length > 0 && (
        <div>
          <button
            onClick={() => setOpen((v) => !v)}
            className="text-xs text-indigo-600 font-semibold hover:underline cursor-pointer"
          >
            {open ? 'Ocultar explicación' : 'Ver explicación'}
          </button>
          <AnimatePresence>
            {open && (
              <motion.ul
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-2 space-y-1 overflow-hidden"
              >
                {result.explanation.map((line, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                    {line}
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

const EmptyState: React.FC = () => (
  <div className="text-center py-20 bg-white rounded-3xl border border-dashed border-gray-200">
    <Search className="w-8 h-8 text-gray-300 mx-auto mb-4" />
    <h3 className="text-lg font-semibold text-gray-900">No results found</h3>
    <p className="text-gray-500 max-w-xs mx-auto mt-2">
      Try different symptoms or check your connection to the backend.
    </p>
  </div>
);

export const SymptomSearchView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [mode, setMode] = useState<SearchBarMode>('standard');
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const clearAll = () => {
    setResponse(null);
    setError(null);
  };

  const handleClear = () => {
    setSearchTerm('');
    clearAll();
  };

  const handleModeToggle = (m: SearchBarMode) => {
    setMode((prev) => (prev === m ? 'standard' : m));
    clearAll();
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;
    setIsSearching(true);
    setError(null);
    setResponse(null);

    try {
      const data = await runPipeline({
        query: searchTerm.trim(),
        k: 10,
        stages: {
          web_enrichment: mode === 'web',
          positioning: mode === 'positioned',
          generation: false,
        },
      });
      setResponse(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsSearching(false);
    }
  };

  const hybridDiseases: Disease[] = response?.hybrid ?? [];
  const positioned = response?.positioned ?? null;
  const webEnriched = response?.web_enriched;
  const hasResults = response !== null;
  const totalCount =
    mode === 'positioned'
      ? positioned?.length ?? 0
      : hybridDiseases.length;

  return (
    <div className="flex flex-col gap-10">
      <div className="max-w-2xl w-full mx-auto space-y-3">
        <SearchBar
          value={searchTerm}
          onChange={setSearchTerm}
          onSubmit={handleSearch}
          onClear={handleClear}
          isLoading={isSearching}
          placeholder="Enter symptoms (e.g. fever, cough...)"
          showModeToggles
          mode={mode}
          onModeToggle={handleModeToggle}
        />

        {webEnriched?.triggered && (
          <div className="px-4 py-2.5 bg-blue-50 border border-blue-100 rounded-xl flex items-center gap-2 text-xs text-blue-800 font-medium">
            <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
            Búsqueda web activada — {webEnriched.docs_added} documento(s) nuevos indexados desde PubMed / EuropePMC / MedlinePlus
          </div>
        )}
      </div>

      {error && (
        <div className="max-w-2xl mx-auto w-full bg-red-50 border border-red-200 text-red-700 text-sm rounded-2xl px-5 py-4">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {isSearching ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20 gap-4"
          >
            <div className="relative">
              <div className="w-12 h-12 border-4 border-indigo-100 rounded-full" />
              <div className="w-12 h-12 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin absolute inset-0" />
            </div>
            <p className="text-gray-500 font-medium animate-pulse">
              {mode === 'web'
                ? 'Buscando en fuentes web...'
                : mode === 'positioned'
                ? 'Analizando posicionamiento clínico...'
                : 'Processing medical data...'}
            </p>
          </motion.div>
        ) : hasResults ? (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            <div className="flex justify-between items-center px-2">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                Search Results
                <span className="text-sm font-normal text-gray-400 bg-gray-100 px-2.5 py-0.5 rounded-full">
                  {totalCount} found
                </span>
              </h2>
            </div>

            {mode !== 'positioned' && (
              hybridDiseases.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {hybridDiseases.map((d) => (
                    <DiseaseCard key={d.id} disease={d} />
                  ))}
                </div>
              ) : (
                <EmptyState />
              )
            )}

            {mode === 'positioned' && (
              positioned && positioned.length > 0 ? (
                <div className="flex flex-col gap-4">
                  {positioned.map((r) => (
                    <PositionedCard key={r.rank} result={r} />
                  ))}
                </div>
              ) : (
                <EmptyState />
              )
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
};
