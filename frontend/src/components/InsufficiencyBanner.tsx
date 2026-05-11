import React from 'react';
import { Globe, Info } from 'lucide-react';
import type { SufficiencyInfo } from '../api/client';

interface InsufficiencyBannerProps {
  sufficiency: SufficiencyInfo;
  onActivateWeb?: () => void;
}

const CRITERIA_LABELS: Record<string, string> = {
  low_ranking_confidence: 'baja confianza en los resultados',
  few_useful_docs: 'pocos documentos relevantes',
  low_symptom_coverage: 'cobertura de síntomas insuficiente',
  low_source_diversity: 'pocas fuentes bibliográficas',
  no_local_results: 'sin resultados locales',
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
            Conocimiento insuficiente:
          </span>
          La base de conocimiento local puede no cubrir esta consulta ({criteriaText}).
          Se recomienda activar la búsqueda web para obtener resultados más completos.
        </p>
      </div>
      {onActivateWeb && (
        <button
          onClick={onActivateWeb}
          className="shrink-0 flex items-center gap-1.5 text-xs font-semibold text-amber-800 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer whitespace-nowrap"
        >
          <Globe className="w-3.5 h-3.5" />
          Activar web
        </button>
      )}
    </div>
  );
};
