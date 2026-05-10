"""Unit tests — MedlinePlusClient (mocked HTTP)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from sri_dx.adapters.medical_apis.medlineplus_client import MedlinePlusClient


# ---------------------------------------------------------------------------
# Fixtures / shared payloads
# ---------------------------------------------------------------------------

_VALID_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <list>
    <document rank="0" url="https://medlineplus.gov/chestpain.html">
      <content name="title">Chest Pain</content>
      <content name="FullSummary">Chest pain has many possible causes including heart, lung, and digestive problems.</content>
      <content name="snippet">Chest pain may be caused by heart, lung, digestive...</content>
      <content name="mesh">Chest Pain</content>
      <content name="mesh">Thoracic Diseases</content>
    </document>
    <document rank="1" url="https://medlineplus.gov/heartattack.html">
      <content name="title">Heart Attack</content>
      <content name="FullSummary">A heart attack occurs when blood flow to the heart is blocked.</content>
      <content name="snippet">Heart attack symptoms include chest pain and shortness of breath.</content>
    </document>
  </list>
</nlmSearchResult>
"""

_EMPTY_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <list/>
</nlmSearchResult>
"""


def _mock_response(content: bytes, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMedlinePlusClient:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("sri_dx.adapters.medical_apis.medlineplus_client.httpx.AsyncClient")
    def test_returns_documents_on_valid_response(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(_VALID_XML))

        client = MedlinePlusClient(retmax=10)
        docs = self._run(client.search("chest pain shortness of breath"))

        assert len(docs) == 2
        assert docs[0].source == "medlineplus"
        assert docs[0].title == "Chest Pain"
        assert "Chest Pain" in docs[0].mesh_terms

    @patch("sri_dx.adapters.medical_apis.medlineplus_client.httpx.AsyncClient")
    def test_empty_results(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(_EMPTY_XML))

        client = MedlinePlusClient()
        docs = self._run(client.search("query with no results"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.medlineplus_client.httpx.AsyncClient")
    def test_timeout_returns_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        client = MedlinePlusClient()
        docs = self._run(client.search("some query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.medlineplus_client.httpx.AsyncClient")
    def test_http_error_returns_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(b"", status_code=500))

        client = MedlinePlusClient()
        docs = self._run(client.search("some query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.medlineplus_client.httpx.AsyncClient")
    def test_invalid_xml_returns_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(b"NOT XML AT ALL <><"))

        client = MedlinePlusClient()
        docs = self._run(client.search("query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.medlineplus_client.httpx.AsyncClient")
    def test_canonical_url_normalised(self, mock_client_cls):
        """Fragment identifiers should be stripped from URLs."""
        xml = b"""<nlmSearchResult><list>
          <document rank="0" url="https://medlineplus.gov/chestpain.html#overview">
            <content name="title">Chest Pain</content>
            <content name="FullSummary">Summary text.</content>
          </document>
        </list></nlmSearchResult>"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(xml))

        client = MedlinePlusClient()
        docs = self._run(client.search("chest pain"))
        assert "#overview" not in docs[0].canonical_url
