import React, { useState } from 'react';
import { ShieldCheck, Globe } from 'lucide-react';
import { ResearchSidebar } from './ResearchSidebar';
import { ResearchHeader } from './ResearchHeader';
import { ResearchResults } from './ResearchResults';
import {
  researchSearchHybrid,
  researchSearchDiseases,
  researchSearchPositioned,
  researchWebSearch,
} from './research.api';
import type { HybridResult, DiseaseResult, PositionedResult, WebSearchResult, SearchMode } from './research.types';

export const ResearchView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<{
    hybrid: HybridResult[] | null;
    diagnostic: DiseaseResult[] | null;
    positioned: PositionedResult[] | null;
    web: WebSearchResult[] | null;
  }>({ hybrid: null, diagnostic: null, positioned: null, web: null });

  const [webEnriched, setWebEnriched] = useState(false);
  const [webDocsAdded, setWebDocsAdded] = useState(0);

  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid');
  const [hybridFusion, setHybridFusion] = useState('weighted_sum');
  const [hybridCandidates, setHybridCandidates] = useState(20);
  const [finalResultsCount, setFinalResultsCount] = useState(3);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    setWebEnriched(false);
    setWebDocsAdded(0);
    try {
      if (searchMode === 'hybrid') {
        const data = await researchSearchHybrid({
          query: searchTerm,
          k: finalResultsCount,
          fusion_method: hybridFusion,
          use_reranking: true,
          hybrid_candidates: hybridCandidates,
        });
        setResults({ hybrid: data, diagnostic: null, positioned: null, web: null });
      } else if ((searchMode as string) === 'positioned') {
        const data = await researchSearchPositioned({
          query: searchTerm,
          k: finalResultsCount,
          hybrid_candidates: hybridCandidates,
          final_results: finalResultsCount,
          min_ner_score: 0.5,
        });
        setResults({ hybrid: null, diagnostic: null, positioned: data, web: null });
      } else if ((searchMode as string) === 'web') {
        const data = await researchWebSearch({
          query: searchTerm,
          k: finalResultsCount,
          hybrid_candidates: hybridCandidates,
          final_results: finalResultsCount,
          min_ner_score: 0.5,
        });
        setResults({ hybrid: null, diagnostic: null, positioned: null, web: data.diseases });
        setWebEnriched(data.web_enriched);
        setWebDocsAdded(data.docs_added);
      } else {
        const data = await researchSearchDiseases({
          query: searchTerm,
          max_diseases: finalResultsCount,
          hybrid_candidates: hybridCandidates,
          min_ner_score: 0.5,
        });
        setResults({ hybrid: null, diagnostic: data, positioned: null, web: null });
      }
    } catch (err) {
      console.error('Research search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setSearchTerm('');
    setResults({ hybrid: null, diagnostic: null, positioned: null, web: null });
    setWebEnriched(false);
    setWebDocsAdded(0);
  };

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col md:flex-row overflow-hidden">
      <ResearchSidebar
        searchMode={searchMode}
        setSearchMode={setSearchMode}
        hybridFusion={hybridFusion}
        setHybridFusion={setHybridFusion}
        hybridCandidates={hybridCandidates}
        setHybridCandidates={setHybridCandidates}
        finalResultsCount={finalResultsCount}
        setFinalResultsCount={setFinalResultsCount}
      />

      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <ResearchHeader
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          handleSearch={handleSearch}
          handleClear={handleClear}
          isSearching={isSearching}
        />

        {/* Web enrichment indicator */}
        {(searchMode as string) === 'web' && webEnriched && (
          <div className="mx-6 mt-4 px-4 py-2.5 bg-blue-50 border border-blue-100 rounded-xl flex items-center gap-2.5 text-xs text-blue-800 font-medium">
            <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
            Búsqueda web activada — {webDocsAdded} documento{webDocsAdded !== 1 ? 's' : ''} nuevos indexados desde PubMed / EuropePMC / MedlinePlus
          </div>
        )}

        <ResearchResults
          isSearching={isSearching}
          results={results}
          searchMode={searchMode}
          searchTerm={searchTerm}
        />

        <footer className="bg-white border-t border-gray-100 px-6 py-4 flex justify-end items-center shrink-0">
          <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            SOPORTADO POR BIBLIOGRAFÍA CIENTÍFICA
          </div>
        </footer>
      </div>
    </div>
  );
};
