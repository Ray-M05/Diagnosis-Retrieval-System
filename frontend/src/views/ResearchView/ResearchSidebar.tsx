import React from 'react';
import { Settings, Activity, Database, FlaskConical } from 'lucide-react';
import type { SearchMode } from './research.types';

interface ResearchSidebarProps {
  searchMode: SearchMode;
  setSearchMode: (mode: SearchMode) => void;
  hybridFusion: string;
  setHybridFusion: (fusion: string) => void;
  hybridCandidates: number;
  setHybridCandidates: (count: number) => void;
  finalResultsCount: number;
  setFinalResultsCount: (count: number) => void;
}

export const ResearchSidebar: React.FC<ResearchSidebarProps> = ({
  searchMode,
  setSearchMode,
  hybridFusion,
  setHybridFusion,
  hybridCandidates,
  setHybridCandidates,
  finalResultsCount,
  setFinalResultsCount,
}) => {
  return (
    <aside className="w-full md:w-80 bg-white border-r border-gray-100 flex flex-col shrink-0 overflow-y-auto">
      <div className="p-6 border-b border-gray-50 flex items-center gap-2.5">
        <div className="p-2 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-100">
          <Settings className="w-5 h-5 text-white" />
        </div>
        <h2 className="text-lg font-extrabold text-gray-900 tracking-tight">Configuración</h2>
      </div>

      <div className="p-6 space-y-8">
        <div className="space-y-4">
          <label className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" /> Modo de búsqueda
          </label>
          <div className="grid grid-cols-1 gap-2">
            <button
              onClick={() => setSearchMode('hybrid')}
              className={`w-full px-4 py-3 rounded-xl text-left transition-all border flex items-center justify-between cursor-pointer ${
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
              className={`w-full px-4 py-3 rounded-xl text-left transition-all border flex items-center justify-between cursor-pointer ${
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

        <div className="space-y-6">
          <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">Parámetros</h3>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-600 flex justify-between">
              <span>Fusión híbrida</span>
              <span className="text-indigo-600 font-bold">
                {hybridFusion === 'weighted_sum' ? 'CC' : 'RRF'}
              </span>
            </label>
            <select
              value={hybridFusion}
              onChange={(e) => setHybridFusion(e.target.value)}
              className="w-full p-2.5 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-100 focus:outline-none cursor-pointer"
            >
              <option value="weighted_sum">Combina Scores (CC)</option>
              <option value="rrf">Reciprocal Rank Fusion (RRF)</option>
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
  );
};
