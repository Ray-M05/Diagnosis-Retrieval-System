from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor

def test_concept_extractor_simple():
    extractor = ConceptExtractor()
    text = "The patient presents dyspnea and chest pain."
    concepts = extractor.extract(text)
    
    # Check if DYSPNEA and CHEST_PAIN are extracted
    assert "DYSPNEA" in concepts
    assert "CHEST_PAIN" in concepts
    assert len(concepts) == 2

def test_concept_extractor_no_match():
    extractor = ConceptExtractor()
    text = "Text with no medical concepts."
    concepts = extractor.extract(text)
    assert len(concepts) == 0

def test_concept_extractor_normalization():
    extractor = ConceptExtractor()
    # Test normalization (capitalization, accents)
    text = "SHORTNESS BREATth and Fever."
    # Fixing typo in test text above purposefully to ensure partial or exact matching behavior
    # Note: Aho-Corasick needs exact match of "shortness of breath" or "fever". Let's give it an exact match with weird caps.
    text = "SHORTNESS OF BREATH and FEver."
    concepts = extractor.extract(text)
    assert "DYSPNEA" in concepts
    assert "FEVER" in concepts

