"""
Async client for the Europe PMC REST API.

Endpoint::
    GET https://www.ebi.ac.uk/europepmc/webservices/rest/search
        ?query=<query>
        &format=json
        &pageSize=<n>
        &resultType=core
"""
from __future__ import annotations

import logging

import httpx

from sri_dx.modules.web_search.normalizers import normalize_europe_pmc_result
from sri_dx.modules.web_search.schemas import ExternalApiDocument

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class EuropePmcClient:
    """
    Async client for Europe PMC biomedical publication search.

    Parameters
    ----------
    retmax:
        Maximum number of results to request (default 8).
    timeout:
        HTTP request timeout in seconds (default 20).
    """

    def __init__(self, retmax: int = 8, timeout: float = 20.0) -> None:
        self.retmax = retmax
        self.timeout = timeout

    async def search(self, query: str) -> list[ExternalApiDocument]:
        """
        Search Europe PMC for English biomedical publications matching *query*.

        Parameters
        ----------
        query:
            Boolean query string
            (e.g. ``'("chest pain") AND (diagnosis OR etiology)'``).

        Returns
        -------
        list[ExternalApiDocument]
            Normalised documents.  Returns an empty list on any error.
        """
        params = {
            "query": query,
            "format": "json",
            "pageSize": self.retmax,
            "resultType": "core",
        }

        logger.info(
            "Europe PMC: querying '%s...' (pageSize=%d)", query[:80], self.retmax
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(_BASE_URL, params=params)
                response.raise_for_status()
        except httpx.TimeoutException:
            logger.warning("Europe PMC: request timed out for query '%s...'", query[:60])
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Europe PMC: HTTP %d for query '%s...'",
                exc.response.status_code, query[:60],
            )
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Europe PMC: unexpected error — %s", exc)
            return []

        return self._parse_json(response.json(), query)

    def _parse_json(self, payload: dict, query: str) -> list[ExternalApiDocument]:
        """Parse the JSON response and return normalised documents."""
        results_raw = (
            payload
            .get("resultList", {})
            .get("result", [])
        )

        if not results_raw:
            hit_count = payload.get("hitCount", 0)
            logger.info(
                "Europe PMC: 0 results returned (hitCount=%s) for '%s...'",
                hit_count, query[:60],
            )
            return []

        docs: list[ExternalApiDocument] = []
        for item in results_raw:
            try:
                ext = normalize_europe_pmc_result(item)
                docs.append(ext)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Europe PMC: skipping malformed result — %s", exc)

        logger.info("Europe PMC: retrieved %d document(s)", len(docs))
        return docs
