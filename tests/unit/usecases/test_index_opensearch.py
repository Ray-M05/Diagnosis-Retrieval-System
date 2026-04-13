import pytest
from unittest.mock import MagicMock, call

from sri_dx.core.ports.acquisition.document_source import DocumentSourcePort
from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument, Content, CrawlMeta, PageMeta
from sri_dx.core.ports.acquisition.manifest_store import ManifestStorePort, ManifestEntry
from sri_dx.adapters.stores.opensearch_sink import OpenSearchIndexSink
from sri_dx.usecases.indexing.index_opensearch import IndexOpenSearchUseCase
from sri_dx.modules.indexing.pipeline_version import PIPELINE_VERSION


@pytest.fixture
def mock_source():
    return MagicMock(spec=DocumentSourcePort)


@pytest.fixture
def mock_sink():
    # Also mock the client inside OpenSearchIndexSink
    sink = MagicMock(spec=OpenSearchIndexSink)
    sink.client = MagicMock()
    sink.client.indices = MagicMock()
    # Mock cfg as well 
    sink.cfg = MagicMock()
    sink.cfg.index_name = "test_index"
    return sink


@pytest.fixture
def mock_manifest():
    return MagicMock(spec=ManifestStorePort)


def _create_fake_acquired_doc(doc_id: str, body: str, ext_hash: str = None) -> AcquiredDocument:
    return AcquiredDocument(
        doc_id=doc_id,
        url=f"http://example.com/{doc_id}",
        source_domain="example.com",
        fetched_at="2026-03-01T00:00:00Z",
        crawl=CrawlMeta(depth=0, parent_url=None, seed_id="seed1", seed_group="test_group"),
        content=Content(mime_type="text/html", title=f"Title {doc_id}", sections=[], body=body),
        page_meta=PageMeta(),
        content_hash=ext_hash
    )


def test_index_opensearch_all_new(mock_source, mock_sink, mock_manifest, monkeypatch):
    """
    Verifica que si los documentos no están en el manifest, se indexan todos.
    """
    # Setup mocks
    mock_source.iter_documents.return_value = [
        _create_fake_acquired_doc("doc_1", "body 1", "hash_1"),
        _create_fake_acquired_doc("doc_2", "body 2", "hash_2")
    ]
    mock_manifest.get.return_value = None
    mock_sink.bulk_upsert.return_value = ["doc_1", "doc_2"]

    # Mock ConceptExtractor para no hacer el extractor real
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = []
    monkeypatch.setattr("sri_dx.usecases.indexing.index_opensearch.ConceptExtractor", lambda: mock_extractor)

    uc = IndexOpenSearchUseCase(
        source=mock_source, 
        sink=mock_sink, 
        manifest=mock_manifest, 
        batch_size=500
    )
    
    stats = uc.run(refresh=False)
    
    # Assertions
    assert stats["docs_seen"] == 2
    assert stats["docs_skipped_same_hash"] == 0
    assert stats["docs_sent_to_index"] == 2
    assert stats["docs_indexed_ok"] == 2
    
    mock_sink.bulk_upsert.assert_called_once()
    mock_manifest.upsert_many.assert_called_once()


def test_index_opensearch_all_skipped(mock_source, mock_sink, mock_manifest, monkeypatch):
    """
    Verifica que si todos los documentos están en el manifest con el mismo hash y pipeline, se saltan.
    """
    # Setup mocks
    mock_source.iter_documents.return_value = [
        _create_fake_acquired_doc("doc_1", "body 1", "hash_1"),
    ]
    
    # Manifest devuelve que ya existe y coincide
    mock_manifest.get.return_value = ManifestEntry(doc_id="doc_1", content_hash="hash_1", pipeline_version=PIPELINE_VERSION)

    # Mock ConceptExtractor
    mock_extractor = MagicMock()
    monkeypatch.setattr("sri_dx.usecases.indexing.index_opensearch.ConceptExtractor", lambda: mock_extractor)

    uc = IndexOpenSearchUseCase(
        source=mock_source, 
        sink=mock_sink, 
        manifest=mock_manifest, 
        batch_size=500
    )
    
    stats = uc.run()
    
    # Assertions
    assert stats["docs_seen"] == 1
    assert stats["docs_skipped_same_hash"] == 1
    assert stats["docs_sent_to_index"] == 0
    assert stats["docs_indexed_ok"] == 0
    
    # bulk_upsert no se debería haber llamado
    mock_sink.bulk_upsert.assert_not_called()


def test_index_opensearch_hash_changed(mock_source, mock_sink, mock_manifest, monkeypatch):
    """
    Verifica que si un documento está en el manifest pero el hash cambió, se reindexa.
    """
    # Setup mocks
    mock_source.iter_documents.return_value = [
        _create_fake_acquired_doc("doc_1", "body 1", "hash_new"),
    ]
    
    # Manifest devuelve un hash distinto
    mock_manifest.get.return_value = ManifestEntry(doc_id="doc_1", content_hash="hash_old", pipeline_version=PIPELINE_VERSION)
    
    mock_sink.bulk_upsert.return_value = ["doc_1"]

    # Mock ConceptExtractor
    mock_extractor = MagicMock()
    monkeypatch.setattr("sri_dx.usecases.indexing.index_opensearch.ConceptExtractor", lambda: mock_extractor)

    uc = IndexOpenSearchUseCase(
        source=mock_source, 
        sink=mock_sink, 
        manifest=mock_manifest, 
        batch_size=500
    )
    
    stats = uc.run()
    
    assert stats["docs_seen"] == 1
    assert stats["docs_skipped_same_hash"] == 0
    assert stats["docs_sent_to_index"] == 1
    assert stats["docs_indexed_ok"] == 1
    
    mock_sink.bulk_upsert.assert_called_once()


def test_index_opensearch_pipeline_version_changed(mock_source, mock_sink, mock_manifest, monkeypatch):
    """
    Verifica que si la versión del pipeline cambia, reindexa aunque el hash del contenido sea el mismo.
    """
    # Setup mocks
    mock_source.iter_documents.return_value = [
        _create_fake_acquired_doc("doc_1", "body 1", "hash_1"),
    ]
    
    # Manifest devuelve mismo hash pero pipeline viejo
    mock_manifest.get.return_value = ManifestEntry(doc_id="doc_1", content_hash="hash_1", pipeline_version="old_version")
    
    mock_sink.bulk_upsert.return_value = ["doc_1"]

    # Mock ConceptExtractor
    mock_extractor = MagicMock()
    monkeypatch.setattr("sri_dx.usecases.indexing.index_opensearch.ConceptExtractor", lambda: mock_extractor)

    uc = IndexOpenSearchUseCase(
        source=mock_source, 
        sink=mock_sink, 
        manifest=mock_manifest, 
        batch_size=500
    )
    
    stats = uc.run()
    
    assert stats["docs_seen"] == 1
    assert stats["docs_skipped_same_hash"] == 0
    assert stats["docs_sent_to_index"] == 1
    assert stats["docs_indexed_ok"] == 1
