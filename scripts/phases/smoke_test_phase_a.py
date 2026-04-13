from pathlib import Path

from sri_dx.adapters.document_sources.jsonl_source import JsonlDocumentSource
from sri_dx.usecases.index_corpus import IndexCorpusPhaseAUseCase
from sri_dx.modules.indexing.prepare import prepare_index_document

paths = [
    Path("data/processed/docs_html.jsonl"),
    Path("data/processed/docs_pdf.jsonl"),
]

# Creamos el source pasándole las rutas
# Si los archivos no existen, simplemente estará vacío en Fase A, o lanzará error según cómo lo usemos
source = JsonlDocumentSource(paths=paths)

print("Iniciando validación manual de primeros documentos...")
ok = 0
N = 20

try:
    for i, doc in enumerate(source.iter_documents(), start=1):
        idx = prepare_index_document(doc)
        
        # Aserciones end to end
        assert idx.doc_id and idx.url and idx.source_domain
        assert idx.mime_type in ("text/html", "application/pdf")
        assert isinstance(idx.body, str) and len(idx.body) > 0
        assert isinstance(idx.sections_text, str)
        assert isinstance(idx.content_hash, str) and len(idx.content_hash) >= 32
        
        ok += 1
        if ok >= N:
            break

    print(f"OK: {ok} documentos leídos y preparados satisfactoriamente (límite probados: {N})")
except Exception as e:
    print(f"Ocurrió un error leyendo o preparando los docs. Es probable que no existan los JSONL de datos.")
    print(e)
    
print("\nCorriendo caso de uso global:")
uc = IndexCorpusPhaseAUseCase(source=source)

try:
    stats = uc.run()
    print("=== STATS FASE A ===")
    print(stats)
except Exception as e:
    print(f"No se pudieron generar las estadísticas. {e}")
