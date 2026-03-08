# src/sri_dx/modules/indexing/concepts/lexicon_en.py
from __future__ import annotations

# Internal concept IDs.
# IMPORTANT: Write aliases already normalized (lowercase, no accents) to match Phase B.

LEXICON_EN: dict[str, list[str]] = {
    "DYSPNEA": [
        "dyspnea",
        "shortness of breath",
        "breathlessness",
        "difficulty breathing",
    ],
    "CHEST_PAIN": [
        "chest pain",
        "chest tightness",
        "chest pressure",
        "angina",
    ],
    "FEVER": [
        "fever",
        "high temperature",
        "hyperthermia",
        "pyrexia",
    ],
    "TACHYCARDIA": [
        "tachycardia",
        "high heart rate",
        "fast heart rate",
        "palpitations",
    ],
    "HYPERTENSION": [
        "hypertension",
        "high blood pressure",
    ],
    "DIABETES": [
        "diabetes",
        "diabetes mellitus",
    ],
    "HYPOXEMIA": [
        "hypoxemia",
        "low oxygen saturation",
        "low spo2",
        "hypoxia",
    ],
}
