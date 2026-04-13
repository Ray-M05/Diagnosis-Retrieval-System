from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schemas.acquisition_config import AcquisitionConfig, Seed


def load_acquisition_config(path: Path) -> AcquisitionConfig:
    """
    Lee configs/acquisition.yaml y lo convierte a AcquisitionConfig.
    Mantiene defaults si faltan campos.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("El YAML debe ser un diccionario en la raíz.")

    # Campos simples (con fallback a defaults del dataclass)
    user_agent = data.get("user_agent", AcquisitionConfig.user_agent)
    timeout_s = float(data.get("timeout_s", AcquisitionConfig.timeout_s))
    per_domain_delay_s = float(data.get("per_domain_delay_s", AcquisitionConfig.per_domain_delay_s))
    max_depth = int(data.get("max_depth", AcquisitionConfig.max_depth))
    max_docs = int(data.get("max_docs", AcquisitionConfig.max_docs))
    max_workers = int(data.get("max_workers", AcquisitionConfig.max_workers))

    # Whitelist
    whitelist = data.get("whitelist_domains", [])
    if whitelist is None:
        whitelist = []
    if not isinstance(whitelist, list):
        raise ValueError("whitelist_domains debe ser una lista.")
    whitelist_domains = tuple(str(x).strip() for x in whitelist if str(x).strip())

    # Seeds
    seeds_raw = data.get("seeds", [])
    if seeds_raw is None:
        seeds_raw = []
    if not isinstance(seeds_raw, list):
        raise ValueError("seeds debe ser una lista.")
    seeds: list[Seed] = []
    for i, item in enumerate(seeds_raw):
        if not isinstance(item, dict):
            raise ValueError(f"Cada seed debe ser un dict. Error en índice {i}.")
        seed_id = str(item.get("seed_id", "")).strip()
        seed_group = str(item.get("seed_group", "")).strip()
        url = str(item.get("url", "")).strip()
        if not seed_id or not seed_group or not url:
            raise ValueError(f"Seed incompleta en índice {i}: requiere seed_id, seed_group, url.")
        seeds.append(Seed(seed_id=seed_id, seed_group=seed_group, url=url))

    # Output (opcional)
    out = data.get("out", {}) or {}
    if not isinstance(out, dict):
        raise ValueError("out debe ser un dict si se provee.")
    out_dir = Path(str(out.get("dir", AcquisitionConfig.out_dir)))
    out_html_name = str(out.get("html_name", AcquisitionConfig.out_html_name))
    out_pdf_name = str(out.get("pdf_name", AcquisitionConfig.out_pdf_name))

    # Persist policy (opcional)
    persist = data.get("persist", {}) or {}
    if not isinstance(persist, dict):
        raise ValueError("persist debe ser un dict si se provee.")
    min_words_html = int(persist.get("min_words_html", AcquisitionConfig.min_words_html))
    min_words_pdf = int(persist.get("min_words_pdf", AcquisitionConfig.min_words_pdf))
    max_out_links_html = int(persist.get("max_out_links_html", AcquisitionConfig.max_out_links_html))
    detect_az_index = bool(persist.get("detect_az_index", AcquisitionConfig.detect_az_index))
    skip_raw = persist.get("skip_url_substrings", [])
    if skip_raw is None:
        skip_raw = []
    skip_persist_url_substrings = tuple(
        str(s).strip() for s in skip_raw if str(s).strip()
    )

    return AcquisitionConfig(
        user_agent=user_agent,
        timeout_s=timeout_s,
        per_domain_delay_s=per_domain_delay_s,
        max_depth=max_depth,
        max_docs=max_docs,
        max_workers=max_workers,
        whitelist_domains=whitelist_domains,
        seeds=tuple(seeds),
        out_dir=out_dir,
        out_html_name=out_html_name,
        out_pdf_name=out_pdf_name,
        min_words_html=min_words_html,
        min_words_pdf=min_words_pdf,
        max_out_links_html=max_out_links_html,
        detect_az_index=detect_az_index,
        skip_persist_url_substrings=skip_persist_url_substrings,
    )