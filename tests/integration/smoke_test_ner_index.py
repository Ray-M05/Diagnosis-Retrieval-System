# tests/integration/smoke_test_ner_index.py
from pprint import pprint

from sri_dx.core.schemas.acquisition.acquired_document import AcquiredDocument, Content, Section, CrawlMeta, PageMeta
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor
from sri_dx.adapters.indexing.ner_tagger_adapter import BiomedicalNERTaggerAdapter
from sri_dx.modules.indexing.prepare import prepare_index_document
from sri_dx.modules.indexing.chunking import chunk_acquired_document

def run_smoke_test():
    # 1. Dependencias
    concept_extractor = ConceptExtractor()
    ner_tagger = BiomedicalNERTaggerAdapter()

    # 2. Documento de prueba en Inglés
    doc = AcquiredDocument(
        doc_id="smoke_test_doc_001",
        url="http://example.com/medical_case",
        source_domain="example.com",
        fetched_at="2026-03-08T00:00:00Z",
        page_meta=PageMeta(language="en", published_at=None, updated_at=None, author=None),
        crawl=CrawlMeta(depth=1, parent_url=None, seed_id="seed1", seed_group="group1"),
        content=Content(
            mime_type="text/plain",
            title="Patient Case 1",
            body="Patient exhibits severe dyspnea and presents with tachycardia after exposure.",
            sections=[
                Section(heading="Symptoms", text="Patient exhibits severe dyspnea and presents with tachycardia after exposure. Also complains of chest pain.")
            ]
        ),
        content_hash="mockhash"
    )

    print("=== TESTING DOC LEVEL ===")
    index_doc = prepare_index_document(doc, concept_extractor=concept_extractor, ner_tagger=ner_tagger)
    print(f"Doc ID: {index_doc.doc_id}")
    print(f"Concept IDs: {index_doc.concept_ids}")
    print(f"NER Entities ({len(index_doc.ner_entities)}):")
    for entity in index_doc.ner_entities:
        print(f"  - [{entity.label}] '{entity.text}' (Score: {entity.score:.2f})")

    print("\n=== TESTING CHUNK LEVEL ===")
    chunks = list(chunk_acquired_document(doc, concept_extractor=concept_extractor, ner_tagger=ner_tagger))
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i} ID: {chunk.chunk_id}")
        print(f"Chunk Text: '{chunk.chunk_text}'")
        print(f"Concept IDs: {chunk.concept_ids}")
        print(f"NER Entities ({len(chunk.ner_entities)}):")
        for entity in chunk.ner_entities:
            print(f"  - [{entity.label}] '{entity.text}' (Score: {entity.score:.2f})")

if __name__ == "__main__":
    run_smoke_test()
