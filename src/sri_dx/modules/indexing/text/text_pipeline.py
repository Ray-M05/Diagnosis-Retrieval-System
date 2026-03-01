from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from collections import Counter
from typing import Iterable, Optional

from .stopwords import STOPWORDS_ES, STOPWORDS_EN


# Tokens tipo: "covid-19", "hba1c", "pO2", "mg/dl" (la barra se separa, pero queda mg y dl)
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)*", flags=re.UNICODE)

_CONTROL_CHARS_RE = re.compile(r"[\u0000-\u001F\u007F]")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class TextPipelineConfig:
    lowercase: bool = True
    strip_accents: bool = True
    remove_stopwords: bool = True
    min_token_len: int = 2
    max_token_len: int = 40

    # Idioma: "es", "en" o None (auto simple)
    default_language: str = "en"


def normalize_text(text: str, cfg: TextPipelineConfig) -> str:
    if not text:
        return ""

    # Unicode normalize (reduce variantes raras)
    text = unicodedata.normalize("NFKC", text)

    # Quita control chars
    text = _CONTROL_CHARS_RE.sub(" ", text)

    # Normaliza guiones "raros" a guion normal
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")

    # Lowercase (opcional)
    if cfg.lowercase:
        text = text.lower()

    # Strip accents (opcional) sin dependencia externa
    if cfg.strip_accents:
        text = "".join(
            ch for ch in unicodedata.normalize("NFD", text)
            if not unicodedata.combining(ch)
        )

    # Colapsa whitespace
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def guess_language(text_norm: str) -> str:
    """
    Heurística sencilla:
    cuenta stopwords presentes en el texto normalizado.
    Si no decide, cae a 'en'.
    """
    if not text_norm:
        return "en"

    tokens = _TOKEN_RE.findall(text_norm)
    if not tokens:
        return "en"

    # Muestreo ligero para no costar mucho
    sample = tokens[:500]
    es_hits = sum(1 for t in sample if t in STOPWORDS_ES)
    en_hits = sum(1 for t in sample if t in STOPWORDS_EN)

    if es_hits > en_hits:
        return "es"
    return "en"


def tokenize(text_norm: str) -> list[str]:
    if not text_norm:
        return []
    return _TOKEN_RE.findall(text_norm)


def filter_tokens(tokens: Iterable[str], *, cfg: TextPipelineConfig, lang: str) -> list[str]:
    out: list[str] = []
    stop = set()
    if cfg.remove_stopwords:
        stop = STOPWORDS_ES if lang.startswith("es") else STOPWORDS_EN

    for t in tokens:
        if len(t) < cfg.min_token_len:
            continue
        if len(t) > cfg.max_token_len:
            continue
        if stop and t in stop:
            continue
        out.append(t)
    return out


@dataclass(frozen=True)
class TextAnalysis:
    language: str
    normalized: str
    tokens: list[str]
    tf: Counter[str]


class TextAnalyzer:
    def __init__(self, cfg: Optional[TextPipelineConfig] = None) -> None:
        self.cfg = cfg or TextPipelineConfig()

    def analyze(self, text: str, *, language: Optional[str] = None) -> TextAnalysis:
        norm = normalize_text(text, self.cfg)
        lang = (language or "").strip().lower()
        if not lang:
            lang = guess_language(norm)
        else:
            # normaliza etiquetas tipo "es-ES" -> "es"
            lang = lang.split("-")[0]

        toks = tokenize(norm)
        toks = filter_tokens(toks, cfg=self.cfg, lang=lang)
        tf = Counter(toks)

        return TextAnalysis(language=lang, normalized=norm, tokens=toks, tf=tf)
