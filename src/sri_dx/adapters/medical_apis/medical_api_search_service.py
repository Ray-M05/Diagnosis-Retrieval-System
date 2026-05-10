"""
Medical APIs Adapter — Medical API Search Service
Parallel orchestrator that queries MedlinePlus, Europe PMC and PubMed
concurrently using :mod:`asyncio` and returns a unified list of
:class:`ExternalApiDocument` objects.

The MedlinePlus client receives a simple keyword query; Europe PMC and PubMed
receive the scientific Boolean query (built by :mod:`query_builder`).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from sri_dx.adapters.medical_apis.europe_pmc_client import EuropePmcClient
from sri_dx.adapters.medical_apis.medlineplus_client import MedlinePlusClient
from sri_dx.adapters.medical_apis.pubmed_client import PubMedClient
from sri_dx.modules.web_search.query_builder import (
    build_medlineplus_query,
    build_scientific_query,
)
from sri_dx.modules.web_search.schemas import ApiRetrievalStats, ExternalApiDocument

logger = logging.getLogger(__name__)


@dataclass
class MedicalApiSearchService:
    """
    Queries all three medical APIs in parallel and returns a combined list.

    Parameters
    ----------
    medlineplus:
        :class:`MedlinePlusClient` instance.
    europe_pmc:
        :class:`EuropePmcClient` instance.
    pubmed:
        :class:`PubMedClient` instance.
    """

    medlineplus: MedlinePlusClient
    europe_pmc: EuropePmcClient
    pubmed: PubMedClient

    async def search(
        self,
        symptoms: list[str],
    ) -> tuple[list[ExternalApiDocument], ApiRetrievalStats]:
        """
        Query all three APIs in parallel for the given symptom list.

        Parameters
        ----------
        symptoms:
            Extracted symptom terms in English
            (e.g. ``["chest pain", "shortness of breath"]``).

        Returns
        -------
        tuple[list[ExternalApiDocument], ApiRetrievalStats]
            All documents combined and per-source counts.
        """
        ml_query = build_medlineplus_query(symptoms)
        sci_query = build_scientific_query(symptoms)

        logger.info(
            "MedicalApiSearchService: running 3 API queries in parallel "
            "(symptoms=%d)", len(symptoms)
        )
        logger.debug("MedlinePlus query: %s", ml_query)
        logger.debug("Scientific query:  %s", sci_query)

        ml_task = asyncio.create_task(
            self.medlineplus.search(ml_query), name="medlineplus"
        )
        epmc_task = asyncio.create_task(
            self.europe_pmc.search(sci_query), name="europe_pmc"
        )
        pubmed_task = asyncio.create_task(
            self.pubmed.search(sci_query), name="pubmed"
        )

        ml_docs, epmc_docs, pubmed_docs = await asyncio.gather(
            ml_task, epmc_task, pubmed_task
        )

        stats = ApiRetrievalStats(
            medlineplus=len(ml_docs),
            europe_pmc=len(epmc_docs),
            pubmed=len(pubmed_docs),
        )
        logger.info(
            "MedicalApiSearchService: retrieved %d total "
            "(MedlinePlus=%d, EuropePMC=%d, PubMed=%d)",
            stats.total, stats.medlineplus, stats.europe_pmc, stats.pubmed,
        )

        return ml_docs + epmc_docs + pubmed_docs, stats

    def search_sync(
        self,
        symptoms: list[str],
    ) -> tuple[list[ExternalApiDocument], ApiRetrievalStats]:
        """
        Synchronous wrapper around :meth:`search` for callers that are not
        inside an async context.
        """
        return asyncio.run(self.search(symptoms))
