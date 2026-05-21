import React from 'react';
import { Globe, Info, CheckCircle2 } from 'lucide-react';
import type { WebEnrichmentSummary } from '../api/client';

interface WebEnrichmentBannerProps {
  summary: WebEnrichmentSummary;
}

type BannerState = 'new_docs' | 'apis_empty' | 'all_duplicates';

function resolveState(summary: WebEnrichmentSummary): BannerState {
  if (summary.docs_added > 0) return 'new_docs';
  if (summary.api_retrieved === 0) return 'apis_empty';
  return 'all_duplicates';
}

export const WebEnrichmentBanner: React.FC<WebEnrichmentBannerProps> = ({ summary }) => {
  const state = resolveState(summary);

  if (state === 'new_docs') {
    return (
      <div className="px-4 py-2.5 bg-blue-50 border border-blue-100 rounded-xl flex items-center gap-2 text-xs text-blue-800 font-medium">
        <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
        Web search enabled — {summary.api_retrieved} document(s) retrieved,{' '}
        {summary.docs_added} new indexed from PubMed / EuropePMC / MedlinePlus
      </div>
    );
  }

  if (state === 'apis_empty') {
    return (
      <div className="px-4 py-2.5 bg-amber-50 border border-amber-100 rounded-xl flex items-start gap-2 text-xs text-amber-900 font-medium">
        <Info className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
        <span>
          Web search enabled — PubMed, EuropePMC and MedlinePlus returned no
          documents for this query. Results below come from the local corpus.
        </span>
      </div>
    );
  }

  return (
    <div className="px-4 py-2.5 bg-emerald-50 border border-emerald-100 rounded-xl flex items-start gap-2 text-xs text-emerald-900 font-medium">
      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
      <span>
        Web search enabled — {summary.api_retrieved} document(s) retrieved from
        PubMed / EuropePMC / MedlinePlus, all already present in the local
        corpus. No new information was added.
      </span>
    </div>
  );
};
