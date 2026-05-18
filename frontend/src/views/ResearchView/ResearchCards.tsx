import React, { useState } from 'react';
import { Link2, ChevronDown, Activity, ShieldCheck, Target, Zap, MapPin, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import type { HybridResult, DiseaseResult, DiseaseEvidence, PositionedResult } from './research.types';
import { RelevanceFeedbackButtons } from '../../components/feedback/RelevanceFeedbackButtons';

export interface CardFeedbackHandlers {
  query: string;
  onFeedback: (args: {
    query: string;
    chunkId: string;
    docId: string;
    relevant: boolean;
  }) => Promise<void>;
  onRetractFeedback?: (args: {
    query: string;
    chunkId: string;
    docId: string;
  }) => Promise<void>;
}

function feedbackButtonsFor(
  handlers: CardFeedbackHandlers | undefined,
  chunkId: string | undefined | null,
  docId: string | undefined | null,
  targetSuffix: string,
) {
  if (!handlers || !chunkId || !docId) return null;
  const targetId = [handlers.query, docId, chunkId, targetSuffix].join('|');
  return (
    <RelevanceFeedbackButtons
      targetId={targetId}
      onSubmit={(relevant) => handlers.onFeedback({
        query: handlers.query,
        chunkId,
        docId,
        relevant,
      })}
      onRetract={
        handlers.onRetractFeedback
          ? () => handlers.onRetractFeedback!({
              query: handlers.query,
              chunkId,
              docId,
            })
          : undefined
      }
    />
  );
}

export const HybridCard: React.FC<{ result: HybridResult; feedback?: CardFeedbackHandlers }> = ({
  result,
  feedback,
}) => {
  const title =
    result.title ||
    result.section_heading ||
    result.metadata?.title ||
    result.metadata?.section_heading ||
    'No title';
  const url = result.url || result.metadata?.url || '#';
  const snippet =
    result.chunk_text_preview ||
    result.metadata?.chunk_text_preview ||
    result.metadata?.chunk_text ||
    'No content available';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow w-full"
    >
      <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-4">
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-bold tracking-wider text-indigo-500 uppercase px-2 py-0.5 bg-indigo-50 rounded shrink-0">
              {result.fusion_method === 'cross-encoder' ? 'Reranked' : 'Hybrid'}
            </span>
            <h4 className="text-sm font-semibold text-gray-900 truncate">{title}</h4>
            <span className="text-[10px] font-mono text-gray-400 shrink-0">
              ID: {result.chunk_id || result.doc_id}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-100/50">
              <Target className="w-3.5 h-3.5" />
              <span className="text-xs font-bold">Score: {result.score.toFixed(4)}</span>
            </div>
          </div>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all shrink-0"
        >
          <Link2 className="w-5 h-5" />
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {result.rerank_score !== undefined && (
          <div className="p-3 bg-gray-50/80 rounded-xl border border-gray-100/50">
            <p className="text-[10px] text-gray-400 font-bold uppercase mb-1 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-500" /> Cross-Encoder
            </p>
            <p className="text-sm font-bold text-gray-700">{result.rerank_score.toFixed(4)}</p>
          </div>
        )}
        {result.vector_score !== undefined && (
          <div className="p-3 bg-gray-50/80 rounded-xl border border-gray-100/50">
            <p className="text-[10px] text-gray-400 font-bold uppercase mb-1 flex items-center gap-1">
              <Activity className="w-3 h-3 text-blue-500" /> Semantic
            </p>
            <p className="text-sm font-bold text-gray-700">{result.vector_score.toFixed(4)}</p>
          </div>
        )}
      </div>

      <div className="relative">
        <div className="absolute -left-2 top-0 bottom-0 w-1 bg-indigo-100/50 rounded-full" />
        <p className="text-sm text-gray-600 leading-relaxed italic pl-4">"{snippet}"</p>
      </div>

      {feedback && (result.chunk_id || result.doc_id) && (
        <div className="mt-4 pt-3 border-t border-gray-50 flex justify-end">
          {feedbackButtonsFor(feedback, result.chunk_id || result.doc_id, result.doc_id || result.chunk_id, 'hybrid')}
        </div>
      )}
    </motion.div>
  );
};

export const DiagnosticCard: React.FC<{ result: DiseaseResult; feedback?: CardFeedbackHandlers }> = ({
  result,
  feedback,
}) => {
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
          <div className="w-10 h-10 flex items-center justify-center bg-indigo-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-100 shrink-0">
            {result.rank || '-'}
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 leading-tight flex items-center gap-2">
              {result.disease_name_display}
              <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
            </h3>
            <p className="text-xs text-gray-400 font-medium mt-1">
              {result.evidence_count} evidence fragments detected
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 self-end md:self-auto">
          <div className="px-3 py-1 bg-amber-50 text-amber-600 rounded-full text-[11px] font-bold border border-amber-100/50 flex items-center gap-1.5 shadow-sm">
            <Target className="w-3 h-3" />
            Score: {result.aggregated_score.toFixed(2)}
          </div>
          <div
            className={`p-1.5 rounded-full transition-transform ${isOpen ? 'rotate-180 bg-indigo-50 text-indigo-600' : 'text-gray-400'}`}
          >
            <ChevronDown className="w-5 h-5" />
          </div>
        </div>
      </button>

      {feedback && result.evidence[0]?.chunk_id && result.evidence[0]?.doc_id && (
        <div
          className="px-6 pb-3 pt-0 flex justify-end"
          onClick={(e) => e.stopPropagation()}
        >
          {feedbackButtonsFor(
            feedback,
            result.evidence[0].chunk_id,
            result.evidence[0].doc_id,
            `diagnostic|${result.disease_name}`,
          )}
        </div>
      )}

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-gray-50"
          >
            <div className="p-6 bg-gray-50/30 space-y-4">
              <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
                Clinical evidence
              </h4>
              <div className="space-y-3">
                {result.evidence.map((ev, idx) => (
                  <EvidenceItem key={ev.chunk_id} evidence={ev} index={idx + 1} />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const EvidenceItem: React.FC<{ evidence: DiseaseEvidence; index: number }> = ({ evidence, index }) => (
  <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-xs">
    <div className="flex justify-between items-start mb-3">
      <div className="flex flex-col min-w-0">
        <span className="text-[10px] font-bold text-indigo-400 font-mono truncate">
          #{index} CHUNK: {evidence.chunk_id}
        </span>
        <a
          href={evidence.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[9px] text-gray-400 hover:text-indigo-500 flex items-center gap-1"
        >
          <Link2 className="w-2.5 h-2.5" /> View source
        </a>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center gap-1 bg-indigo-50/50 px-2 py-0.5 rounded border border-indigo-100/50">
          <span className="text-[9px] font-bold text-gray-400 uppercase">rerank</span>
          <span className="text-[11px] font-bold text-indigo-600">{evidence.rerank_score.toFixed(3)}</span>
        </div>
        <div className="flex items-center gap-1 bg-emerald-50/50 px-2 py-0.5 rounded border border-emerald-100/50">
          <span className="text-[9px] font-bold text-gray-400 uppercase">ner</span>
          <span className="text-[11px] font-bold text-emerald-600">{evidence.ner_score.toFixed(3)}</span>
        </div>
      </div>
    </div>
    <p className="text-sm text-gray-600 leading-relaxed font-medium">"{evidence.content_preview}"</p>
  </div>
);

// --- Positioned Card (Mode 3: Clinical Positioning) ---
export const PositionedCard: React.FC<{
  result: PositionedResult;
  feedback?: CardFeedbackHandlers;
}> = ({ result, feedback }) => {
  const [isOpen, setIsOpen] = useState(false);
  const topEvidence = result.evidences[0];

  const labelColor =
    result.relevance_label === 'high'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
      : result.relevance_label === 'medium'
      ? 'bg-amber-50 text-amber-700 border-amber-100'
      : 'bg-gray-50 text-gray-500 border-gray-100';

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
          <div className="w-10 h-10 flex items-center justify-center bg-indigo-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-100 shrink-0">
            {result.rank}
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 leading-tight flex items-center gap-2">
              <MapPin className="w-4 h-4 text-indigo-400 shrink-0" />
              {result.disease_name_display}
            </h3>
            {result.matched_symptoms.length > 0 && (
              <p className="text-xs text-gray-400 mt-0.5">
                Symptoms: {result.matched_symptoms.join(', ')}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 self-end md:self-auto">
          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${labelColor}`}>
            {result.relevance_label.toUpperCase()}
          </span>
          <div className="flex items-center gap-1 px-2.5 py-1 bg-indigo-50 text-indigo-600 rounded-lg border border-indigo-100/50">
            <Target className="w-3 h-3" />
            <span className="text-xs font-bold">{result.final_score.toFixed(4)}</span>
          </div>
          <div className={`p-1.5 rounded-full transition-transform ${isOpen ? 'rotate-180 text-indigo-600' : 'text-gray-400'}`}>
            <ChevronDown className="w-4 h-4" />
          </div>
        </div>
      </button>

      {feedback && topEvidence?.chunk_id && topEvidence?.doc_id && (
        <div
          className="px-6 pb-3 pt-0 flex justify-end"
          onClick={(e) => e.stopPropagation()}
        >
          {feedbackButtonsFor(
            feedback,
            topEvidence.chunk_id,
            topEvidence.doc_id,
            `positioned|${result.disease_name_display}`,
          )}
        </div>
      )}

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-gray-50"
          >
            <div className="p-6 bg-gray-50/30 space-y-4">
              {result.explanation.length > 0 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Explanation</p>
                  {result.explanation.map((line, i) => (
                    <p key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                      <AlertCircle className="w-3 h-3 text-indigo-400 mt-0.5 shrink-0" /> {line}
                    </p>
                  ))}
                </div>
              )}
              {result.evidences.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Evidence</p>
                  {result.evidences.slice(0, 3).map((ev) => (
                    <div key={ev.chunk_id} className="bg-white rounded-xl border border-gray-100 p-3 text-xs space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="font-mono text-indigo-400">{ev.chunk_id}</span>
                        {ev.cross_encoder_score !== undefined && (
                          <span className="text-gray-400">CE: {ev.cross_encoder_score.toFixed(3)}</span>
                        )}
                      </div>
                      {ev.content_preview && (
                        <p className="text-gray-600 italic">"{ev.content_preview.slice(0, 200)}"</p>
                      )}
                      {ev.url && (
                        <a href={ev.url} target="_blank" rel="noopener noreferrer"
                          className="text-indigo-400 hover:text-indigo-600 flex items-center gap-1">
                          <Link2 className="w-3 h-3" /> {ev.url.slice(0, 60)}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
