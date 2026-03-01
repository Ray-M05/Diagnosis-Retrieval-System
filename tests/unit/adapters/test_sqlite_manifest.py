import sqlite3
import tempfile
from pathlib import Path
import pytest

from sri_dx.core.ports.manifest_store import ManifestEntry
from sri_dx.adapters.stores.sqlite_manifest import SqliteManifestStore


@pytest.fixture
def temp_manifest_store():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_manifest.sqlite"
        store = SqliteManifestStore(path=db_path)
        yield store


def test_sqlite_manifest_initialization(temp_manifest_store):
    """
    Verifica que el store inicializa la tabla y el índice correctamente.
    """
    store = temp_manifest_store
    
    assert store.path.exists()
    
    with store._connect() as con:
        # Verificar la existencia de la tabla
        table_info = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='manifest'"
        ).fetchone()
        assert table_info is not None
        
        # Verificar la existencia del índice
        index_info = con.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_manifest_hash'"
        ).fetchone()
        assert index_info is not None


def test_sqlite_manifest_upsert_and_get(temp_manifest_store):
    """
    Verifica que podemos insertar (upsert) y recuperar un registro simple.
    """
    store = temp_manifest_store
    
    entry = ManifestEntry(
        doc_id="doc_1",
        content_hash="hash_1",
        pipeline_version="v1"
    )
    
    # Upsert
    store.upsert_many([entry])
    
    # Get
    retrieved = store.get("doc_1")
    assert retrieved is not None
    assert retrieved.doc_id == "doc_1"
    assert retrieved.content_hash == "hash_1"
    assert retrieved.pipeline_version == "v1"


def test_sqlite_manifest_get_not_found(temp_manifest_store):
    """
    Verifica que devuelva None si el documento no existe.
    """
    store = temp_manifest_store
    retrieved = store.get("non_existent_doc")
    assert retrieved is None


def test_sqlite_manifest_upsert_updates_existing(temp_manifest_store):
    """
    Verifica que un upsert con el mismo doc_id actualiza los demás campos.
    """
    store = temp_manifest_store
    
    entry1 = ManifestEntry(doc_id="doc_1", content_hash="hash_old", pipeline_version="v1")
    store.upsert_many([entry1])
    
    entry2 = ManifestEntry(doc_id="doc_1", content_hash="hash_new", pipeline_version="v2")
    store.upsert_many([entry2])
    
    retrieved = store.get("doc_1")
    assert retrieved is not None
    assert retrieved.content_hash == "hash_new"
    assert retrieved.pipeline_version == "v2"


def test_sqlite_manifest_get_many(temp_manifest_store):
    """
    Verifica qye get_many devuelva múltiples documentos y omita los que no existen.
    """
    store = temp_manifest_store
    
    entries = [
        ManifestEntry(doc_id="doc_1", content_hash="hash_1", pipeline_version="v1"),
        ManifestEntry(doc_id="doc_2", content_hash="hash_2", pipeline_version="v1"),
        ManifestEntry(doc_id="doc_3", content_hash="hash_3", pipeline_version="v2"),
    ]
    store.upsert_many(entries)
    
    result = store.get_many(["doc_1", "doc_3", "doc_4"])
    
    assert len(result) == 2
    assert "doc_1" in result
    assert "doc_3" in result
    assert "doc_4" not in result
    assert result["doc_1"].content_hash == "hash_1"
    assert result["doc_3"].pipeline_version == "v2"


def test_sqlite_manifest_empty_lists(temp_manifest_store):
    """
    Verifica el comportamiento seguro de listas vacías.
    """
    store = temp_manifest_store
    
    # No debería explotar
    store.upsert_many([])
    
    result = store.get_many([])
    assert result == {}
