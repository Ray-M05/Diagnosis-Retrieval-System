import React, { useState } from 'react';
import { ShieldCheck, Globe } from 'lucide-react';
import { ResearchSidebar } from './ResearchSidebar';
import { ResearchHeader } from './ResearchHeader';
import { ResearchResults } from './ResearchResults';
import { InsufficiencyBanner } from '../../components/InsufficiencyBanner';
import {
  researchSearchHybrid,
  researchSearchDiseases,
  researchSearchPositioned,
  researchWebSearch,
} from './research.api';
import type { HybridResult, DiseaseResult, PositionedResult, WebSearchResult, SearchMode } from './research.types';
import type { SufficiencyInfo } from '../../api/client';
import type { Disease } from '../../types';

// Map DiseaseDTO (from /pipeline) → HybridResult expected by ResearchResults UI
function diseasesToHybridResults(diseases: Disease[]): HybridResult[] {
  return diseases.map((d) => ({
    doc_id: d.id,
    chunk_id: d.id,
    score: 0,
    fusion_method: 'rrf',
    metadata: {
      doc_id: d.id,
      url: d.sourceUrl,
      title: d.name,
      chunk_text_preview: d.description,
    },
  }));
}

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
  const [sufficiency, setSufficiency] = useState<SufficiencyInfo | null>(null);

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
    setSufficiency(null);
    try {
      if (searchMode === 'hybrid') {
        const data = await researchSearchHybrid(searchTerm, finalResultsCount);
        setResults({ hybrid: diseasesToHybridResults(data.hybrid), diagnostic: null, positioned: null, web: null });
        setSufficiency(data.sufficiency);
      } else if ((searchMode as string) === 'positioned') {
        const data = await researchSearchPositioned(searchTerm, finalResultsCount);
        const positioned: PositionedResult[] = data.positioned.map((r) => ({
          rank: r.rank,
          disease_name_display: r.disease_name_display,
          final_score: r.final_score,
          relevance_label: r.relevance_label,
          matched_symptoms: r.matched_symptoms,
          source_domains: [],
          explanation: r.explanation,
          evidences: [],
        }));
        setResults({ hybrid: null, diagnostic: null, positioned, web: null });
        setSufficiency(data.sufficiency);
      } else if ((searchMode as string) === 'web') {
        const data = await researchWebSearch(searchTerm, finalResultsCount);
        // Map DiseaseDTO → WebSearchResult shape
        const webDiseases: WebSearchResult[] = data.hybrid.map((d) => ({
          disease_name: d.name,
          disease_name_display: d.name,
          aggregated_score: 0,
          evidence_count: d.evidence_count,
          rank: d.rank ?? 0,
          evidence: [],
        }));
        setResults({ hybrid: null, diagnostic: null, positioned: null, web: webDiseases });
        setWebEnriched(data.web_enriched?.triggered ?? false);
        setWebDocsAdded(data.web_enriched?.docs_added ?? 0);
      } else {
        const data = await researchSearchDiseases(searchTerm, finalResultsCount);
        setResults({ hybrid: null, diagnostic: data.diseases, positioned: null, web: null });
        setSufficiency(data.sufficiency);
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
    setSufficiency(null);
  };

  // Hybrid configuration sliders are kept for future use (not all are routed yet)
  void hybridFusion;
  void hybridCandidates;

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

        {/* Insufficiency banner */}
        {sufficiency && !sufficiency.sufficient && (searchMode as string) !== 'web' && (
          <div className="mx-6 mt-4">
            <InsufficiencyBanner
              sufficiency={sufficiency}
              onActivateWeb={() => setSearchMode('web' as typeof searchMode)}
            />
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
