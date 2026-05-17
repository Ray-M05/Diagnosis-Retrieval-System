import React from 'react';
import { Link2, Target, FileText, Globe } from 'lucide-react';
import { motion } from 'motion/react';
import type { Disease } from '../types';

interface WebDocumentCardProps {
  disease: Disease;
}

/**
 * Card used to render a single chunk/document returned by Web Search
 * (the /pipeline endpoint when web_enrichment is enabled).
 *
 * Shape-wise the backend reuses DiseaseDTO, but conceptually each item is
 * a single document/chunk rather than an NER-aggregated disease. This card
 * surfaces the document title, the chunk preview and the rerank score —
 * which is what the Testing/Web Search panel already does.
 */
export const WebDocumentCard: React.FC<WebDocumentCardProps> = ({ disease }) => {
  const title = disease.doc_title || disease.name || 'Untitled document';
  const snippet = disease.description || '';
  const score = typeof disease.score === 'number' ? disease.score : 0;
  const source = disease.source || (disease.sourceUrl ? disease.sourceUrl.split('/')[2] ?? '' : '');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow w-full flex flex-col gap-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {disease.rank > 0 && (
            <span className="shrink-0 w-7 h-7 rounded-xl bg-indigo-600 text-white text-xs font-black flex items-center justify-center shadow-sm shadow-indigo-100">
              {disease.rank}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <h3 className="text-base font-bold text-gray-900 leading-tight flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
              <span className="truncate">{title}</span>
            </h3>
            {source && (
              <p className="mt-0.5 text-[11px] text-gray-400 flex items-center gap-1">
                <Globe className="w-3 h-3" />
                {source}
              </p>
            )}
          </div>
        </div>
        {score > 0 && (
          <span className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full text-[11px] font-bold border border-amber-100/50">
            <Target className="w-3 h-3" />
            {score.toFixed(score < 1 ? 3 : 2)}
          </span>
        )}
      </div>

      {snippet && (
        <p className="text-sm text-gray-600 leading-relaxed italic line-clamp-4">
          “{snippet}”
        </p>
      )}

      {disease.sourceUrl && (
        <a
          href={disease.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="self-start inline-flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
        >
          <Link2 className="w-3 h-3" />
          <span className="truncate max-w-[280px]">{disease.sourceUrl}</span>
        </a>
      )}
    </motion.div>
  );
};
