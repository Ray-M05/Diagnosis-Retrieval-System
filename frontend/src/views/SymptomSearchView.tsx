import React, { useState } from 'react';
import { RefreshCw, Search, Globe } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ResultCard } from '../components/ResultCard';
import { SearchBar } from '../components/SearchBar';
import { InsufficiencyBanner } from '../components/InsufficiencyBanner';
import { runPipeline } from '../api/client';
import { useFeedback } from '../hooks/useFeedback';
import {
  findHybridForPositioned,
  syntheticDiseaseFromPositioned,
} from '../utils/matchPositioned';
import type { Disease } from '../types';
import type { PipelineResponse } from '../api/client';
import type { SearchBarModifier, SearchBarModifiers } from '../components/SearchBar';

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
  // Positioning is always-on in this view. Only `web` is user-toggleable.
  const [modifiers, setModifiers] = useState<SearchBarModifiers>({ web: false, positioned: true });
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refinedQuery, setRefinedQuery] = useState<string | null>(null);
  const feedback = useFeedback();

  const clearAll = () => {
    setResponse(null);
    setError(null);
    setRefinedQuery(null);
    feedback.reset();
  };

  const handleClear = () => {
    setSearchTerm('');
    clearAll();
  };

  const handleModifierToggle = (m: SearchBarModifier) => {
    // Only `web` is exposed to the user here; ignore other modifiers.
    if (m !== 'web') return;
    setModifiers((prev) => ({ ...prev, web: !prev.web }));
    clearAll();
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;
    setIsSearching(true);
    setError(null);
    setResponse(null);
    feedback.reset();

    try {
      const data = await runPipeline({
        query: searchTerm.trim(),
        k: 10,
        stages: {
          web_enrichment: modifiers.web,
          positioning: true,
          generation: false,
        },
      });
      setResponse(data);
      setRefinedQuery(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsSearching(false);
    }
  };

  const handleFeedbackSubmit = async (args: {
    query: string;
    chunkId: string;
    docId: string;
    relevant: boolean;
  }) => {
    try {
      await feedback.submit(args);
    } catch (err) {
      setError(String(err));
    }
  };

  const handleFeedbackRetract = async (args: {
    query: string;
    chunkId: string;
    docId: string;
  }) => {
    try {
      await feedback.retract(args);
    } catch (err) {
      setError(String(err));
    }
  };

  const handleRefine = async () => {
    if (!searchTerm.trim()) return;
    setError(null);
    try {
      const currentQuery = response?.query ?? searchTerm.trim();
      const refined = await feedback.refine(currentQuery, 10);
      setResponse(refined.results);
      setRefinedQuery(refined.refined_query);
      feedback.reset();
    } catch (err) {
      setError(String(err));
    }
  };

  const hybridDiseases: Disease[] = response?.hybrid ?? [];
  const positioned = response?.positioned ?? null;
  const webEnriched = response?.web_enriched;
  const hasResults = response !== null;

  // Build the unified result list: prefer positioned (always on) and enrich
  // each entry with its hybrid counterpart for description / source / feedback.
  const unifiedItems =
    positioned && positioned.length > 0
      ? positioned.map((p) => {
          const match = findHybridForPositioned(p, hybridDiseases);
          return {
            positioned: p,
            disease: match ?? syntheticDiseaseFromPositioned(p),
          };
        })
      : hybridDiseases.map((d) => ({ positioned: null, disease: d }));

  const totalCount = unifiedItems.length;

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
          showPositioningToggle={false}
          modifiers={modifiers}
          onModifierToggle={handleModifierToggle}
        />

        {webEnriched?.triggered && (
          <div className="px-4 py-2.5 bg-blue-50 border border-blue-100 rounded-xl flex items-center gap-2 text-xs text-blue-800 font-medium">
            <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
            Web search enabled — {webEnriched.api_retrieved} document(s) retrieved, {webEnriched.docs_added} new indexed from PubMed / EuropePMC / MedlinePlus
          </div>
        )}

        {response?.sufficiency && !response.sufficiency.sufficient && !modifiers.web && (
          <InsufficiencyBanner
            sufficiency={response.sufficiency}
            onActivateWeb={() => handleModifierToggle('web')}
          />
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
              {modifiers.web
                ? 'Searching web + analyzing positioning...'
                : 'Analyzing clinical positioning...'}
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
              {feedback.hasFeedback && (
                <button
                  type="button"
                  onClick={handleRefine}
                  disabled={feedback.isRefining}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600 shadow-sm transition-colors hover:border-indigo-200 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${feedback.isRefining ? 'animate-spin' : ''}`} />
                  Refine
                </button>
              )}
            </div>

            {refinedQuery && refinedQuery !== searchTerm.trim() && (
              <div className="mx-2 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-2 text-xs text-indigo-700">
                Refined query: {refinedQuery}
              </div>
            )}

            {unifiedItems.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {unifiedItems.map((item, idx) => {
                  const resultKey = [
                    response?.query ?? searchTerm,
                    item.disease.id,
                    item.disease.feedback_doc_id,
                    item.disease.feedback_chunk_id,
                    item.disease.name,
                    idx,
                  ].join('|');
                  return (
                    <ResultCard
                      key={resultKey}
                      variant={item.positioned ? 'positioned' : 'hybrid'}
                      disease={item.disease}
                      positioned={item.positioned}
                      query={response?.query ?? searchTerm}
                      onFeedback={handleFeedbackSubmit}
                      onRetractFeedback={handleFeedbackRetract}
                    />
                  );
                })}
              </div>
            ) : (
              <EmptyState />
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
};
