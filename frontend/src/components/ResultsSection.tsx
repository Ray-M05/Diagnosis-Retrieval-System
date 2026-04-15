import React from 'react';
import { 
  CheckCircle2, AlertCircle, Search, HeartPulse 
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { HybridResult, DiseaseResult } from '../data/diseases';
import { HybridCard, DiagnosticCard } from './DiseaseCard';

interface ResultsSectionProps {
  isSearching: boolean;
  results: {
    hybrid: HybridResult[] | null;
    diagnostic: DiseaseResult[] | null;
  };
  searchMode: 'hybrid' | 'diagnostic';
  searchTerm: string;
}

export const ResultsSection: React.FC<ResultsSectionProps> = ({
  isSearching,
  results,
  searchMode,
  searchTerm,
}) => {
  const currentResultsLength = searchMode === 'hybrid' 
    ? (results.hybrid?.length || 0) 
    : (results.diagnostic?.length || 0);

  return (
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
              <p className="text-gray-900 font-black text-xl tracking-tight">Procesando consulta...</p>
              <p className="text-gray-400 text-sm font-medium animate-pulse text-balance max-w-xs">
                {searchMode === 'hybrid' 
                  ? 'Analizando documentos médicos con Cross-Encoders' 
                  : 'Extrayendo entidades clínicas y agregando evidencia'
                }
              </p>
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
              <HybridCard key={res.chunk_id || res.doc_id} result={res} />
            ))}
            
            {searchMode === 'diagnostic' && results.diagnostic?.map((res) => (
              <DiagnosticCard key={res.disease_name} result={res} />
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
  );
};
