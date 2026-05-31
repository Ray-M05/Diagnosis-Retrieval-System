"""
Medical APIs Adapter — PubMed Client (NCBI E-Utilities)

Step 1 — ESearch::

    GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
        ?db=pubmed&term=<query>&retmax=<n>&retmode=json

Step 2 — EFetch (only when PMIDs were found)::

    GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
        ?db=pubmed&id=<pmids>&retmode=xml

**No NCBI API key** is used in this implementation.  The default unauthenticated
rate limit is 3 requests per second.  To stay safe, ``retmax`` is intentionally
kept small (default 5) and no parallel EFetch batching is performed.
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from lxml import etree

from sri_dx.modules.web_search.normalizers import normalize_pubmed_article
from sri_dx.modules.web_search.schemas import ExternalApiDocument

logger = logging.getLogger(__name__)

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Polite delay between ESearch and EFetch (no API key → 3 req/s limit)
_INTER_REQUEST_DELAY = 0.4  # seconds


class PubMedClient:
    """
    Async two-step PubMed client (ESearch → EFetch).

    Parameters
    ----------
    retmax:
        Maximum number of PMIDs to retrieve via ESearch (default 5).
        Kept low because no API key is used.
    timeout:
        HTTP request timeout per request in seconds (default 20).
    """

    def __init__(self, retmax: int = 5, timeout: float = 20.0) -> None:
        self.retmax = retmax
        self.timeout = timeout
        # Set to True when the most recent search() errored out (timeout / HTTP
        # error / network failure) rather than genuinely returning no results.
        self.last_request_failed = False

    async def search(self, query: str) -> list[ExternalApiDocument]:
        """
        Search PubMed for English biomedical articles matching *query*.

        Parameters
        ----------
        query:
            Boolean query string in PubMed syntax
            (e.g. ``'("chest pain") AND (diagnosis OR etiology)'``).

        Returns
        -------
        list[ExternalApiDocument]
            Normalised documents.  Returns an empty list on any error.
        """
        logger.info(
            "PubMed ESearch: querying '%s...' (retmax=%d)", query[:80], self.retmax
        )
        self.last_request_failed = False

        pmids = await self._esearch(query)
        if not pmids:
            logger.info("PubMed: no PMIDs found for query '%s...'", query[:60])
            return []

        logger.info("PubMed ESearch: found %d PMID(s)", len(pmids))

        # Polite pause before EFetch
        await asyncio.sleep(_INTER_REQUEST_DELAY)

        return await self._efetch(pmids)

    async def _esearch(self, query: str) -> list[str]:
        """Run ESearch and return a list of PMID strings."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": self.retmax,
            "retmode": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(_ESEARCH_URL, params=params)
                response.raise_for_status()
        except httpx.TimeoutException:
            logger.warning("PubMed ESearch: timeout for query '%s...'", query[:60])
            self.last_request_failed = True
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "PubMed ESearch: HTTP %d for query '%s...'",
                exc.response.status_code, query[:60],
            )
            self.last_request_failed = True
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("PubMed ESearch: unexpected error — %s", exc)
            self.last_request_failed = True
            return []

        payload = response.json()
        id_list: list[str] = (
            payload.get("esearchresult", {}).get("idlist", [])
        )
        return id_list

    async def _efetch(self, pmids: list[str]) -> list[ExternalApiDocument]:
        """Run EFetch for the given PMIDs and return normalised documents."""
        id_str = ",".join(pmids)
        params = {
            "db": "pubmed",
            "id": id_str,
            "retmode": "xml",
        }

        logger.info("PubMed EFetch: fetching %d article(s)", len(pmids))

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(_EFETCH_URL, params=params)
                response.raise_for_status()
        except httpx.TimeoutException:
            logger.warning("PubMed EFetch: timeout for %d PMIDs", len(pmids))
            self.last_request_failed = True
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "PubMed EFetch: HTTP %d for %d PMIDs",
                exc.response.status_code, len(pmids),
            )
            self.last_request_failed = True
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("PubMed EFetch: unexpected error — %s", exc)
            self.last_request_failed = True
            return []

        return self._parse_xml(response.content)

    def _parse_xml(self, content: bytes) -> list[ExternalApiDocument]:
        """Parse EFetch XML and return normalised documents."""
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as exc:
            logger.warning("PubMed EFetch: XML parse error — %s", exc)
            return []

        docs: list[ExternalApiDocument] = []
        for article_el in root.findall(".//PubmedArticle"):
            try:
                ext = normalize_pubmed_article(article_el)
                docs.append(ext)
            except Exception as exc:  # noqa: BLE001
                logger.debug("PubMed EFetch: skipping malformed article — %s", exc)

        logger.info("PubMed: retrieved %d article(s)", len(docs))
        return docs
