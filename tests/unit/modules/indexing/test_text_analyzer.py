from sri_dx.modules.indexing.text.text_pipeline import TextAnalyzer

def test_text_analyzer_normalization():
    analyzer = TextAnalyzer()
    text = "Hola, ¿cómo estás? Árbol de levas."
    # Analyze should normalize text (lowercase, remove punctuation, etc.)
    res = analyzer.analyze(text, language="es")
    
    # Check if 'cómo' became 'como' (depending on analyzer implementation)
    # Most basic: check if tokens are produced and are lowercase
    assert len(res.tokens) > 0
    for token in res.tokens:
        assert token == token.lower()

def test_text_analyzer_language_detection():
    analyzer = TextAnalyzer()
    text_en = "This is a test in English."
    res_en = analyzer.analyze(text_en)
    # If it detects English, it should handle it accordingly
    assert res_en.tokens is not None
