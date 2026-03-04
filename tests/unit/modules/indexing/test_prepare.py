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
