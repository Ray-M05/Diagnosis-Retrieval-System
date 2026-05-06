"""Unit tests — EuropePmcClient (mocked HTTP)."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sri_dx.adapters.medical_apis.europe_pmc_client import EuropePmcClient


# ---------------------------------------------------------------------------
# Fixtures / shared payloads
# ---------------------------------------------------------------------------

def _result(**kwargs) -> dict:
    defaults = {
        "id": "28550024",
        "source": "MED",
        "pmid": "28550024",
        "pmcid": "PMC5726088",
        "doi": "10.1136/bmjopen-2017-015857",
        "title": "Chest pain and shortness of breath in cardiovascular disease",
        "journalTitle": "BMJ Open",
        "pubYear": "2017",
        "abstractText": "Objective: To determine characteristics.",
        "authorString": "Smith J, Doe A",
    }
    defaults.update(kwargs)
    return defaults


def _payload(results: list[dict]) -> dict:
    return {
        "hitCount": len(results),
        "resultList": {"result": results},
    }


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json = MagicMock(return_value=payload)
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEuropePmcClient:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("sri_dx.adapters.medical_apis.europe_pmc_client.httpx.AsyncClient")
    def test_returns_documents_on_valid_response(self, mock_client_cls):
        items = [_result(), _result(pmid="99999", doi=None, pmcid=None)]
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(_payload(items)))

        client = EuropePmcClient(retmax=10)
        docs = self._run(client.search("chest pain"))

        assert len(docs) == 2
        assert docs[0].source == "europe_pmc"
        assert docs[0].pmid == "28550024"
        assert docs[0].pmcid == "PMC5726088"
        assert docs[0].published_at.year == 2017

    @patch("sri_dx.adapters.medical_apis.europe_pmc_client.httpx.AsyncClient")
    def test_empty_results(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response({"hitCount": 0, "resultList": {"result": []}}))

        client = EuropePmcClient()
        docs = self._run(client.search("obscure query with no results"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.europe_pmc_client.httpx.AsyncClient")
    def test_timeout_returns_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        client = EuropePmcClient()
        docs = self._run(client.search("query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.europe_pmc_client.httpx.AsyncClient")
    def test_http_error_returns_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response({}, status_code=503))

        client = EuropePmcClient()
        docs = self._run(client.search("query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.europe_pmc_client.httpx.AsyncClient")
    def test_missing_abstract_handled(self, mock_client_cls):
        item = _result(abstractText=None)
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(_payload([item])))

        client = EuropePmcClient()
        docs = self._run(client.search("query"))
        assert len(docs) == 1
        assert docs[0].abstract_or_summary == ""

    @patch("sri_dx.adapters.medical_apis.europe_pmc_client.httpx.AsyncClient")
    def test_missing_pmcid_falls_back_to_pmid_url(self, mock_client_cls):
        item = _result(pmcid=None)
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(_payload([item])))

        client = EuropePmcClient()
        docs = self._run(client.search("query"))
        assert "MED" in docs[0].canonical_url or "28550024" in docs[0].canonical_url
