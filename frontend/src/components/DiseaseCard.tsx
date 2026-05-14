import React from 'react';
import { Link2 } from 'lucide-react';
import { motion } from 'motion/react';
import type { Disease } from '../types';
import { RelevanceFeedbackButtons } from './feedback/RelevanceFeedbackButtons';

interface DiseaseCardProps {
  disease: Disease;
  query?: string;
  onFeedback?: (args: {
    query: string;
    chunkId: string;
    docId: string;
    relevant: boolean;
  }) => Promise<void>;
}

export const DiseaseCard: React.FC<DiseaseCardProps> = ({ disease, query, onFeedback }) => {
  const canSubmitFeedback = Boolean(
    query && onFeedback && disease.feedback_chunk_id && disease.feedback_doc_id,
  );

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col gap-4"
    >
      <div>
        <div className="flex items-center gap-2 mb-1">
          {disease.rank > 0 && (
            <span className="text-xs font-bold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full">
              #{disease.rank}
            </span>
          )}
          <h3 className="text-xl font-bold text-gray-900 leading-tight">
            {disease.name}
          </h3>
        </div>
        {disease.description && (
          <p className="text-sm text-gray-500 mt-1 leading-relaxed line-clamp-3">
            {disease.description}
          </p>
        )}
      </div>

      {disease.symptoms.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {disease.symptoms.slice(0, 6).map((symptom) => (
            <span
              key={symptom}
              className="px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[13px] font-medium border border-indigo-100/50"
            >
              {symptom}
            </span>
          ))}
        </div>
      )}

      {disease.evidence_count > 0 && (
        <p className="text-xs text-gray-400">
          {disease.evidence_count} supporting evidence chunk{disease.evidence_count !== 1 ? 's' : ''}
        </p>
      )}

      <div className="mt-auto pt-4 border-t border-gray-50 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
        <Link2 className="w-4 h-4 text-gray-400 shrink-0" />
        {disease.sourceUrl ? (
          <a
            href={disease.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-gray-400 hover:text-indigo-600 transition-colors truncate"
          >
            {disease.source || disease.sourceUrl.split('/')[2] || 'Source'}
          </a>
        ) : (
            <span className="text-xs text-gray-300">{disease.source || '-'}</span>
        )}
        </div>

        {canSubmitFeedback && (
          <RelevanceFeedbackButtons
            onSubmit={(relevant) => onFeedback!({
              query: query!,
              chunkId: disease.feedback_chunk_id!,
              docId: disease.feedback_doc_id!,
              relevant,
            })}
          />
        )}
      </div>
    </motion.div>
  );
};
