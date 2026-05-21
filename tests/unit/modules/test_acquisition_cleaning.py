from sri_dx.modules.acquisition.cleaning import clean_text


def test_clean_text_strips_html_markup_and_entities():
    raw = '<p><span class="qt0">Cough</span> &amp; wheezing</p><ul><li>Asthma</li></ul>'

    assert clean_text(raw) == "Cough & wheezing\nAsthma"
