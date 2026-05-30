from sri_dx.modules.indexing.prepare import prepare_index_document
from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument, CrawlMeta, Content, Section

def test_prepare_index_document():
    """
    Verifica que la funcionalidad del prepare_index_document deriva 
    correctamente en un IndexDocument y genera el content_hash.
    """
    acquired_doc = AcquiredDocument(
        doc_id="doc_test_01",
        url="https://example.org/test",
        source_domain="example.org",
        fetched_at="2026-02-26T05:12:10Z",
        crawl=CrawlMeta(
            depth=0, 
            parent_url=None, 
            seed_id="seed_01", 
            seed_group="guidelines"
        ),
        content=Content(
            mime_type="text/html",
            title="Test Title",
            sections=[
                Section(heading="H1", text="Section 1 content")
            ],
            body="hello world from test"
        )
    )
    
    idx_doc = prepare_index_document(acquired_doc)
    
    # Validar derivación de campos de IndexDocument
    assert idx_doc.doc_id == "doc_test_01"
    assert idx_doc.title == "Test Title"
    assert len(idx_doc.sections_text) > 0
    assert idx_doc.word_count > 0
    assert idx_doc.content_hash is not None
    assert len(idx_doc.content_hash) >= 32, "El hash debe de ser al menos de 32 caracteres (sha256)"


def _doc(*, title, sections, url="https://example.org/path", domain="example.org"):
    return AcquiredDocument(
        doc_id="doc_x",
        url=url,
        source_domain=domain,
        fetched_at="2026-02-26T05:12:10Z",
        crawl=CrawlMeta(depth=0, parent_url=None, seed_id="s", seed_group="g"),
        content=Content(mime_type="text/html", title=title, sections=sections, body="body text"),
    )


def test_title_falls_back_to_section_heading_when_missing():
    doc = _doc(title=None, sections=[Section(heading="Asthma", text="...")])
    assert prepare_index_document(doc).title == "Asthma"


def test_title_falls_back_to_url_slug_when_no_usable_heading():
    doc = _doc(
        title="   ",
        sections=[Section(heading="main", text="...")],
        url="https://www.mayoclinic.org/diseases-conditions/asthma/symptoms-causes/syc-20369653",
    )
    # "main" heading and noise slug are skipped → meaningful slug used.
    assert prepare_index_document(doc).title == "Asthma"


def test_title_never_empty():
    doc = _doc(title=None, sections=[Section(heading="main", text="...")], url="", domain="")
    assert prepare_index_document(doc).title  # non-empty fallback (humanized doc id)
