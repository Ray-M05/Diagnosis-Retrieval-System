# src/sri_dx/modules/indexing/concepts/lexicon_es.py
from __future__ import annotations

# Internal concept IDs (simple strings). Can be migrated to Wikidata QIDs in the future.
# Aliases must be pre-normalized (lowercase, no diacritics) to match the indexing pipeline.

LEXICON_ES: dict[str, list[str]] = {
    "DISNEA": [
        "disnea",
        "dificultad respiratoria",
        "falta de aire",
        "ahogo",
    ],
    "DOLOR_TORACICO": [
        "dolor toracico",
        "opresion toracica",
        "dolor en el pecho",
        "pecho opresivo",
    ],
    "FIEBRE": [
        "fiebre",
        "temperatura alta",
        "hipertermia",
    ],
    "TAQUICARDIA": [
        "taquicardia",
        "frecuencia cardiaca elevada",
        "palpitaciones",
    ],
    "HIPERTENSION": [
        "hipertension",
        "presion arterial alta",
    ],
    "DIABETES": [
        "diabetes",
        "diabetes mellitus",
    ],
    "HIPOXEMIA": [
        "hipoxemia",
        "saturacion baja",
        "spo2 baja",
        "saturacion de oxigeno baja",
    ],
}
