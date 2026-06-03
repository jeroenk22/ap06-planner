"""Tests voor xlsx-parser."""

from ap06_planner.parsers.xlsx_parser import GELDIG_TABBLAD_PATROON, selecteer_tabbladen


def test_selecteer_geldige_tabbladen():
    tabs = ["13-4 Maandag", "11-4 Zaterdag", "Blad2", "Blad129"]
    geselecteerd = selecteer_tabbladen(tabs)
    assert "13-4 Maandag" in geselecteerd
    assert "11-4 Zaterdag" in geselecteerd
    assert "Blad2" not in geselecteerd
    assert "Blad129" not in geselecteerd


def test_selecteer_kleine_letters():
    tabs = ["11-5 maandag", "9-5 Zaterdag", "20-4 Maandag"]
    geselecteerd = selecteer_tabbladen(tabs)
    assert len(geselecteerd) == 3


def test_tabblad_patroon_varianten():
    geldige_tabs = [
        "13-4 Maandag",
        "11-5 maandag",
        "9-5 Zaterdag",
        "20-4 Maandag",
        "18-4 Zaterdag",
        "10-4 Vrijdag",
        "5-5 dinsdag",
        "20-5 Woensdag",
    ]
    for tab in geldige_tabs:
        assert GELDIG_TABBLAD_PATROON.search(tab), f"Verwacht geldig: {tab}"


def test_tabblad_patroon_ongeldig():
    ongeldige_tabs = ["Blad2", "Blad129", "Sheet1", "Data", "Projectnr"]
    for tab in ongeldige_tabs:
        assert not GELDIG_TABBLAD_PATROON.search(tab), f"Verwacht ongeldig: {tab}"
