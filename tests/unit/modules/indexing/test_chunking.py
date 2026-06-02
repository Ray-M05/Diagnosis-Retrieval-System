import pytest
from unittest.mock import MagicMock
from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument, Content, Section, CrawlMeta
from sri_dx.modules.indexing.chunking import chunk_acquired_document, ChunkingConfig


@pytest.fixture
def mock_semantic_chunker():
    mock_instance = MagicMock()
    mock_instance.split_text.return_value = [
        (0, 49, "Contenido de la seccion 1 con sintomas respiratorios"),
        (50, 98, "y dolor toracico persistente que requiere dividirse."),
    ]
    return mock_instance

def test_chunk_acquired_document(mock_semantic_chunker):
    s1_text = (
        "Contenido de la seccion 1 con sintomas respiratorios "
        "y dolor toracico persistente que requiere dividirse."
    )
    s2_text = "Seccion breve clinicamente util con detalles suficientes para indexar."
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
                Section(heading="S1", text=s1_text),
                Section(heading="S2", text=s2_text),
            ],
            body="..."
        ),
        content_hash="hash1"
    )
    
    cfg = ChunkingConfig(max_chars=80, overlap_chars=5, min_chars=2)
    # Passed explicitly to avoid missing import try-catch issues in test env
    chunks = list(chunk_acquired_document(doc, cfg=cfg, semantic_chunker=mock_semantic_chunker))
    
    assert len(chunks) == 3 # S1 split into 2 by mock, S2 kept as 1 chunk
    
    # Verificar trazabilidad (Chunk 1 de S1)
    chunk0 = chunks[0]
    assert chunk0.doc_id == "doc1"
    assert chunk0.section_heading == "S1"
    assert chunk0.section_index == 0
    assert chunk0.chunk_index == 0
    assert chunk0.chunk_id == "doc1:0:0"
    assert chunk0.chunk_text == "Contenido de la seccion 1 con sintomas respiratorios"
    
    # Chunk 2 de S1
    chunk1 = chunks[1]
    assert chunk1.section_heading == "S1"
    assert chunk1.chunk_index == 1
    assert chunk1.chunk_text == "y dolor toracico persistente que requiere dividirse."
    
    # Verificar que S2 se incluyó intacto
    last_chunk = chunks[-1]
    assert last_chunk.section_heading == "S2"
    assert last_chunk.chunk_index == 0
    assert last_chunk.chunk_text == s2_text
    
    # Confirmar que el mock fue llamado por exceder los 20 max_chars
    mock_semantic_chunker.split_text.assert_called_once_with(s1_text)
