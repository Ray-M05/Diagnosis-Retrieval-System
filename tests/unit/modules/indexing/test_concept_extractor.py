from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor

def test_concept_extractor_simple():
    extractor = ConceptExtractor()
    text = "El paciente presenta disnea y dolor en el pecho."
    concepts = extractor.extract(text)
    
    # Check if DISNEA and DOLOR_TORACICO are extracted
    assert "DISNEA" in concepts
    assert "DOLOR_TORACICO" in concepts
    assert len(concepts) == 2

def test_concept_extractor_no_match():
    extractor = ConceptExtractor()
    text = "Texto sin conceptos medicos."
    concepts = extractor.extract(text)
    assert len(concepts) == 0

def test_concept_extractor_normalization():
    extractor = ConceptExtractor()
    # Test normalization (capitalization, accents)
    text = "DIFICULTAD RESPIRATORIA y Fiebre."
    concepts = extractor.extract(text)
    assert "DISNEA" in concepts
    assert "FIEBRE" in concepts
