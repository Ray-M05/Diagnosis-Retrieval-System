"""Unit tests — MedicalApiSearchService failure propagation.

These verify that a source which *errored out* (timeout / HTTP / rate-limit) is
reported via ``ApiRetrievalStats.failed_sources``, distinct from a source that
genuinely returned zero results. The UI relies on this distinction to warn the
user instead of claiming "no documents were found".
"""
from __future__ import annotations

import asyncio

from sri_dx.adapters.medical_apis.medical_api_search_service import (
    MedicalApiSearchService,
)


def _run(service, symptoms):
    """Drive the async search on a private loop.

    ``MedicalApiSearchService.search_sync`` uses ``asyncio.run``, which closes
    the *global* default loop on exit. Other suites in this directory still use
    the deprecated ``asyncio.get_event_loop()`` pattern, so calling search_sync
    here would close the loop out from under them. Using a dedicated loop keeps
    the suites independent of collection order.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(service.search(symptoms))
    finally:
        loop.close()


class _FakeClient:
    """Minimal async stand-in for a medical API client."""

    def __init__(self, docs: list, failed: bool = False) -> None:
        self._docs = docs
        # Mirrors the real clients: set on every search() call.
        self.last_request_failed = failed

    async def search(self, query: str) -> list:  # noqa: ARG002
        return self._docs


def _service(*, ml_failed=False, epmc_failed=False, pubmed_failed=False,
             ml_docs=None, epmc_docs=None, pubmed_docs=None):
    return MedicalApiSearchService(
        medlineplus=_FakeClient(ml_docs or [], failed=ml_failed),
        europe_pmc=_FakeClient(epmc_docs or [], failed=epmc_failed),
        pubmed=_FakeClient(pubmed_docs or [], failed=pubmed_failed),
    )


class TestFailedSources:
    def test_no_failures_when_all_succeed(self):
        service = _service(epmc_docs=["a"], pubmed_docs=["b"])
        _, stats = _run(service, ["chest pain"])
        assert stats.failed_sources == []
        assert stats.had_failures is False
        assert stats.total == 2

    def test_empty_but_no_error_is_not_a_failure(self):
        # All sources returned 0 results cleanly — NOT a failure.
        service = _service()
        _, stats = _run(service, ["chest pain"])
        assert stats.total == 0
        assert stats.failed_sources == []
        assert stats.had_failures is False

    def test_errored_source_is_reported(self):
        # PubMed and EuropePMC errored out (e.g. rate-limited) → total 0 but
        # had_failures True, so the UI can warn rather than say "no results".
        service = _service(epmc_failed=True, pubmed_failed=True)
        _, stats = _run(service, ["chest pain"])
        assert stats.total == 0
        assert set(stats.failed_sources) == {"europe_pmc", "pubmed"}
        assert stats.had_failures is True

    def test_partial_success_with_one_failure(self):
        service = _service(epmc_docs=["a", "b"], pubmed_failed=True)
        _, stats = _run(service, ["chest pain"])
        assert stats.total == 2
        assert stats.failed_sources == ["pubmed"]
