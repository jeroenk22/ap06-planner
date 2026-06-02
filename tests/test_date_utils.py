"""Tests voor date_utils."""

import pytest
from datetime import date

from ap06_planner.utils.date_utils import (
    DAGAFKORTINGEN,
    DAGNAMEN_NL,
    format_datum_nl,
    is_ophaaldag,
    parse_datum,
    voeg_minuten_toe,
)


class TestIsOphaaldag:
    def test_maandag_is_ma(self):
        maandag = date(2026, 6, 1)  # weekday() == 0
        assert is_ophaaldag(maandag, ["ma"]) is True

    def test_maandag_niet_in_di_wo(self):
        maandag = date(2026, 6, 1)
        assert is_ophaaldag(maandag, ["di", "wo"]) is False

    def test_lege_ophaaldagen(self):
        assert is_ophaaldag(date(2026, 6, 1), []) is False

    def test_onbekende_afkorting(self):
        assert is_ophaaldag(date(2026, 6, 1), ["xx", "zz"]) is False

    def test_vrijdag(self):
        vrijdag = date(2026, 6, 5)  # weekday() == 4
        assert is_ophaaldag(vrijdag, ["vr"]) is True
        assert is_ophaaldag(vrijdag, ["ma"]) is False

    def test_zaterdag(self):
        zaterdag = date(2026, 6, 6)  # weekday() == 5
        assert is_ophaaldag(zaterdag, ["za"]) is True

    def test_meerdere_ophaaldagen_match(self):
        woensdag = date(2026, 6, 3)  # weekday() == 2
        assert is_ophaaldag(woensdag, ["ma", "wo", "vr"]) is True


class TestFormatDatumNl:
    def test_maandag(self):
        assert format_datum_nl(date(2026, 6, 1)) == "maandag 01-06-2026"

    def test_vrijdag(self):
        assert format_datum_nl(date(2026, 6, 5)) == "vrijdag 05-06-2026"

    def test_zaterdag(self):
        assert format_datum_nl(date(2026, 6, 6)) == "zaterdag 06-06-2026"

    def test_zondag(self):
        assert format_datum_nl(date(2026, 6, 7)) == "zondag 07-06-2026"

    def test_nulpadding(self):
        result = format_datum_nl(date(2026, 1, 5))
        assert "05-01-2026" in result


class TestVoegMinutenToe:
    def test_basis(self):
        assert voeg_minuten_toe("10:00", 30) == "10:30"

    def test_uur_overgang(self):
        assert voeg_minuten_toe("10:45", 30) == "11:15"

    def test_dag_overgang(self):
        assert voeg_minuten_toe("23:45", 30) == "00:15"

    def test_nul_minuten(self):
        assert voeg_minuten_toe("15:00", 0) == "15:00"

    def test_exact_uur(self):
        assert voeg_minuten_toe("09:00", 60) == "10:00"

    def test_nulpadding(self):
        assert voeg_minuten_toe("08:30", 15) == "08:45"

    def test_ongeldige_input_raises(self):
        with pytest.raises(ValueError, match="Ongeldige tijdstring"):
            voeg_minuten_toe("geen_tijd", 30)

    def test_lege_string_raises(self):
        with pytest.raises(ValueError):
            voeg_minuten_toe("", 10)


class TestParseDatum:
    def test_dd_mm_jjjj(self):
        assert parse_datum("13-06-2026") == date(2026, 6, 13)

    def test_dd_slash_mm_jjjj(self):
        assert parse_datum("13/06/2026") == date(2026, 6, 13)

    def test_iso_formaat(self):
        assert parse_datum("2026-06-13") == date(2026, 6, 13)

    def test_ongeldig_geeft_none(self):
        assert parse_datum("geen datum") is None

    def test_lege_string_geeft_none(self):
        assert parse_datum("") is None

    def test_dag_met_nulpadding(self):
        assert parse_datum("01-01-2026") == date(2026, 1, 1)


class TestConstants:
    def test_dagafkortingen_volledig(self):
        for afk in ["ma", "di", "wo", "do", "vr", "za", "zo"]:
            assert afk in DAGAFKORTINGEN

    def test_dagnamen_nl_volledig(self):
        assert DAGNAMEN_NL[0] == "maandag"
        assert DAGNAMEN_NL[6] == "zondag"
