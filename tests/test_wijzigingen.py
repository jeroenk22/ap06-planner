"""Tests voor wijzigingen-verwerking."""

import pytest
from ap06_planner.parsers.wijzigingen import verwerk_wijzigingen
from ap06_planner.parsers.tijdvenster import parse_tijdvenster


def test_geen_wijzigingen():
    resultaat = verwerk_wijzigingen(None)
    assert resultaat.tijdvervang is None
    assert resultaat.negeer is False


def test_tijdvervang_hoofdletter():
    resultaat = verwerk_wijzigingen("Naar 12-18")
    assert resultaat.tijdvervang == ("12:00", "18:00")


def test_tijdvervang_kleine_letter():
    resultaat = verwerk_wijzigingen("naar 8-10")
    assert resultaat.tijdvervang == ("08:00", "10:00")


def test_tijdvervang_met_punt():
    resultaat = verwerk_wijzigingen("naar 10.30-12.30")
    assert resultaat.tijdvervang == ("10:30", "12:30")


def test_persoon_na():
    resultaat = verwerk_wijzigingen("Anouk na 12")
    assert resultaat.persoon_start_na == "12:00"
    assert resultaat.persoon_eind_voor is None


def test_persoon_tot():
    resultaat = verwerk_wijzigingen("Tom tot 12")
    assert resultaat.persoon_eind_voor == "12:00"
    assert resultaat.persoon_start_na is None


def test_persoon_hele_dag():
    resultaat = verwerk_wijzigingen("Danielle hele dag")
    assert resultaat.persoon_hele_dag is True


def test_negeer_dagblok():
    resultaat = verwerk_wijzigingen("dagblok")
    assert resultaat.negeer is True


def test_negeer_ochtendblok():
    resultaat = verwerk_wijzigingen("ochtendblok")
    assert resultaat.negeer is True


def test_vervallen_niet_in_wijzigingen():
    # "vervallen" wordt al gefilterd door xlsx_parser, niet door wijzigingen-parser
    resultaat = verwerk_wijzigingen("vervallen")
    # Geen van de patronen matcht → leeg resultaat
    assert resultaat.tijdvervang is None
    assert resultaat.negeer is False
