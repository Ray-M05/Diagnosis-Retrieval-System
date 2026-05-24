"""UMLS REST API adapter for disease name normalization.

Authentication flow:
  1. POST /auth/token  → obtain TGT (Ticket Granting Ticket) using the API key
  2. POST {tgt_url}    → obtain a single-use ST (Service Ticket)
  3. GET  /search/current?string=...&sabs=SNOMEDCT_US,MSH → search concepts

The TGT is cached in memory (~8 h lifetime) to avoid re-authentication per lookup.
"""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_UMLS_AUTH_URL = "https://utslogin.nlm.nih.gov/cas/v1/api-key"
_UMLS_SEARCH_URL = "https://uts-ws.nlm.nih.gov/rest/search/current"
_UMLS_SERVICE = "http://umlsks.nlm.nih.gov"

# Priority order: SNOMED CT US, MeSH, OMIM, ICD-10-CM
_DEFAULT_SABS = "SNOMEDCT_US,MSH,OMIM,ICD10CM"


class UMLSNormalizerAdapter:
    """Normalizes disease names via UMLS Metathesaurus REST API."""

    def __init__(
        self,
        api_key: str,
        sabs: str = _DEFAULT_SABS,
        timeout_s: float = 5.0,
    ) -> None:
        if not api_key:
            raise ValueError("UMLS_API_KEY is required")
        self._api_key = api_key
        self._sabs = sabs
        self._timeout = timeout_s
        self._tgt_url: Optional[str] = None
        self._tgt_expires_at: float = 0.0
        self._lock = Lock()
        self._cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public interface (DiseaseNormalizerPort)
    # ------------------------------------------------------------------

    def normalize(self, disease_name: str) -> str:
        """Returns the canonical UMLS name, or the original name if no match found."""
        key = disease_name.strip().lower()
        if not key:
            return disease_name

        if key in self._cache:
            return self._cache[key]

        try:
            canonical = self._lookup(key)
        except Exception as exc:
            logger.warning("UMLS lookup failed for '%s': %s", disease_name, exc)
            canonical = disease_name

        self._cache[key] = canonical
        return canonical

    # ------------------------------------------------------------------
    # Internal UMLS auth + search
    # ------------------------------------------------------------------

    def _get_tgt(self) -> str:
        """Returns a cached TGT (valid ~8 h) or acquires a new one."""
        with self._lock:
            if self._tgt_url and time.time() < self._tgt_expires_at:
                return self._tgt_url

            resp = requests.post(
                _UMLS_AUTH_URL,
                data={"apikey": self._api_key},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            tgt_url = resp.headers.get("location") or resp.url
            if not tgt_url or "TGT" not in tgt_url:
                raise RuntimeError(f"Could not obtain TGT: {resp.text[:200]}")

            self._tgt_url = tgt_url
            self._tgt_expires_at = time.time() + 8 * 3600 - 60  # 1-minute safety margin
            return self._tgt_url

    def _get_service_ticket(self) -> str:
        tgt_url = self._get_tgt()
        resp = requests.post(
            tgt_url,
            data={"service": _UMLS_SERVICE},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def _lookup(self, name: str) -> str:
        st = self._get_service_ticket()
        resp = requests.get(
            _UMLS_SEARCH_URL,
            params={
                "string": name,
                "ticket": st,
                "sabs": self._sabs,
                "searchType": "normalizedWords",
                "returnIdType": "concept",
                "pageSize": 1,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("result", {}).get("results", [])
        if not results or results[0].get("ui") == "NONE":
            return name

        preferred = results[0].get("name", "").strip()
        return preferred.lower() if preferred else name
