"""Configuration defaults for clinical positioning."""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_WEIGHTS = {
    "cross_encoder": 0.45,
    "hybrid": 0.20,
    "symptom_coverage": 0.15,
    "authority": 0.15,
    "freshness": 0.05,
}


DEFAULT_SOURCE_RELIABILITY = {
    "medlineplus.gov": 1.00,
    "cdc.gov": 0.95,
    "who.int": 0.95,
    "mayoclinic.org": 0.95,
    "nhs.uk": 0.90,
    "msdmanuals.com": 0.90,
}


DEFAULT_PREFERRED_SECTIONS = {
    "symptoms": 1.00,
    "signs and symptoms": 1.00,
    "overview": 0.95,
    "causes": 0.90,
    "diagnosis": 0.90,
    "diagnosis and treatment": 0.85,
    "treatment": 0.75,
    "main": 0.70,
}


@dataclass(frozen=True)
class PositioningConfig:
    """Runtime knobs for clinical positioning V1."""

    top_k: int = 10
    top_evidences: int = 3
    lambda_mmr: float = 0.80
    min_ner_score: float = 0.50
    max_diseases_per_chunk: int = 3

    unknown_freshness_score: float = 0.60
    unknown_authority_score: float = 0.55
    missing_domain_authority_score: float = 0.40

    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    source_reliability: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SOURCE_RELIABILITY)
    )
    preferred_sections: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PREFERRED_SECTIONS)
    )
