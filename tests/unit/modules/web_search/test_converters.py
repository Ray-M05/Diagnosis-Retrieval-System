"""Unit tests — external_to_acquired_dict converter."""
from __future__ import annotations

import json

import pytest

from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.modules.web_search.converters import external_to_acquired_dict
from sri_dx.modules.web_search.schemas import ExternalApiDocument


def _ext(
    source: str = "pubmed",
    pmid: str | None = "12345678",
    pmcid: str | None = None,
    doi: str | None = None,
    url: str = "https://pubmed.ncbi.nlm.nih.gov/12345678/",
    title: str = "Chest Pain Review",
    abstract: str = "A comprehensive review of chest pain aetiology.",
    mesh: list[str] | None = None,
) -> ExternalApiDocument:
    return ExternalApiDocument(
        source=source,
        external_id=pmid or "unknown",
        canonical_url=url,
        title=title,
        abstract_or_summary=abstract,
        sections=[Section(heading="Abstract", text=abstract)],
        authors=["Smith J"],
        journal="BMJ Open",
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        mesh_terms=mesh or ["Chest Pain"],
    )


class TestExternalToAcquiredDict:
    def _convert(self, **kwargs) -> dict:
        return external_to_acquired_dict(
            _ext(**kwargs),
            query_id="abc12345",
            original_query="chest pain and shortness of breath",
        )

    def test_returns_dict(self):
        result = self._convert()
        assert isinstance(result, dict)

    def test_required_top_level_keys(self):
        result = self._convert()
        for key in ("doc_id", "url", "source_domain", "fetched_at", "crawl", "content", "page_meta", "content_hash"):
            assert key in result, f"Missing key: {key}"

    def test_crawl_fields(self):
        result = self._convert()
        crawl = result["crawl"]
        assert crawl["depth"] == 0
        assert crawl["seed_id"] == "abc12345"
        assert crawl["seed_group"] == "api_pubmed"

    def test_content_fields(self):
        result = self._convert()
        content = result["content"]
        assert content["mime_type"] == "application/json"
        assert content["title"] == "Chest Pain Review"
        assert isinstance(content["sections"], list)
        assert len(content["sections"]) >= 1
        assert content["body"]

    def test_doc_id_is_deterministic(self):
        """Same URL always produces the same doc_id."""
        r1 = self._convert(url="https://pubmed.ncbi.nlm.nih.gov/12345678/")
        r2 = self._convert(url="https://pubmed.ncbi.nlm.nih.gov/12345678/")
        assert r1["doc_id"] == r2["doc_id"]

    def test_content_hash_is_consistent(self):
        r1 = self._convert(abstract="A consistent abstract text.")
        r2 = self._convert(abstract="A consistent abstract text.")
        assert r1["content_hash"] == r2["content_hash"]

    def test_source_domain_extracted(self):
        result = self._convert(url="https://pubmed.ncbi.nlm.nih.gov/12345678/")
        assert result["source_domain"] == "pubmed.ncbi.nlm.nih.gov"

    def test_page_meta_language(self):
        result = self._convert()
        assert result["page_meta"]["language"] == "en"

    def test_page_meta_author(self):
        result = self._convert()
        assert "Smith" in (result["page_meta"]["author"] or "")

    def test_json_serialisable(self):
        """The dict must be JSON-serialisable without custom encoder."""
        result = self._convert()
        # Should not raise
        json.dumps(result, default=str)

    def test_medlineplus_source(self):
        result = external_to_acquired_dict(
            _ext(source="medlineplus", url="https://medlineplus.gov/chestpain.html"),
            query_id="q1",
            original_query="chest pain",
        )
        assert result["crawl"]["seed_group"] == "api_medlineplus"
        assert result["source_domain"] == "medlineplus.gov"

    def test_empty_abstract_and_sections_are_skipped(self):
        """Title-only API stubs should not pollute the acquired corpus."""
        result = external_to_acquired_dict(
            _ext(abstract="", url="https://pubmed.ncbi.nlm.nih.gov/1/"),
            query_id="q1",
            original_query="test",
        )
        assert result is None
