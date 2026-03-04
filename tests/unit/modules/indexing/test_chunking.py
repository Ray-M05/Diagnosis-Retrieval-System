import pytest
from sri_dx.core.schemas.acquired_document import AcquiredDocument, Content, Section, CrawlMeta
from sri_dx.modules.indexing.chunking import chunk_acquired_document, ChunkingConfig, _split_with_overlap

def test_split_with_overlap_basic():
    cfg = ChunkingConfig(max_chars=10, overlap_chars=2, min_chars=2)
    text = "1234567890abcdefghij" # 20 chars
    # Chunk 1: "1234567890" (0-10)
    # Chunk 2: "90abcdefgh" (8-18)
    # Chunk 3: "ghij" (16-20)
    
    pieces = _split_with_overlap(text, cfg)
    
    assert len(pieces) == 3
    assert pieces[0][2] == "1234567890"
    assert pieces[1][2] == "90abcdefgh"
    assert pieces[2][2] == "ghij"

def test_split_with_overlap_whitespace():
    cfg = ChunkingConfig(max_chars=15, overlap_chars=5, min_chars=5)
    text = "HOLA MUNDO ESTO ES UNA PRUEBA"
    # "HOLA MUNDO ESTO" (0-15)
    # Próximo empieza en 15-5=10 -> " ESTO ES UNA PRUE"
    # Pero intenta no cortar palabra...
    
    pieces = _split_with_overlap(text, cfg)
    assert len(pieces) > 1
    for start, end, chunk in pieces:
        assert len(chunk) >= cfg.min_chars
        assert text[start:end].strip() == chunk

def test_chunk_acquired_document():
    doc = AcquiredDocument(
        doc_id="doc1",
        url="http://test.com",
        source_domain="test.com",
        fetched_at="2024-01-01T00:00:00Z",
        crawl=CrawlMeta(depth=1, parent_url=None, seed_id="s1", seed_group="g1"),
        content=Content(
            mime_type="text/html",
            title="Test",
            sections=[
                Section(heading="S1", text="Contenido de la sección 1 que es largo."),
                Section(heading="S2", text="Corto."),
            ],
            body="..."
        ),
        content_hash="hash1"
    )
    
    cfg = ChunkingConfig(max_chars=20, overlap_chars=5, min_chars=2)
    chunks = list(chunk_acquired_document(doc, cfg=cfg))
    
    assert len(chunks) >= 3 # S1 se divide, S2 es un chunk
    
    # Verificar trazabilidad
    chunk0 = chunks[0]
    assert chunk0.doc_id == "doc1"
    assert chunk0.section_heading == "S1"
    assert chunk0.section_index == 0
    assert chunk0.chunk_index == 0
    assert chunk0.chunk_id == "doc1:0:0"
    
    # Verificar que S2 se incluyó
    last_chunk = chunks[-1]
    assert last_chunk.section_heading == "S2"
    assert last_chunk.chunk_text == "Corto."
