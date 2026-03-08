# src/sri_dx/modules/indexing/concepts/extractor.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sri_dx.modules.indexing.text.text_pipeline import normalize_text, TextPipelineConfig
from .lexicon_en import LEXICON_EN

try:
    import ahocorasick  # pyahocorasick
except Exception:  # pragma: no cover
    ahocorasick = None


@dataclass(frozen=True)
class ConceptExtractorConfig:
    # Reutilizamos normalización compatible con Fase B
    text_cfg: TextPipelineConfig = TextPipelineConfig(
        lowercase=True,
        strip_accents=True,
        remove_stopwords=False,   # para matching de frases NO conviene quitar stopwords
    )


class ConceptExtractor:
    """
    Extrae concept_ids desde texto usando matching de aliases.
    """
    def __init__(self, cfg: Optional[ConceptExtractorConfig] = None) -> None:
        self.cfg = cfg or ConceptExtractorConfig()
        self._automaton = self._build_automaton()

    def _build_automaton(self):
        if ahocorasick is None:
            return None

        A = ahocorasick.Automaton()
        for concept_id, aliases in LEXICON_EN.items():
            for alias in aliases:
                alias_norm = normalize_text(alias, self.cfg.text_cfg)
                if alias_norm:
                    # value = concept_id
                    A.add_word(alias_norm, (len(alias_norm), concept_id))
        A.make_automaton()
        return A

    def extract(self, text: str, *, language: Optional[str] = "en") -> list[str]:
        """
        Retorna concept_ids deduplicados.
        """
        if not text:
            return []

        text_norm = normalize_text(text, self.cfg.text_cfg)
        if not text_norm:
            return []

        found: set[str] = set()

        if self._automaton is not None:
            # Iterar sobre las coincidencias
            for _, (_, concept_id) in self._automaton.iter(text_norm):
                found.add(concept_id)
            return sorted(found)

        # Fallback simple (si no está pyahocorasick)
        # Búsqueda substring simple. Hay que iterar y usar `in`.
        for concept_id, aliases in LEXICON_EN.items():
            for alias in aliases:
                alias_norm = normalize_text(alias, self.cfg.text_cfg)
                if alias_norm and alias_norm in text_norm:
                    found.add(concept_id)
                    break
        return sorted(found)

