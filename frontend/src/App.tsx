import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ResultsSection } from './components/ResultsSection';
import { apiService } from './services/api';
import { HybridResult, DiseaseResult } from './data/diseases';

type SearchMode = 'hybrid' | 'diagnostic';

export default function App() {
  // State for search and UI
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<{
    hybrid: HybridResult[] | null;
    diagnostic: DiseaseResult[] | null;
  }>({ hybrid: null, diagnostic: null });

  // Configuration state (Sidebar)
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid');
  const [hybridFusion, setHybridFusion] = useState('rrf');
  const [hybridCandidates, setHybridCandidates] = useState(100);
  const [finalResultsCount, setFinalResultsCount] = useState(10);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    
    try {
      if (searchMode === 'hybrid') {
        const data = await apiService.searchHybrid({
          query: searchTerm,
          k: finalResultsCount,
          fusion_method: hybridFusion,
          use_reranking: true, // Habilitar reranking por defecto en modo híbrido
          hybrid_candidates: hybridCandidates,
        });
        setResults({ hybrid: data, diagnostic: null });
      } else {
        const data = await apiService.searchDiseases({
          query: searchTerm,
          max_diseases: finalResultsCount,
          hybrid_candidates: hybridCandidates,
          min_ner_score: 0.5,
        });
        setResults({ hybrid: null, diagnostic: data });
      }
    } catch (error) {
      console.error('Search failed:', error);
      // Aqui se podría añadir una notificación de error
    } finally {
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setSearchTerm('');
    setResults({ hybrid: null, diagnostic: null });
  };

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col md:flex-row overflow-hidden">
      
      <Sidebar 
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
        <Header 
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          handleSearch={handleSearch}
          handleClear={handleClear}
          isSearching={isSearching}
        />

        <ResultsSection 
          isSearching={isSearching}
          results={results}
          searchMode={searchMode}
          searchTerm={searchTerm}
        />

        {/* Footer Disclaimer */}
        <footer className="bg-white border-t border-gray-100 px-6 py-4 flex flex-col md:flex-row justify-end items-center gap-4 shrink-0">
          <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            SOPORTADO POR BIBLIOGRAFÍA CIENTÍFICA
          </div>
        </footer>
      </div>
    </div>
  );
}
