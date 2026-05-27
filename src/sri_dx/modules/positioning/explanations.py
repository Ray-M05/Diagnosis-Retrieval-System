"""Deterministic explanations for positioned clinical results."""

from __future__ import annotations

from sri_dx.modules.positioning.models import ClinicalGroup


def relevance_label(group: ClinicalGroup) -> str:
    ce = group.component_scores.get("cross_encoder", 0.0)
    coverage = group.component_scores.get("symptom_coverage", 0.0)
    authority = group.component_scores.get("authority", 0.0)

    if group.relevance_score >= 0.75 and ce >= 0.60 and (coverage >= 0.50 or authority >= 0.85):
        return "High"
    if group.relevance_score >= 0.50:
        return "Medium"
    return "Low"


def generate_explanation(group: ClinicalGroup) -> list[str]:
    """Generate transparent, non-diagnostic explanation bullets."""

    explanation: list[str] = []
    scores = group.component_scores

    if scores.get("cross_encoder", 0.0) >= 0.70:
        explanation.append("High semantic relevance between the query and the retrieved evidence.")
    elif scores.get("cross_encoder", 0.0) >= 0.45:
        explanation.append("Moderate semantic relevance to the user's query.")

    if group.matched_symptoms:
        joined = ", ".join(group.matched_symptoms[:4])
        explanation.append(f"Matches symptoms or concepts from the query: {joined}.")

    if scores.get("authority", 0.0) >= 0.85 and group.source_domains:
        domains = ", ".join(group.source_domains[:3])
        explanation.append(f"Includes evidence from trusted clinical sources: {domains}.")

    if len(group.evidences) >= 3:
        explanation.append("Has several retrieved evidence chunks associated with this clinical condition.")

    if group.mmr_score:
        explanation.append("Selected by balancing relevance and diversity against other results.")

    if not explanation:
        explanation.append("Informative result retrieved to support the differential analysis.")

    return explanation
