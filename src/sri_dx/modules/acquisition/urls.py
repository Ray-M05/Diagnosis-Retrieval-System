from __future__ import annotations

from urllib.parse import urlparse, urlunparse, urljoin, parse_qsl, urlencode

# Params típicos de tracking que no queremos en URLs normalizadas
_TRACKING_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid"
}

# Substrings que suelen llevar a páginas inútiles para el corpus
_DENY_SUBSTRINGS = (
    "/login", "/signin", "/signup",
    "/search", "/cookie", "/privacy", "/terms",
)

_DENY_SCHEMES = ("mailto", "javascript", "tel")


def normalize_url(url: str) -> str:
    """
    Normaliza una URL de forma determinista:
    - quita fragment (#...)
    - elimina query params de tracking (utm_*, gclid, fbclid)
    """
    p = urlparse(url)
    # remove fragment
    p = p._replace(fragment="")

    # remove tracking params
    q = [
        (k, v)
        for (k, v) in parse_qsl(p.query, keep_blank_values=True)
        if k not in _TRACKING_KEYS
    ]
    p = p._replace(query=urlencode(q, doseq=True))
    return urlunparse(p)


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def is_denied(url: str) -> bool:
    p = urlparse(url)
    if p.scheme.lower() in _DENY_SCHEMES:
        return True

    u = url.lower()
    return any(s in u for s in _DENY_SUBSTRINGS)


def within_whitelist(url: str, whitelist: tuple[str, ...]) -> bool:
    """
    Acepta:
    - dominio exacto (cdc.gov)
    - subdominios (www.cdc.gov) si la whitelist contiene cdc.gov
    """
    domain = get_domain(url)
    for w in whitelist:
        w = w.lower()
        if domain == w or domain.endswith("." + w):
            return True
    return False


def absolutize(base_url: str, href: str) -> str:
    """
    Convierte href relativo a absoluto y lo normaliza.
    """
    return normalize_url(urljoin(base_url, href))