"""Unit tests — PubMedClient (mocked HTTP)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from sri_dx.adapters.medical_apis.pubmed_client import PubMedClient


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_ESEARCH_RESP = {
    "esearchresult": {
        "count": "2",
        "retmax": "5",
        "idlist": ["28550024", "12345678"],
    }
}

_ESEARCH_EMPTY = {
    "esearchresult": {
        "count": "0",
        "retmax": "5",
        "idlist": [],
    }
}

_EFETCH_XML = b"""<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>28550024</PMID>
      <Article>
        <ArticleTitle>Chest pain and shortness of breath in cardiovascular disease</ArticleTitle>
        <Abstract>
          <AbstractText>Objective: To determine characteristics.</AbstractText>
        </Abstract>
        <Journal><Title>BMJ Open</Title></Journal>
        <AuthorList>
          <Author><LastName>Smith</LastName><ForeName>John</ForeName></Author>
        </AuthorList>
      </Article>
      <PubDate><Year>2017</Year></PubDate>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Chest Pain</DescriptorName></MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1136/bmjopen-2017</ArticleId>
        <ArticleId IdType="pmc">PMC5726088</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Dyspnea and cardiac disease</ArticleTitle>
        <Abstract><AbstractText>Abstract about dyspnea.</AbstractText></Abstract>
        <Journal><Title>Heart Journal</Title></Journal>
      </Article>
      <PubDate><Year>2020</Year></PubDate>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _mock_json_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json = MagicMock(return_value=payload)
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


def _mock_xml_response(content: bytes, status_code: int = 200) -> MagicMock:
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

class TestPubMedClient:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _setup_two_step_mock(
        self,
        mock_client_cls: MagicMock,
        esearch_payload: dict = _ESEARCH_RESP,
        efetch_content: bytes = _EFETCH_XML,
        esearch_status: int = 200,
        efetch_status: int = 200,
    ) -> None:
        """Configure mock to return ESearch then EFetch responses."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        esearch_resp = _mock_json_response(esearch_payload, esearch_status)
        efetch_resp = _mock_xml_response(efetch_content, efetch_status)

        mock_client.get = AsyncMock(side_effect=[esearch_resp, efetch_resp])

    @patch("sri_dx.adapters.medical_apis.pubmed_client.asyncio.sleep", new_callable=AsyncMock)
    @patch("sri_dx.adapters.medical_apis.pubmed_client.httpx.AsyncClient")
    def test_returns_documents_on_valid_responses(self, mock_client_cls, _mock_sleep):
        self._setup_two_step_mock(mock_client_cls)
        client = PubMedClient(retmax=5)
        docs = self._run(client.search("chest pain"))

        assert len(docs) == 2
        assert docs[0].source == "pubmed"
        assert docs[0].pmid == "28550024"
        assert "Chest Pain" in docs[0].mesh_terms
        assert docs[0].published_at.year == 2017

    @patch("sri_dx.adapters.medical_apis.pubmed_client.asyncio.sleep", new_callable=AsyncMock)
    @patch("sri_dx.adapters.medical_apis.pubmed_client.httpx.AsyncClient")
    def test_empty_esearch_skips_efetch(self, mock_client_cls, _mock_sleep):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_json_response(_ESEARCH_EMPTY))

        client = PubMedClient(retmax=5)
        docs = self._run(client.search("very obscure query"))

        # EFetch should NOT be called when no PMIDs found
        assert mock_client.get.call_count == 1
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.pubmed_client.httpx.AsyncClient")
    def test_esearch_timeout_returns_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        client = PubMedClient()
        docs = self._run(client.search("query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.pubmed_client.asyncio.sleep", new_callable=AsyncMock)
    @patch("sri_dx.adapters.medical_apis.pubmed_client.httpx.AsyncClient")
    def test_efetch_http_error_returns_empty(self, mock_client_cls, _mock_sleep):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        esearch_resp = _mock_json_response(_ESEARCH_RESP)
        efetch_resp = _mock_xml_response(b"", status_code=429)
        mock_client.get = AsyncMock(side_effect=[esearch_resp, efetch_resp])

        client = PubMedClient()
        docs = self._run(client.search("query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.pubmed_client.asyncio.sleep", new_callable=AsyncMock)
    @patch("sri_dx.adapters.medical_apis.pubmed_client.httpx.AsyncClient")
    def test_efetch_invalid_xml_returns_empty(self, mock_client_cls, _mock_sleep):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        esearch_resp = _mock_json_response(_ESEARCH_RESP)
        efetch_resp = _mock_xml_response(b"NOT VALID XML")
        mock_client.get = AsyncMock(side_effect=[esearch_resp, efetch_resp])

        client = PubMedClient()
        docs = self._run(client.search("query"))
        assert docs == []

    @patch("sri_dx.adapters.medical_apis.pubmed_client.asyncio.sleep", new_callable=AsyncMock)
    @patch("sri_dx.adapters.medical_apis.pubmed_client.httpx.AsyncClient")
    def test_polite_delay_called(self, mock_client_cls, mock_sleep):
        """Verifies the inter-request delay is applied between ESearch and EFetch."""
        self._setup_two_step_mock(mock_client_cls)
        client = PubMedClient()
        self._run(client.search("chest pain"))
        mock_sleep.assert_called_once()
