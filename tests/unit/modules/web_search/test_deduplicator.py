"""Unit tests — ApiDocumentDeduplicator."""
from __future__ import annotations

import pytest

from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.modules.web_search.deduplicator import ApiDocumentDeduplicator, identity_keys
from sri_dx.modules.web_search.schemas import ExternalApiDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ext(
    source: str = "pubmed",
    pmid: str | None = None,
    pmcid: str | None = None,
    doi: str | None = None,
    url: str = "https://example.com/doc1",
) -> ExternalApiDocument:
    return ExternalApiDocument(
        source=source,
        external_id=pmid or url,
        canonical_url=url,
        title="Test Document",
        abstract_or_summary="Abstract text.",
        sections=[Section(heading="Abstract", text="Abstract text.")],
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
    )


def _acq(content_hash: str = "hash001") -> dict:
    return {
        "doc_id": "doc_abc",
        "url": "https://example.com/doc1",
        "content_hash": content_hash,
    }


# ---------------------------------------------------------------------------
# identity_keys
# ---------------------------------------------------------------------------

class TestIdentityKeys:
    def test_all_identifiers(self):
        ext = _ext(pmid="111", pmcid="PMC222", doi="10.1234/test", url="https://a.com/b")
        keys = identity_keys(ext)
        assert "pmid:111" in keys
        assert "pmcid:PMC222" in keys
        assert "doi:10.1234/test" in keys
        assert "url:https://a.com/b" in keys

    def test_only_url(self):
        ext = _ext(url="https://medlineplus.gov/x.html")
        keys = identity_keys(ext)
        assert any("url:" in k for k in keys)

    def test_doi_lowercased(self):
        ext = _ext(doi="10.1234/UPPERCASE")
        keys = identity_keys(ext)
        assert "doi:10.1234/uppercase" in keys

    def test_empty_fields_excluded(self):
        ext = _ext(pmid=None, pmcid=None, doi=None, url="https://a.com/b")
        keys = identity_keys(ext)
        assert not any("pmid:" in k for k in keys)
        assert not any("pmcid:" in k for k in keys)


# ---------------------------------------------------------------------------
# ApiDocumentDeduplicator
# ---------------------------------------------------------------------------

class TestApiDocumentDeduplicator:
    def test_new_document_kept(self):
        dup = ApiDocumentDeduplicator()
        ext = _ext(pmid="123", url="https://pubmed.ncbi.nlm.nih.gov/123/")
        acq = _acq("unique_hash_001")
        assert dup.should_keep(ext, acq) is True

    def test_duplicate_by_pmid_in_existing(self):
        dup = ApiDocumentDeduplicator(
            existing_identity_keys={"pmid:123"}
        )
        ext = _ext(pmid="123", url="https://pubmed.ncbi.nlm.nih.gov/123/")
        assert dup.should_keep(ext, _acq()) is False

    def test_duplicate_by_content_hash_in_existing(self):
        dup = ApiDocumentDeduplicator(
            existing_content_hashes={"hash_existing"}
        )
        ext = _ext(url="https://a.com/new_url")
        assert dup.should_keep(ext, _acq("hash_existing")) is False

    def test_session_dedup_by_pmid(self):
        dup = ApiDocumentDeduplicator()
        ext1 = _ext(pmid="999", url="https://pubmed.ncbi.nlm.nih.gov/999/")
        ext2 = _ext(source="europe_pmc", pmid="999", url="https://europepmc.org/article/MED/999")

        acq1 = _acq("hash_a")
        acq2 = _acq("hash_b")

        assert dup.should_keep(ext1, acq1) is True   # first: kept
        assert dup.should_keep(ext2, acq2) is False  # second: PMID already seen

    def test_session_dedup_by_content_hash(self):
        dup = ApiDocumentDeduplicator()
        ext1 = _ext(url="https://a.com/doc1")
        ext2 = _ext(url="https://b.com/doc2")  # different URL, same content

        acq = _acq("shared_hash")

        assert dup.should_keep(ext1, acq) is True   # first: kept
        assert dup.should_keep(ext2, acq) is False  # second: same content_hash

    def test_filter_returns_only_kept(self):
        dup = ApiDocumentDeduplicator(existing_identity_keys={"pmid:111"})

        pairs = [
            (_ext(pmid="111", url="https://a.com/1"), _acq("h1")),  # duplicate
            (_ext(pmid="222", url="https://a.com/2"), _acq("h2")),  # new
            (_ext(pmid="333", url="https://a.com/3"), _acq("h3")),  # new
        ]
        kept = dup.filter(pairs)
        assert len(kept) == 2
        pmids_kept = {ext.pmid for ext, _ in kept}
        assert "222" in pmids_kept
        assert "333" in pmids_kept
        assert "111" not in pmids_kept

    def test_filter_empty_input(self):
        dup = ApiDocumentDeduplicator()
        assert dup.filter([]) == []

    def test_all_new_documents_pass(self):
        dup = ApiDocumentDeduplicator()
        pairs = [
            (_ext(pmid=str(i), url=f"https://a.com/{i}"), _acq(f"hash_{i}"))
            for i in range(5)
        ]
        kept = dup.filter(pairs)
        assert len(kept) == 5
