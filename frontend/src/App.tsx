import React, { useState, useMemo } from 'react';
import { 
  Search, Info, X, HeartPulse, Loader2, Settings, Activity, 
  Database, FlaskConical, Filter, ChevronRight, LayoutGrid, 
  Clock, CheckCircle2, AlertCircle, Zap, ShieldCheck
} from 'lucide-react';
import { 
  hybridMockResults, 
  diagnosticMockResults, 
  HybridResult, 
  DiseaseResult 
} from './data/diseases';
import { HybridCard, DiagnosticCard } from './components/DiseaseCard';
import { motion, AnimatePresence } from 'motion/react';

type SearchMode = 'hybrid' | 'diagnostic';

export default function App() {
  // State for search and UI
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<{
    hybrid: HybridResult[] | null;
    diagnostic: DiseaseResult[] | null;
  }>({ hybrid: null, diagnostic: null });
  const [searchTime, setSearchTime] = useState(0);

  // Configuration state (Sidebar)
  const [searchMode, setSearchMode] = useState<SearchMode>('hybrid');
  const [hybridFusion, setHybridFusion] = useState('CC');
  const [hybridCandidates, setHybridCandidates] = useState(20);
  const [finalResultsCount, setFinalResultsCount] = useState(3);
  const [crossEncoderModel, setCrossEncoderModel] = useState('mixedbread-ai/mxbai-rerank-v1');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    const startTime = performance.now();
    
    // Simulate complex data processing
    setTimeout(() => {
      const endTime = performance.now();
      setSearchTime(Math.round(endTime - startTime + 450)); // Add some fake backend delay

      if (searchMode === 'hybrid') {
        setResults({ hybrid: hybridMockResults, diagnostic: null });
      } else {
        setResults({ hybrid: null, diagnostic: diagnosticMockResults });
      }
      setIsSearching(false);
    }, 1200);
  };

  const handleClear = () => {
    setSearchTerm('');
    setResults({ hybrid: null, diagnostic: null });
  };

  const currentResultsLength = useMemo(() => {
    if (searchMode === 'hybrid') return results.hybrid?.length || 0;
    return results.diagnostic?.length || 0;
  }, [searchMode, results]);

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col md:flex-row overflow-hidden">
      
      {/* Sidebar - Configuration */}
      <aside className="w-full md:w-80 bg-white border-r border-gray-100 flex flex-col shrink-0 overflow-y-auto">
        <div className="p-6 border-b border-gray-50 flex items-center gap-2.5">
          <div className="p-2 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-100">
            <Settings className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-lg font-extrabold text-gray-900 tracking-tight">Configuración</h2>
        </div>

        <div className="p-6 space-y-8">
          {/* Modo de Búsqueda */}
          <div className="space-y-4">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
              <Activity className="w-3.5 h-3.5" /> Modo de búsqueda
            </label>
            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={() => setSearchMode('hybrid')}
                className={`w-full px-4 py-3 rounded-xl text-left transition-all border flex items-center justify-between group cursor-pointer ${
                  searchMode === 'hybrid' 
                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-100' 
                    : 'bg-white border-gray-100 text-gray-600 hover:border-indigo-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Database className={`w-4 h-4 ${searchMode === 'hybrid' ? 'text-indigo-200' : 'text-gray-400'}`} />
                  <span className="text-sm font-bold">Híbrido + Reranking</span>
                </div>
                {searchMode === 'hybrid' && <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />}
              </button>
              <button
                onClick={() => setSearchMode('diagnostic')}
                className={`w-full px-4 py-3 rounded-xl text-left transition-all border flex items-center justify-between group cursor-pointer ${
                  searchMode === 'diagnostic' 
                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-100' 
                    : 'bg-white border-gray-100 text-gray-600 hover:border-indigo-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <FlaskConical className={`w-4 h-4 ${searchMode === 'diagnostic' ? 'text-indigo-200' : 'text-gray-400'}`} />
                  <span className="text-sm font-bold">Diagnóstico por Enfermedades</span>
                </div>
                {searchMode === 'diagnostic' && <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />}
              </button>
            </div>
          </div>

          <div className="h-px bg-gray-50 w-full" />

          {/* Parameters */}
          <div className="space-y-6">
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">Parámetros</h3>
            
            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-600 flex justify-between">
                <span>Fusión híbrida</span>
                <span className="text-indigo-600 font-bold">{hybridFusion}</span>
              </label>
              <select 
                value={hybridFusion} 
                onChange={(e) => setHybridFusion(e.target.value)}
                className="w-full p-2.5 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-100 focus:outline-none cursor-pointer"
              >
                <option value="CC">Combina Scores (CC)</option>
                <option value="RRF">Reciprocal Rank Fusion (RRF)</option>
              </select>
            </div>

            <div className="space-y-3">
              <label className="text-xs font-semibold text-gray-600 flex justify-between">
                <span>Candidatos híbridos</span>
                <span className="text-indigo-600 font-bold">{hybridCandidates}</span>
              </label>
              <input 
                type="range" min="10" max="250" step="10"
                value={hybridCandidates}
                onChange={(e) => setHybridCandidates(parseInt(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            <div className="space-y-3">
              <label className="text-xs font-semibold text-gray-600 flex justify-between">
                <span>Resultados finales</span>
                <span className="text-indigo-600 font-bold">{finalResultsCount}</span>
              </label>
              <input 
                type="range" min="1" max="20" step="1"
                value={finalResultsCount}
                onChange={(e) => setFinalResultsCount(parseInt(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 p-4 md:px-8 flex flex-col gap-4 shrink-0 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-0.5">
              <h1 className="text-xl md:text-2xl font-extrabold text-gray-900 tracking-tight leading-none">
                Encuentra información de salud <br className="hidden md:block" />
                <span className="bg-clip-text bg-linear-to-r from-indigo-600 to-blue-500 text-lg md:text-xl">
                  por síntomas.
                </span>
              </h1>
              <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                <Filter className="w-3 h-3 text-indigo-400" /> SRI-DX Support Engine
              </p>
            </div>

            <form onSubmit={handleSearch} className="relative group max-w-lg w-full">
              <div className="relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none transition-transform group-focus-within:scale-105">
                  <Search className="h-4 w-4 text-gray-400 group-focus-within:text-indigo-500" />
                </div>
                <input
                  type="text"
                  className="w-full pl-11 pr-24 py-3 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all text-sm font-medium placeholder:text-gray-400"
                  placeholder="Ingrese síntomas clínicos..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <div className="absolute inset-y-0 right-2 flex items-center gap-1.5">
                  {searchTerm && (
                    <button
                      type="button"
                      onClick={handleClear}
                      className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={isSearching || !searchTerm.trim()}
                    className="px-4 py-1.5 bg-indigo-600 text-white text-[10px] font-bold rounded-xl hover:bg-indigo-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all shadow-md shadow-indigo-100 cursor-pointer"
                  >
                    {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'BUSCAR'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto bg-gray-50/30 p-6 md:p-10 space-y-8 scrollbar-hide">
          
          {/* Status Bar */}
          <div className="bg-white border border-gray-100 rounded-2xl p-4 flex flex-wrap items-center gap-6 shadow-xs">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-blue-50 text-blue-600 rounded-lg">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <p className="text-gray-400 font-bold uppercase tracking-tighter leading-none mb-0.5">Resultados</p>
                <p className="text-gray-900 font-extrabold">{currentResultsLength}</p>
              </div>
            </div>
            <div className="w-px h-8 bg-gray-100 hidden sm:block" />
            <div className="flex-1 min-w-[200px]">
              <div className="bg-amber-50/50 border border-amber-100/50 p-2 rounded-xl flex items-start gap-3">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                <p className="text-[10px] text-amber-900 font-medium leading-tight">
                  <span className="font-bold">Aviso:</span> Herramienta de apoyo diagnóstico. No sustituye la valoración clínica profesional.
                </p>
              </div>
            </div>
          </div>

          {/* Results Grid/List */}
          <AnimatePresence mode='wait'>
            {isSearching ? (
              <motion.div
                key="searching"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center py-32 gap-6"
              >
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-indigo-100 rounded-2xl rotate-45 animate-pulse"></div>
                  <div className="w-16 h-16 border-t-4 border-indigo-600 rounded-2xl rotate-45 animate-spin absolute inset-0"></div>
                </div>
                <div className="text-center space-y-2">
                  <p className="text-gray-900 font-black text-xl tracking-tight">Ejecutando Reranking...</p>
                  <p className="text-gray-400 text-sm font-medium animate-pulse">Analizando documentos médicos con Cross-Encoders</p>
                </div>
              </motion.div>
            ) : currentResultsLength > 0 ? (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col gap-6 w-full"
              >
                {searchMode === 'hybrid' && results.hybrid?.map((res) => (
                  <HybridCard key={res.docId} result={res} />
                ))}
                
                {searchMode === 'diagnostic' && results.diagnostic?.map((res) => (
                  <DiagnosticCard key={res.name} result={res} />
                ))}
              </motion.div>
            ) : searchTerm && !isSearching ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-32 bg-white rounded-3xl border-2 border-dashed border-gray-100 w-full"
              >
                <div className="w-20 h-20 bg-gray-50 rounded-3xl flex items-center justify-center mx-auto mb-6 rotate-12">
                  <Search className="w-10 h-10 text-gray-200" />
                </div>
                <h3 className="text-xl font-black text-gray-900 mb-2">Sin coincidencias clínicas</h3>
                <p className="text-gray-400 font-medium max-w-sm mx-auto">
                  Ajuste los parámetros de búsqueda o intente con síntomas más específicos.
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="welcome"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-24 text-center space-y-6"
              >
                <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 shadow-inner">
                  <HeartPulse className="w-12 h-12" />
                </div>
                <div className="space-y-4">
                  <h2 className="text-3xl font-black text-gray-900 tracking-tight">Bienvenido al motor SRI-DX</h2>
                  <p className="text-gray-400 font-medium max-w-lg mx-auto leading-relaxed">
                    Utilice la barra de búsqueda para iniciar un análisis diferencial basado en síntomas. 
                    Puede configurar el motor híbrido desde el panel lateral.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

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
