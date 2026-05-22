import React, { useState } from 'react';
import { RefreshCw, ShieldCheck, Globe, Search as SearchIcon, BarChart3 } from 'lucide-react';
import { ResearchSidebar } from './ResearchSidebar';
import { ResearchHeader } from './ResearchHeader';
import { ResearchResults } from './ResearchResults';
import { EvaluationPanel } from './EvaluationPanel';
import { InsufficiencyBanner } from '../../components/InsufficiencyBanner';
import {
  researchSearchHybrid,
  researchSearchDiseases,
  researchSearchPositioned,
  researchWebSearch,
} from './research.api';
import type { HybridResult, DiseaseResult, PositionedResult, WebSearchResult, SearchMode } from './research.types';
import type { HybridChunk, SufficiencyInfo } from '../../api/client';
import { useFeedback } from '../../hooks/useFeedback';

type SubTab = 'results' | 'evaluation';

// Map backend HybridChunk → HybridResult expected by ResearchResults UI
function chunksToHybridResults(chunks: HybridChunk[]): HybridResult[] {
  return chunks.map((c) => ({
    doc_id: c.doc_id,
    chunk_id: c.chunk_id,
    score: c.score,
    rerank_score: c.rerank_score,
    vector_score: c.vector_score ?? undefined,
    lexical_score: c.lexical_score ?? undefined,
    fusion_method: c.fusion_method,
    title: c.title ?? null,
    section_heading: c.section_heading ?? null,
    url: c.url ?? null,
    source_domain: c.source_domain ?? null,
    chunk_text_preview: c.chunk_text_preview,
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
  const [webDocsRetrieved, setWebDocsRetrieved] = useState(0);
  const [sufficiency, setSufficiency] = useState<SufficiencyInfo | null>(null);

  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid');
  const [subTab, setSubTab] = useState<SubTab>('results');
  const [hybridCandidates, setHybridCandidates] = useState(20);
  const [finalResultsCount, setFinalResultsCount] = useState(3);
  const [refinedQuery, setRefinedQuery] = useState<string | null>(null);
  const feedback = useFeedback();

  const handleFeedbackSubmit = async (args: {
    query: string;
    chunkId: string;
    docId: string;
    relevant: boolean;
  }) => {
    try {
      await feedback.submit(args);
    } catch (err) {
      console.error('Feedback submit failed:', err);
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
      console.error('Feedback retract failed:', err);
    }
  };

  const handleRefine = async () => {
    if (!searchTerm.trim()) return;
    try {
      const currentQuery = searchTerm.trim();
      const refined = await feedback.refine(currentQuery, finalResultsCount);
      // Refine always returns NER-aggregated diseases via the diseases_to_response
      // helper in the backend. Map them into the diagnostic card shape.
      const diseases: DiseaseResult[] = (refined.results?.hybrid ?? []).map((d: any, idx: number) => {
        const chunkId = d.feedback_chunk_id ?? '';
        const docId = d.feedback_doc_id ?? '';
        return {
          disease_name: d.name,
          disease_name_display: d.doc_title ?? d.name,
          aggregated_score: d.score ?? 0,
          evidence_count: d.evidence_count,
          rank: d.rank ?? idx + 1,
          evidence: chunkId && docId
            ? [{
                chunk_id: chunkId,
                doc_id: docId,
                rerank_score: 0,
                ner_score: 0,
                combined_score: d.score ?? 0,
                content_preview: d.description ?? '',
                url: d.sourceUrl ?? '',
              }]
            : [],
        };
      });
      setResults({ hybrid: null, diagnostic: diseases, positioned: null, web: null });
      setSearchMode('diagnostic');
      setRefinedQuery(refined.refined_query);
      feedback.reset();
    } catch (err) {
      console.error('Refine failed:', err);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    if ((searchMode as string) === 'rag') {
      // RAG mode is only meaningful via the evaluation pipeline; there is
      // no equivalent per-query browsing UI here yet.
      setSubTab('evaluation');
      return;
    }

    setIsSearching(true);
    setWebEnriched(false);
    setWebDocsAdded(0);
    setWebDocsRetrieved(0);
    setSufficiency(null);
    setRefinedQuery(null);
    feedback.reset();
    try {
      if (searchMode === 'hybrid') {
        const data = await researchSearchHybrid(searchTerm, finalResultsCount);
        setResults({ hybrid: chunksToHybridResults(data.chunks), diagnostic: null, positioned: null, web: null });
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
          evidences: r.evidences ?? [],
        }));
        setResults({ hybrid: null, diagnostic: null, positioned, web: null });
        setSufficiency(data.sufficiency);
      } else if ((searchMode as string) === 'web') {
        const data = await researchWebSearch(searchTerm, finalResultsCount);
        // Map DiseaseDTO → WebSearchResult shape (preserving score + doc title)
        const webDiseases: WebSearchResult[] = data.hybrid.map((d, idx) => {
          const chunkId = d.feedback_chunk_id ?? '';
          const docId = d.feedback_doc_id ?? '';
          return {
            disease_name: d.name,
            disease_name_display: d.doc_title ?? d.name,
            aggregated_score: d.score ?? 0,
            evidence_count: d.evidence_count,
            rank: d.rank ?? idx + 1,
            evidence: chunkId && docId
              ? [{
                  chunk_id: chunkId,
                  doc_id: docId,
                  rerank_score: 0,
                  ner_score: 0,
                  combined_score: d.score ?? 0,
                  content_preview: d.description ?? '',
                  url: d.sourceUrl ?? '',
                }]
              : [],
            feedback_chunk_id: chunkId || null,
            feedback_doc_id: docId || null,
          };
        });
        setResults({ hybrid: null, diagnostic: null, positioned: null, web: webDiseases });
        setWebEnriched(data.web_enriched?.triggered ?? false);
        setWebDocsAdded(data.web_enriched?.docs_added ?? 0);
        setWebDocsRetrieved(data.web_enriched?.api_retrieved ?? 0);
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
    setWebDocsRetrieved(0);
    setSufficiency(null);
    setRefinedQuery(null);
    feedback.reset();
  };

  // Hybrid configuration sliders are kept for future use (not all are routed yet)
  void hybridCandidates;

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col md:flex-row overflow-hidden">
      <ResearchSidebar
        searchMode={searchMode}
        setSearchMode={setSearchMode}
        hybridCandidates={hybridCandidates}
        setHybridCandidates={setHybridCandidates}
        finalResultsCount={finalResultsCount}
        setFinalResultsCount={setFinalResultsCount}
      />

      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Sub-tab toggle — Results vs Evaluation */}
        <div className="px-6 pt-4 pb-2 bg-white border-b border-gray-50 shrink-0">
          <div className="inline-flex bg-gray-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setSubTab('results')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5 ${
                subTab === 'results'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <SearchIcon className="w-3.5 h-3.5" />
              Results
            </button>
            <button
              type="button"
              onClick={() => setSubTab('evaluation')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5 ${
                subTab === 'evaluation'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Evaluation
            </button>
          </div>
        </div>

        {subTab === 'evaluation' ? (
          <EvaluationPanel mode={searchMode} />
        ) : (
        <>
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
            Web search enabled — {webDocsRetrieved} document{webDocsRetrieved !== 1 ? 's' : ''} retrieved, {webDocsAdded} new indexed from PubMed / EuropePMC / MedlinePlus
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

        {/* Refine button + refined query banner */}
        {feedback.hasFeedback && (
          <div className="mx-6 mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleRefine}
              disabled={feedback.isRefining}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600 shadow-sm transition-colors hover:border-indigo-200 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${feedback.isRefining ? 'animate-spin' : ''}`} />
              Refine with feedback
            </button>
          </div>
        )}
        {refinedQuery && refinedQuery !== searchTerm.trim() && (
          <div className="mx-6 mt-2 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-2 text-xs text-indigo-700">
            Refined query: {refinedQuery}
          </div>
        )}

        <ResearchResults
          isSearching={isSearching}
          results={results}
          searchMode={searchMode}
          searchTerm={searchTerm}
          feedback={{
            query: searchTerm.trim(),
            onFeedback: handleFeedbackSubmit,
            onRetractFeedback: handleFeedbackRetract,
          }}
        />
        </>
        )}

        <footer className="bg-white border-t border-gray-100 px-6 py-4 flex justify-end items-center shrink-0">
          <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            SUPPORTED BY SCIENTIFIC BIBLIOGRAPHY
          </div>
        </footer>
      </div>
    </div>
  );
};
