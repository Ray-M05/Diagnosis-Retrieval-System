"""Unit tests — normalizers (MedlinePlus, Europe PMC, PubMed)."""
from __future__ import annotations

import pytest
from lxml import etree

from sri_dx.modules.web_search.normalizers import (
    normalize_europe_pmc_result,
    normalize_medlineplus_document,
    normalize_pubmed_article,
)


# ---------------------------------------------------------------------------
# MedlinePlus
# ---------------------------------------------------------------------------

def _ml_xml(url: str, title: str, summary: str, snippet: str = "", mesh: list[str] | None = None) -> etree._Element:
    """Build a minimal MedlinePlus <document> element."""
    doc = etree.Element("document", url=url)

    def _add(name: str, text: str) -> None:
        el = etree.SubElement(doc, "content", name=name)
        el.text = text

    _add("title", title)
    if summary:
        _add("FullSummary", summary)
    if snippet:
        _add("snippet", snippet)
    for term in (mesh or []):
        _add("mesh", term)
    return doc


class TestNormalizeMedlinePlus:
    def test_basic_fields(self):
        el = _ml_xml(
            url="https://medlineplus.gov/chestpain.html",
            title="Chest Pain",
            summary="Chest pain has many possible causes...",
            snippet="Chest pain may be caused by heart problems.",
            mesh=["Chest Pain", "Thoracic Diseases"],
        )
        doc = normalize_medlineplus_document(el)
        assert doc.source == "medlineplus"
        assert doc.title == "Chest Pain"
        assert doc.canonical_url == "https://medlineplus.gov/chestpain.html"
        assert "National Library of Medicine" in doc.authors
        assert "Chest Pain" in doc.mesh_terms
        assert doc.language == "en"

    def test_sections_built(self):
        el = _ml_xml(
            url="https://medlineplus.gov/test.html",
            title="Test",
            summary="Full summary here.",
            snippet="Short snippet.",
        )
        doc = normalize_medlineplus_document(el)
        headings = [s.heading for s in doc.sections]
        assert "Summary" in headings

    def test_missing_summary_falls_back_to_title(self):
        doc_el = etree.Element("document", url="https://medlineplus.gov/x.html")
        title_el = etree.SubElement(doc_el, "content", name="title")
        title_el.text = "Dyspnea"
        doc = normalize_medlineplus_document(doc_el)
        # Should not raise; sections should not be empty
        assert len(doc.sections) >= 1

    def test_url_is_normalised(self):
        el = _ml_xml(
            url="https://medlineplus.gov/chestpain.html#section",
            title="T", summary="S",
        )
        doc = normalize_medlineplus_document(el)
        assert "#section" not in doc.canonical_url

    def test_no_mesh_terms(self):
        el = _ml_xml(url="https://medlineplus.gov/x.html", title="T", summary="S")
        doc = normalize_medlineplus_document(el)
        assert doc.mesh_terms == []


# ---------------------------------------------------------------------------
# Europe PMC
# ---------------------------------------------------------------------------

_EPMC_ITEM = {
    "id": "28550024",
    "source": "MED",
    "pmid": "28550024",
    "pmcid": "PMC5726088",
    "doi": "10.1136/bmjopen-2017-015857",
    "title": "Chest pain and shortness of breath in cardiovascular disease",
    "journalTitle": "BMJ Open",
    "pubYear": "2017",
    "abstractText": "Objective: To determine characteristics associated with chest pain.",
    "authorString": "Smith J, Doe A, Garcia M",
}


class TestNormalizeEuropePmc:
    def test_basic_fields(self):
        doc = normalize_europe_pmc_result(_EPMC_ITEM)
        assert doc.source == "europe_pmc"
        assert doc.pmid == "28550024"
        assert doc.pmcid == "PMC5726088"
        assert doc.doi == "10.1136/bmjopen-2017-015857"
        assert doc.journal == "BMJ Open"
        assert doc.title == "Chest pain and shortness of breath in cardiovascular disease"
        assert len(doc.authors) == 3

    def test_canonical_url_uses_pmcid(self):
        doc = normalize_europe_pmc_result(_EPMC_ITEM)
        assert "PMC" in doc.canonical_url or "5726088" in doc.canonical_url

    def test_published_at_parsed(self):
        doc = normalize_europe_pmc_result(_EPMC_ITEM)
        assert doc.published_at is not None
        assert doc.published_at.year == 2017

    def test_missing_pmcid_uses_pmid_url(self):
        item = {**_EPMC_ITEM, "pmcid": None}
        doc = normalize_europe_pmc_result(item)
        assert "MED" in doc.canonical_url or "28550024" in doc.canonical_url

    def test_missing_abstract(self):
        item = {**_EPMC_ITEM, "abstractText": None}
        doc = normalize_europe_pmc_result(item)
        assert doc.abstract_or_summary == ""

    def test_sections_not_empty(self):
        doc = normalize_europe_pmc_result(_EPMC_ITEM)
        assert len(doc.sections) >= 1

    def test_no_author_string(self):
        item = {**_EPMC_ITEM, "authorString": None}
        doc = normalize_europe_pmc_result(item)
        assert doc.authors == []

    def test_language_is_english(self):
        doc = normalize_europe_pmc_result(_EPMC_ITEM)
        assert doc.language == "en"


# ---------------------------------------------------------------------------
# PubMed
# ---------------------------------------------------------------------------

_PUBMED_XML = b"""
<PubmedArticle>
  <MedlineCitation>
    <PMID>28550024</PMID>
    <Article>
      <ArticleTitle>Chest pain and shortness of breath in cardiovascular disease</ArticleTitle>
      <Abstract>
        <AbstractText>Objective: To determine characteristics associated with chest pain.</AbstractText>
      </Abstract>
      <Journal>
        <Title>BMJ Open</Title>
      </Journal>
      <AuthorList>
        <Author>
          <LastName>Smith</LastName>
          <ForeName>John</ForeName>
        </Author>
        <Author>
          <LastName>Doe</LastName>
          <Initials>A</Initials>
        </Author>
      </AuthorList>
    </Article>
    <PubDate>
      <Year>2017</Year>
    </PubDate>
    <MeshHeadingList>
      <MeshHeading>
        <DescriptorName>Chest Pain</DescriptorName>
      </MeshHeading>
      <MeshHeading>
        <DescriptorName>Dyspnea</DescriptorName>
      </MeshHeading>
    </MeshHeadingList>
  </MedlineCitation>
  <PubmedData>
    <ArticleIdList>
      <ArticleId IdType="doi">10.1136/bmjopen-2017-015857</ArticleId>
      <ArticleId IdType="pmc">PMC5726088</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>
"""


class TestNormalizePubmed:
    def _parse(self) -> etree._Element:
        return etree.fromstring(_PUBMED_XML)

    def test_basic_fields(self):
        doc = normalize_pubmed_article(self._parse())
        assert doc.source == "pubmed"
        assert doc.pmid == "28550024"
        assert doc.title == "Chest pain and shortness of breath in cardiovascular disease"
        assert doc.journal == "BMJ Open"
        assert doc.doi == "10.1136/bmjopen-2017-015857"
        assert doc.pmcid == "PMC5726088"

    def test_abstract_extracted(self):
        doc = normalize_pubmed_article(self._parse())
        assert "chest pain" in doc.abstract_or_summary.lower()

    def test_mesh_terms_extracted(self):
        doc = normalize_pubmed_article(self._parse())
        assert "Chest Pain" in doc.mesh_terms
        assert "Dyspnea" in doc.mesh_terms

    def test_authors_extracted(self):
        doc = normalize_pubmed_article(self._parse())
        assert len(doc.authors) == 2
        assert any("Smith" in a for a in doc.authors)

    def test_published_at_year(self):
        doc = normalize_pubmed_article(self._parse())
        assert doc.published_at is not None
        assert doc.published_at.year == 2017

    def test_canonical_url_contains_pmid(self):
        doc = normalize_pubmed_article(self._parse())
        assert "28550024" in doc.canonical_url

    def test_language_is_english(self):
        doc = normalize_pubmed_article(self._parse())
        assert doc.language == "en"

    def test_sections_not_empty(self):
        doc = normalize_pubmed_article(self._parse())
        assert len(doc.sections) >= 1

    def test_no_abstract_uses_title_fallback(self):
        xml = b"""
        <PubmedArticle>
          <MedlineCitation>
            <PMID>99999</PMID>
            <Article>
              <ArticleTitle>Minimal Article</ArticleTitle>
              <Journal><Title>Test Journal</Title></Journal>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        doc = normalize_pubmed_article(etree.fromstring(xml))
        assert doc.pmid == "99999"
        assert doc.abstract_or_summary == ""
        assert len(doc.sections) >= 1  # falls back to title section
