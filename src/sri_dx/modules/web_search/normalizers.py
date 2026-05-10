"""
Converts raw API responses (XML / JSON) from MedlinePlus, Europe PMC and
PubMed into the unified :class:`ExternalApiDocument` format.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from lxml import etree

from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.modules.acquisition.urls import normalize_url
from sri_dx.modules.web_search.schemas import ExternalApiDocument

logger = logging.getLogger(__name__)


def _sha1_text(text: str) -> str:
    """Return the full SHA-1 hex digest of a UTF-8 string."""
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _parse_year(raw: Any) -> datetime | None:
    """Parse a year string/int into a UTC-aware datetime (Jan 1st)."""
    if not raw:
        return None
    try:
        year = int(str(raw).strip())
        return datetime(year, 1, 1, tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _parse_authors_from_string(author_string: str | None) -> list[str]:
    """
    Split an author string like ``"Smith J, Doe A, ..."`` into a list.
    Returns an empty list when the input is None or empty.
    """
    if not author_string:
        return []
    return [a.strip() for a in author_string.split(",") if a.strip()]


def _parse_pubmed_authors(article_xml: etree._Element) -> list[str]:
    """Extract author names from a PubMed PubmedArticle XML element."""
    authors: list[str] = []
    for author in article_xml.findall(".//Author"):
        last = author.findtext("LastName") or ""
        fore = author.findtext("ForeName") or author.findtext("Initials") or ""
        name = f"{last} {fore}".strip()
        if name:
            authors.append(name)
    return authors


def _xml_text(element: etree._Element, xpath: str) -> str:
    """Return the text of the first matching element or empty string."""
    found = element.find(xpath)
    return (found.text or "").strip() if found is not None else ""


def _xml_texts(element: etree._Element, xpath: str) -> list[str]:
    """Return the text of all matching elements (non-empty only)."""
    return [
        (el.text or "").strip()
        for el in element.findall(xpath)
        if (el.text or "").strip()
    ]


def _find_article_id(article_xml: etree._Element, id_type: str) -> str | None:
    """Find ArticleId of a given type (doi, pmc, pubmed, …) in PubMed XML."""
    for aid in article_xml.findall(".//ArticleId"):
        if (aid.get("IdType") or "").lower() == id_type.lower():
            return (aid.text or "").strip() or None
    return None


def _section(heading: str, text: str) -> Section | None:
    """Return a Section only when text is non-empty."""
    t = (text or "").strip()
    return Section(heading=heading, text=t) if t else None


# MedlinePlus

def _medlineplus_get_content(doc_el: etree._Element, name: str) -> str:
    """Return the text of <content name='name'> inside a MedlinePlus document."""
    for el in doc_el.findall("content"):
        if el.get("name") == name:
            return (el.text or "").strip()
    return ""


def _medlineplus_get_all_content(doc_el: etree._Element, name: str) -> list[str]:
    return [
        (el.text or "").strip()
        for el in doc_el.findall("content")
        if el.get("name") == name and (el.text or "").strip()
    ]


def normalize_medlineplus_document(xml_doc: etree._Element) -> ExternalApiDocument:
    """
    Convert a MedlinePlus ``<document>`` XML element to :class:`ExternalApiDocument`.

    Parameters
    ----------
    xml_doc:
        An lxml element representing a single ``<document>`` in the
        ``<nlmSearchResult>`` response.
    """
    url = normalize_url(xml_doc.get("url", ""))
    title = _medlineplus_get_content(xml_doc, "title") or "MedlinePlus Health Topic"
    summary = (
        _medlineplus_get_content(xml_doc, "FullSummary")
        or _medlineplus_get_content(xml_doc, "snippet")
        or ""
    )
    snippet = _medlineplus_get_content(xml_doc, "snippet")
    mesh_terms = _medlineplus_get_all_content(xml_doc, "mesh")

    sections: list[Section] = []
    for s in [
        _section("Summary", summary),
        _section("Search snippet", snippet),
        _section("MeSH terms", ", ".join(mesh_terms)),
    ]:
        if s:
            sections.append(s)

    if not sections:
        sections = [Section(heading="Summary", text=title)]

    return ExternalApiDocument(
        source="medlineplus",
        external_id=_sha1_text(url),
        canonical_url=url,
        title=title,
        abstract_or_summary=summary,
        sections=sections,
        language="en",
        authors=["National Library of Medicine"],
        mesh_terms=mesh_terms,
        raw=etree.tostring(xml_doc, encoding="unicode"),
    )


# Europe PMC

def normalize_europe_pmc_result(item: dict) -> ExternalApiDocument:
    """
    Convert a single result dict from the Europe PMC JSON API to
    :class:`ExternalApiDocument`.
    """
    pmid: str | None = item.get("pmid") or None
    pmcid: str | None = item.get("pmcid") or None
    doi: str | None = item.get("doi") or None
    title: str = item.get("title") or "Untitled Europe PMC record"
    abstract: str = item.get("abstractText") or ""
    journal: str | None = item.get("journalTitle") or None
    pub_year: str | None = item.get("pubYear") or None
    author_string: str | None = item.get("authorString") or None

    if pmcid:
        canonical_url = f"https://europepmc.org/article/PMC/{pmcid.replace('PMC', '')}"
    elif pmid:
        canonical_url = f"https://europepmc.org/article/MED/{pmid}"
    elif doi:
        canonical_url = f"https://europepmc.org/article/DOI/{doi}"
    else:
        canonical_url = (
            f"https://europepmc.org/article/{item.get('source', 'UNK')}/{item.get('id', '')}"
        )

    canonical_url = normalize_url(canonical_url)

    sections: list[Section] = []
    for s in [
        _section("Abstract", abstract),
        _section("Journal", journal or ""),
        _section(
            "Publication metadata",
            f"Year: {pub_year or ''}; DOI: {doi or ''}; PMID: {pmid or ''}; PMCID: {pmcid or ''}",
        ),
    ]:
        if s:
            sections.append(s)

    if not sections:
        sections = [Section(heading="Abstract", text=title)]

    return ExternalApiDocument(
        source="europe_pmc",
        external_id=pmcid or pmid or doi or item.get("id", ""),
        canonical_url=canonical_url,
        title=title,
        abstract_or_summary=abstract,
        sections=sections,
        language="en",
        published_at=_parse_year(pub_year),
        authors=_parse_authors_from_string(author_string),
        journal=journal,
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        raw=item,
    )


# PubMed

def normalize_pubmed_article(article_xml: etree._Element) -> ExternalApiDocument:
    """
    Convert a PubMed ``<PubmedArticle>`` XML element to
    :class:`ExternalApiDocument`.
    """
    pmid: str | None = _xml_text(article_xml, ".//PMID") or None
    title: str = _xml_text(article_xml, ".//ArticleTitle") or "Untitled PubMed article"
    abstract_parts: list[str] = _xml_texts(article_xml, ".//AbstractText")
    abstract: str = "\n".join(abstract_parts)
    journal: str | None = _xml_text(article_xml, ".//Journal/Title") or None
    year: str | None = _xml_text(article_xml, ".//PubDate/Year") or None
    doi: str | None = _find_article_id(article_xml, "doi")
    pmcid: str | None = _find_article_id(article_xml, "pmc")
    mesh_terms: list[str] = _xml_texts(article_xml, ".//MeshHeading/DescriptorName")
    authors: list[str] = _parse_pubmed_authors(article_xml)

    canonical_url = normalize_url(f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

    sections: list[Section] = []
    for s in [
        _section("Abstract", abstract),
        _section("MeSH terms", ", ".join(mesh_terms)),
        _section("Journal", journal or ""),
        _section(
            "Publication metadata",
            f"PMID: {pmid or ''}; DOI: {doi or ''}; PMCID: {pmcid or ''}; Year: {year or ''}",
        ),
    ]:
        if s:
            sections.append(s)

    if not sections:
        sections = [Section(heading="Abstract", text=title)]

    return ExternalApiDocument(
        source="pubmed",
        external_id=pmid or "",
        canonical_url=canonical_url,
        title=title,
        abstract_or_summary=abstract,
        sections=sections,
        language="en",
        published_at=_parse_year(year),
        authors=authors,
        journal=journal,
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        mesh_terms=mesh_terms,
        raw=etree.tostring(article_xml, encoding="unicode"),
    )
