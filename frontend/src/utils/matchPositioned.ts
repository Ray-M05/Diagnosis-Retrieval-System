import type { Disease } from '../types';
import type { PositionedResult } from '../api/client';

function normalize(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

/**
 * Given a PositionedResult, find the Disease in the hybrid list that refers
 * to the same condition. Match strategy:
 *   1. exact normalized match on disease_name / disease_name_display
 *   2. fall back to token-set containment (one is contained in the other)
 *   3. if no match, fall back to the first evidence chunk_id
 */
export function findHybridForPositioned(
  positioned: PositionedResult,
  hybrid: Disease[],
): Disease | null {
  const candidates = [positioned.disease_name, positioned.disease_name_display]
    .filter(Boolean)
    .map((n) => normalize(n as string));

  if (candidates.length === 0) return null;

  for (const cand of candidates) {
    const exact = hybrid.find((d) => normalize(d.name) === cand);
    if (exact) return exact;
  }

  for (const cand of candidates) {
    const candTokens = new Set(cand.split(' ').filter(Boolean));
    const partial = hybrid.find((d) => {
      const dn = normalize(d.name);
      const dnTokens = new Set(dn.split(' ').filter(Boolean));
      if (candTokens.size === 0 || dnTokens.size === 0) return false;
      const allInD = [...candTokens].every((t) => dnTokens.has(t));
      const allInCand = [...dnTokens].every((t) => candTokens.has(t));
      return allInD || allInCand;
    });
    if (partial) return partial;
  }

  // Last resort — link by first evidence chunk_id
  const firstEvidence = positioned.evidences?.[0];
  if (firstEvidence) {
    const byChunk = hybrid.find(
      (d) => d.feedback_chunk_id === firstEvidence.chunk_id,
    );
    if (byChunk) return byChunk;
  }

  return null;
}

/**
 * Build a synthetic Disease from a PositionedResult when no hybrid match is
 * available — keeps the UI consistent (we always render via ResultCard).
 */
export function syntheticDiseaseFromPositioned(
  positioned: PositionedResult,
): Disease {
  const firstEvidence = positioned.evidences?.[0];
  return {
    id: positioned.disease_name_display,
    name: positioned.disease_name_display,
    description: firstEvidence?.content_preview ?? '',
    symptoms: positioned.matched_symptoms,
    source: positioned.source_domains?.[0] ?? '',
    sourceUrl: firstEvidence?.url ?? '',
    evidence_count: positioned.evidences?.length ?? 0,
    rank: positioned.rank,
    feedback_chunk_id: firstEvidence?.chunk_id ?? null,
    feedback_doc_id: firstEvidence?.doc_id ?? null,
    score: positioned.final_score,
    doc_title: null,
  };
}
