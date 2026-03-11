from __future__ import annotations
import re
from .schemas.acquisition_config import AcquisitionConfig

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", re.UNICODE)
AZ_RE = re.compile(r"\bA\s+B\s+C\s+D\s+E\b")

def should_persist(
    *,
    url: str,
    mime_type: str,
    body: str,
    out_links_count: int,
    cfg: AcquisitionConfig,
) -> bool:
    u = url.lower()

    # 1) Skip por patrón de URL (hubs/índices)
    if any(sub in u for sub in cfg.skip_persist_url_substrings):
        return False

    words = WORD_RE.findall(body or "")
    wc = len(words)

    # 2) Reglas por tipo
    if mime_type.startswith("text/html"):
        if wc < cfg.min_words_html:
            return False

        # Índice A-Z típico (como el de MedlinePlus)
        if cfg.detect_az_index and AZ_RE.search(body):
            return False

        # Muchísimos links suele ser “directory page”
        if out_links_count >= cfg.max_out_links_html and wc < cfg.min_words_html * 3:
            return False

        # Heurística de “listado”: demasiadas líneas muy cortas
        lines = [ln.strip() for ln in (body or "").splitlines() if ln.strip()]
        if lines:
            short_lines = sum(1 for ln in lines if len(ln.split()) <= 3)
            if (short_lines / len(lines)) > 0.60 and wc < cfg.min_words_html * 4:
                return False

        return True

    # PDF (texto extraído)
    if mime_type == "application/pdf":
        return wc >= cfg.min_words_pdf

    return False