import React, { useState } from 'react';
import { HybridResult, DiseaseResult, EvidenceChunk } from '../data/diseases';
import { Link2, ChevronDown, ChevronUp, FileText, Activity, ShieldCheck, Target, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

// --- Hybrid Card (Mode 1: Híbrido + Reranking) ---
interface HybridCardProps {
  result: HybridResult;
}

export const HybridCard: React.FC<HybridCardProps> = ({ result }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow group w-full"
    >
      <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-wider text-indigo-500 uppercase px-2 py-0.5 bg-indigo-50 rounded">Document</span>
            <h4 className="text-sm font-semibold text-gray-500 font-mono">{result.docId}</h4>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-100/50">
              <Target className="w-3.5 h-3.5" />
              <span className="text-xs font-bold">Score: {result.score.toFixed(3)}</span>
            </div>
          </div>
        </div>
        <a 
          href={result.sourceUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all"
          title="Go to source"
        >
          <Link2 className="w-5 h-5" />
        </a>
      </div>

      <div className="flex flex-col gap-3 mb-4">
        <div className="p-3 bg-gray-50/80 rounded-xl border border-gray-100/50">
          <p className="text-[10px] text-gray-400 font-bold uppercase mb-1 flex items-center gap-1">
            <Zap className="w-3 h-3 text-amber-500" /> Cross-Encoder
          </p>
          <p className="text-sm font-semibold text-gray-700">{result.crossEncoderScore.toFixed(3)}</p>
        </div>
        <div className="p-3 bg-gray-50/80 rounded-xl border border-gray-100/50">
          <p className="text-[10px] text-gray-400 font-bold uppercase mb-1 flex items-center gap-1">
            <Activity className="w-3 h-3 text-blue-500" /> Semántico
          </p>
          <p className="text-sm font-semibold text-gray-700">{result.semanticScore.toFixed(3)}</p>
        </div>
      </div>

      <div className="relative">
        <div className="absolute -left-2 top-0 bottom-0 w-1 bg-indigo-100/50 rounded-full"></div>
        <p className="text-sm text-gray-600 leading-relaxed italic pl-4">
          "{result.snippet}"
        </p>
      </div>
    </motion.div>
  );
};

// --- Diagnostic Card (Mode 2: Diagnóstico por Enfermedades) ---
interface DiagnosticCardProps {
  result: DiseaseResult;
}

export const DiagnosticCard: React.FC<DiagnosticCardProps> = ({ result }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border border-gray-100 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow w-full"
    >
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full text-left p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 flex items-center justify-center bg-indigo-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-100">
            {result.rank}
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 leading-tight flex items-center gap-2">
              {result.name}
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
            </h3>
            <p className="text-xs text-gray-400 font-medium mt-1">
              Found {result.evidenceChunks.length} evidence chunks
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 self-end md:self-auto">
          <div className="px-3 py-1 bg-amber-50 text-amber-600 rounded-full text-[11px] font-bold border border-amber-100/50 flex items-center gap-1.5">
            <FileText className="w-3 h-3" />
            {result.evidenceChunks.length} Chunks
          </div>
          <div className={`p-1.5 rounded-full transition-transform ${isOpen ? 'rotate-180 bg-indigo-50 text-indigo-600' : 'text-gray-400'}`}>
            <ChevronDown className="w-5 h-5" />
          </div>
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-gray-50"
          >
            <div className="p-6 bg-gray-50/30 space-y-4">
              <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">Fragmentos de evidencia</h4>
              <div className="space-y-3">
                {result.evidenceChunks.map((chunk, idx) => (
                  <EvidenceItem key={chunk.id} chunk={chunk} index={idx + 1} />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const EvidenceItem: React.FC<{ chunk: EvidenceChunk; index: number }> = ({ chunk, index }) => {
  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-xs relative overflow-hidden group">
      <div className="flex justify-between items-start mb-3">
        <span className="text-[10px] font-bold text-indigo-400 font-mono">#{index} ID: {chunk.id}</span>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-indigo-50/50 px-2 py-0.5 rounded border border-indigo-100/50">
            <span className="text-[9px] font-bold text-gray-400 uppercase">rerank</span>
            <span className="text-[11px] font-bold text-indigo-600">{chunk.rerankScore.toFixed(3)}</span>
          </div>
          <div className="flex items-center gap-1 bg-emerald-50/50 px-2 py-0.5 rounded border border-emerald-100/50">
            <span className="text-[9px] font-bold text-gray-400 uppercase">ner</span>
            <span className="text-[11px] font-bold text-emerald-600">{chunk.nerScore.toFixed(3)}</span>
          </div>
        </div>
      </div>
      <p className="text-sm text-gray-600 leading-relaxed font-medium">
        {chunk.snippet}
      </p>
      <div className="absolute bottom-0 right-0 w-8 h-8 opacity-0 group-hover:opacity-10 pointer-events-none transition-opacity">
        <Activity className="w-full h-full text-indigo-600" />
      </div>
    </div>
  );
};
