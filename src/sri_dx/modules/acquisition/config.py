from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class Seed:
    """Seed (URL inicial) que alimenta el crawler."""
    seed_id: str
    seed_group: str
    url: str


@dataclass(frozen=True)
class AcquisitionConfig:
    # HTTP / crawling
    user_agent: str = "sri-dx-acquisition/0.1"
    timeout_s: float = 20.0
    per_domain_delay_s: float = 1.0
    max_depth: int = 2
    max_docs: int = 2500
    verify_ssl: bool = True
    max_workers: int = 8  # concurrent fetcher threads

    # Fuentes permitidas
    whitelist_domains: Tuple[str, ...] = ()

    # Seeds iniciales
    seeds: Tuple[Seed, ...] = ()

    # Salidas (solo JSONL, organizado por tipo)
    out_dir: Path = Path("data/processed")
    out_html_name: str = "docs_html.jsonl"
    out_pdf_name: str = "docs_pdf.jsonl"

    # Persistencia (solo decide qué guardar)
    min_words_html: int = 200
    min_words_pdf: int = 200
    max_out_links_html: int = 120
    skip_persist_url_substrings: Tuple[str, ...] = ()
    detect_az_index: bool = True