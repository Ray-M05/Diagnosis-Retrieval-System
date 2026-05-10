"""Deterministic explanations for positioned clinical results."""

from __future__ import annotations

from sri_dx.modules.positioning.models import ClinicalGroup


def relevance_label(group: ClinicalGroup) -> str:
    ce = group.component_scores.get("cross_encoder", 0.0)
    coverage = group.component_scores.get("symptom_coverage", 0.0)
    authority = group.component_scores.get("authority", 0.0)

    if group.relevance_score >= 0.75 and ce >= 0.60 and (coverage >= 0.50 or authority >= 0.85):
        return "Alta"
    if group.relevance_score >= 0.50:
        return "Media"
    return "Baja"


def generate_explanation(group: ClinicalGroup) -> list[str]:
    """Generate transparent, non-diagnostic explanation bullets."""

    explanation: list[str] = []
    scores = group.component_scores

    if scores.get("cross_encoder", 0.0) >= 0.70:
        explanation.append("Alta relevancia semantica entre la consulta y las evidencias recuperadas.")
    elif scores.get("cross_encoder", 0.0) >= 0.45:
        explanation.append("Relevancia semantica moderada con la consulta del usuario.")

    if group.matched_symptoms:
        joined = ", ".join(group.matched_symptoms[:4])
        explanation.append(f"Coincide con sintomas o conceptos de la consulta: {joined}.")

    if scores.get("authority", 0.0) >= 0.85 and group.source_domains:
        domains = ", ".join(group.source_domains[:3])
        explanation.append(f"Incluye evidencia procedente de fuentes clinicas confiables: {domains}.")

    if len(group.evidences) >= 3:
        explanation.append("Tiene varias evidencias recuperadas asociadas a esta condicion clinica.")

    if group.mmr_score:
        explanation.append("Fue seleccionado considerando relevancia y diversidad frente a otros resultados.")

    if not explanation:
        explanation.append("Resultado informativo recuperado para apoyar el analisis diferencial.")

    return explanation
