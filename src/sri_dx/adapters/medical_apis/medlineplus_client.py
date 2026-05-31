"""
Medical APIs Adapter — MedlinePlus Client
Endpoint::
    GET https://wsearch.nlm.nih.gov/ws/query
        ?db=healthTopics
        &term=<query>
        &retmax=<n>
        &rettype=brief

The service returns XML.  Results are English health-topic pages from the
National Library of Medicine.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from lxml import etree

from sri_dx.modules.web_search.normalizers import normalize_medlineplus_document
from sri_dx.modules.web_search.schemas import ExternalApiDocument

logger = logging.getLogger(__name__)

_BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"


class MedlinePlusClient:
    """
    Async client for MedlinePlus health-topic search.

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
        # Set to True when the most recent search() errored out (timeout / HTTP
        # error / network failure) rather than genuinely returning no results.
        self.last_request_failed = False

    async def search(self, query: str) -> list[ExternalApiDocument]:
        """
        Search MedlinePlus for English health topics matching *query*.

        Parameters
        ----------
        query:
            Plain-text query (e.g. ``"chest pain shortness of breath"``).

        Returns
        -------
        list[ExternalApiDocument]
            Normalised documents.  Returns an empty list on any error.
        """
        params: dict[str, Any] = {
            "db": "healthTopics",
            "term": query,
            "retmax": self.retmax,
            "rettype": "brief",
        }

        logger.info("MedlinePlus: querying '%s...' (retmax=%d)", query[:60], self.retmax)
        self.last_request_failed = False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(_BASE_URL, params=params)
                response.raise_for_status()
        except httpx.TimeoutException:
            logger.warning("MedlinePlus: request timed out for query '%s...'", query[:60])
            self.last_request_failed = True
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "MedlinePlus: HTTP %d for query '%s...'",
                exc.response.status_code, query[:60],
            )
            self.last_request_failed = True
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("MedlinePlus: unexpected error — %s", exc)
            self.last_request_failed = True
            return []

        return self._parse_xml(response.content, query)

    def _parse_xml(self, content: bytes, query: str) -> list[ExternalApiDocument]:
        """Parse the XML response and return normalised documents."""
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as exc:
            logger.warning("MedlinePlus: XML parse error — %s", exc)
            return []

        docs: list[ExternalApiDocument] = []
        for doc_el in root.findall(".//document"):
            try:
                ext = normalize_medlineplus_document(doc_el)
                docs.append(ext)
            except Exception as exc:  # noqa: BLE001
                logger.debug("MedlinePlus: skipping malformed document — %s", exc)

        logger.info("MedlinePlus: retrieved %d document(s)", len(docs))
        return docs
