import React from 'react';
import { Link2, Target, FileText, Globe } from 'lucide-react';
import { motion } from 'motion/react';
import type { Disease } from '../types';
import type { PositionedResult } from '../api/client';
import { RelevanceFeedbackButtons } from './feedback/RelevanceFeedbackButtons';

export type ResultVariant = 'hybrid' | 'positioned' | 'web';

const relevanceColor: Record<string, string> = {
  high: 'bg-green-100 text-green-700 border-green-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-gray-100 text-gray-500 border-gray-200',
};

interface ResultCardProps {
  variant: ResultVariant;
  disease: Disease;
  positioned?: PositionedResult | null;
  query?: string;
  onFeedback?: (args: {
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

export const ResultCard: React.FC<ResultCardProps> = ({
  variant,
  disease,
  positioned = null,
  query,
  onFeedback,
  onRetractFeedback,
}) => {
  const rank = positioned?.rank ?? disease.rank;
  const title =
    variant === 'web'
      ? disease.doc_title || disease.name || 'Untitled document'
      : positioned?.disease_name_display || disease.name;

  const score =
    variant === 'positioned'
      ? positioned?.final_score ?? disease.score
      : disease.score;

  const symptoms =
    positioned?.matched_symptoms && positioned.matched_symptoms.length > 0
      ? positioned.matched_symptoms
      : disease.symptoms;

  const relevanceLabel = positioned?.relevance_label;
  const relevanceClass =
    relevanceLabel && relevanceColor[relevanceLabel.toLowerCase()]
      ? relevanceColor[relevanceLabel.toLowerCase()]
      : 'bg-gray-100 text-gray-500 border-gray-200';

  const sourceDomains = positioned?.source_domains ?? [];
  const source =
    disease.source || (disease.sourceUrl ? disease.sourceUrl.split('/')[2] ?? '' : '');
  const navigableUrl =
    disease.sourceUrl ||
    (source ? (source.startsWith('http') ? source : `https://${source}`) : '');

  const canSubmitFeedback = Boolean(
    query && onFeedback && disease.feedback_chunk_id && disease.feedback_doc_id,
  );
  const feedbackTargetId = [
    query,
    disease.feedback_doc_id,
    disease.feedback_chunk_id,
    disease.name,
  ].join('|');

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col gap-4"
    >
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          {rank > 0 && (
            <span className="text-xs font-bold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full">
              #{rank}
            </span>
          )}
          <h3 className="text-xl font-bold text-gray-900 leading-tight flex items-center gap-1.5 flex-1 min-w-0">
            {variant === 'web' && (
              <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
            )}
            <span className="truncate">{title}</span>
          </h3>

          {/* Score (always when present) */}
          {typeof score === 'number' && score > 0 && (
            <span className="ml-auto shrink-0 inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full text-[11px] font-bold border border-amber-100/50">
              <Target className="w-3 h-3" />
              {score.toFixed(score < 1 ? 3 : 2)}
            </span>
          )}

          {/* Relevance badge only in positioned mode */}
          {variant === 'positioned' && relevanceLabel && (
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full shrink-0 border ${relevanceClass}`}
            >
              {relevanceLabel}
            </span>
          )}
        </div>

        {/* Doc title (when distinct from the disease name) */}
        {variant !== 'web' &&
          disease.doc_title &&
          disease.doc_title.toLowerCase() !== (title ?? '').toLowerCase() && (
            <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
              <FileText className="w-3 h-3 text-gray-400" />
              <span className="truncate">{disease.doc_title}</span>
            </p>
          )}

        {/* Source for web cards */}
        {variant === 'web' && source && (
          <p className="mt-0.5 text-[11px] text-gray-400 flex items-center gap-1">
            <Globe className="w-3 h-3" />
            {source}
          </p>
        )}

        {/* Description / snippet */}
        {disease.description &&
          (variant === 'web' ? (
            <p className="text-sm text-gray-600 leading-relaxed italic line-clamp-4 mt-2">
              “{disease.description}”
            </p>
          ) : (
            <p className="text-sm text-gray-500 mt-2 leading-relaxed line-clamp-3">
              {disease.description}
            </p>
          ))}
      </div>

      {/* Symptoms (matched_symptoms when positioned, otherwise disease.symptoms) */}
      {symptoms.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {symptoms.slice(0, 6).map((symptom) => (
            <span
              key={symptom}
              className="px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[13px] font-medium border border-indigo-100/50"
            >
              {symptom}
            </span>
          ))}
        </div>
      )}

      {/* Evidence count */}
      {disease.evidence_count > 0 && (
        <p className="text-xs text-gray-400">
          {disease.evidence_count} supporting evidence chunk
          {disease.evidence_count !== 1 ? 's' : ''}
        </p>
      )}

      {/* Source domains (positioned) */}
      {variant === 'positioned' && sourceDomains.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {sourceDomains.map((d) => (
            <span
              key={d}
              className="text-[10px] font-medium text-gray-500 bg-gray-50 border border-gray-100 px-2 py-0.5 rounded-full inline-flex items-center gap-1"
            >
              <Globe className="w-2.5 h-2.5" /> {d}
            </span>
          ))}
        </div>
      )}

      {/* Footer: source + feedback */}
      <div className="mt-auto pt-4 border-t border-gray-50 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Link2 className="w-4 h-4 text-gray-400 shrink-0" />
          {navigableUrl ? (
            <a
              href={navigableUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-gray-400 hover:text-indigo-600 transition-colors truncate"
            >
              {source || navigableUrl}
            </a>
          ) : (
            <span className="text-xs text-gray-300">-</span>
          )}
        </div>

        {canSubmitFeedback && (
          <RelevanceFeedbackButtons
            targetId={feedbackTargetId}
            onSubmit={(relevant) =>
              onFeedback!({
                query: query!,
                chunkId: disease.feedback_chunk_id!,
                docId: disease.feedback_doc_id!,
                relevant,
              })
            }
            onRetract={
              onRetractFeedback
                ? () =>
                    onRetractFeedback({
                      query: query!,
                      chunkId: disease.feedback_chunk_id!,
                      docId: disease.feedback_doc_id!,
                    })
                : undefined
            }
          />
        )}
      </div>
    </motion.div>
  );
};
