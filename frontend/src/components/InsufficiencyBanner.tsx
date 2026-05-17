import React from 'react';
import { Globe, Info } from 'lucide-react';
import type { SufficiencyInfo } from '../api/client';

interface InsufficiencyBannerProps {
  sufficiency: SufficiencyInfo;
  onActivateWeb?: () => void;
}

const CRITERIA_LABELS: Record<string, string> = {
  low_ranking_confidence: 'low confidence in results',
  few_useful_docs: 'few relevant documents',
  low_symptom_coverage: 'insufficient symptom coverage',
  low_source_diversity: 'few bibliographic sources',
  no_local_results: 'no local results',
};

export const InsufficiencyBanner: React.FC<InsufficiencyBannerProps> = ({
  sufficiency,
  onActivateWeb,
}) => {
  if (sufficiency.sufficient) return null;

  const criteriaText = sufficiency.failed_criteria
    .map((c) => CRITERIA_LABELS[c] ?? c)
    .join(', ');

  return (
    <div className="bg-amber-50 border border-amber-100 p-4 rounded-2xl flex items-start gap-4 shadow-sm w-full">
      <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-amber-900 leading-relaxed font-medium">
          <span className="font-bold text-amber-800 uppercase tracking-wide block mb-1">
            Insufficient knowledge:
          </span>
          The local knowledge base may not cover this query ({criteriaText}).
          Web search is recommended for more complete results.
        </p>
      </div>
      {onActivateWeb && (
        <button
          onClick={onActivateWeb}
          className="shrink-0 flex items-center gap-1.5 text-xs font-semibold text-amber-800 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer whitespace-nowrap"
        >
          <Globe className="w-3.5 h-3.5" />
          Enable web
        </button>
      )}
    </div>
  );
};
