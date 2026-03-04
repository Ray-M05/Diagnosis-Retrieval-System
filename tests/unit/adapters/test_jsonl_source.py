import tempfile
from pathlib import Path
import json
import pytest

from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource, InvalidDocumentError


def test_jsonl_happy_path_parsing():
    """
    Verifica que el JsonlDocumentSource lee y parsea correctamente 
    un AcquiredDocument desde un archivo válido.
    """
    line = {
        "doc_id": "doc_test_01",
        "url": "https://example.org/test",
        "source_domain": "example.org",
        "fetched_at": "2026-02-26T05:12:10Z",
        "crawl": {
            "depth": 0, 
            "parent_url": None, 
            "seed_id": "seed_01", 
            "seed_group": "guidelines"
        },
        "content": {
            "mime_type": "text/html",
            "title": "Test Title",
            "sections": [
                {"heading": "H1", "text": "Section 1 content"}
            ],
            "body": "hello world from test"
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_docs.jsonl"
        test_file.write_text(json.dumps(line) + "\n", encoding="utf-8")

        # Configurar Source y extraer
        source = JsonlDocumentSource(paths=[test_file])
        docs = list(source.iter_documents())
        
        assert len(docs) == 1, "Debería haber leído un documento"
        doc = docs[0]
        
        # Validaciones de parsing AcquiredDocument
        assert doc.doc_id == "doc_test_01"
        assert doc.content.mime_type == "text/html"


def test_jsonl_missing_required_field_fails():
    """
    Asegura que nuestro adaptador levante InvalidDocumentError 
    al enfrentarse a datos sin un campo requerido según nuestro esquema.
    """
    bad_line = {
        "doc_id": "doc_test_bad"
        # Falta todo lo demás: url, content, crawl...
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "bad_docs.jsonl"
        test_file.write_text(json.dumps(bad_line) + "\n", encoding="utf-8")

        source = JsonlDocumentSource(paths=[test_file])
        
        with pytest.raises(InvalidDocumentError):
            # Forzar la iteración donde ocurrirá el fallo
            list(source.iter_documents())
