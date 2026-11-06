from lakselus import livscyklus


def test_html_viser_ugens_tal_og_fire_trin():
    h = livscyklus.html(uge=44, km_dag=7.2, fast=0.11, mob=0.34, hun=0.21, temp=9.6)
    assert h.count('class="lc-trin"') == 4
    assert h.count('class="lc-larve"') == 10  # den animerede scene
    assert "week 44" in h and "this week" not in h
    for tekst in ("7 km a day", "about 35 km", "0.11", "0.34", "0.21", "about 10 °C", "0.5 adult females"):
        assert tekst in h
    # Hunlusens tal farves efter niveauet (0,21 er mellem 0,2 og 0,5)
    assert livscyklus.LUS_FARVER["mellem"] in h


def test_html_har_ingen_tomme_linjer():
    # Streamlit-markdown afbryder HTML ved en tom linje, så alt skal hænge sammen.
    assert "\n\n" not in livscyklus.html(44, 5, 0.1, 0.2, 0.3, 8)
