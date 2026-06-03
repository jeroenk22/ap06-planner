"""Aanvullende tests voor wijzigingen-parser en tijdvenster-vergelijking."""


from ap06_planner.models.schemas import Tijdvenster
from ap06_planner.parsers.tijdvenster import vergelijk_tijdvensters
from ap06_planner.parsers.wijzigingen import (
    WijzigingenResultaat,
    _pas_claude_toe,
    _regex_fallback,
    pas_wijziging_toe,
    verwerk_wijzigingen,
)


def _maak_tv(**kwargs) -> Tijdvenster:
    defaults = {
        "plaats": "Bladel",
        "klant_naam": "TonTrans",
        "begintijd": "07:00",
        "eindtijd": "18:00",
        "type": "LAD",
        "nummer": "17",
        "origineel": "Bladel TonTrans 7-18 LAD17",
    }
    defaults.update(kwargs)
    return Tijdvenster(**defaults)


class TestNormaliseerTijdEnParseTijdvenster:
    """Extra tests voor ontbrekende takken in tijdvenster.py."""

    def test_parse_tijdvenster_begint_met_tijdvenster(self):
        """Als er niets voor het tijdvenster staat → lege plaats en klant_naam."""
        from ap06_planner.parsers.tijdvenster import parse_tijdvenster
        tv = parse_tijdvenster("7-18 LAD")
        assert tv is not None
        assert tv.plaats == ""
        assert tv.klant_naam == ""
        assert tv.begintijd == "07:00"

    def test_parse_tijdvenster_een_woord_voor(self):
        """Eén woord voor tijdvenster → alleen plaats, lege klant_naam."""
        from ap06_planner.parsers.tijdvenster import parse_tijdvenster
        tv = parse_tijdvenster("Bladel 7-18 LAD")
        assert tv is not None
        assert tv.plaats == "Bladel"
        assert tv.klant_naam == ""


class TestVergelijkTijdvensters:
    def test_lege_lijst(self):
        assert vergelijk_tijdvensters([]) is None

    def test_een_element(self):
        tv = _maak_tv(begintijd="07:00")
        result = vergelijk_tijdvensters([tv])
        assert result.begintijd == "07:00"

    def test_hoogste_begintijd_wint(self):
        tv1 = _maak_tv(begintijd="07:00", eindtijd="10:00")
        tv2 = _maak_tv(begintijd="14:00", eindtijd="16:00", plaats="Zundert")
        result = vergelijk_tijdvensters([tv1, tv2])
        assert result.plaats == "Zundert"

    def test_gelijke_begintijden(self):
        tv1 = _maak_tv(begintijd="10:00", eindtijd="12:00", plaats="A")
        tv2 = _maak_tv(begintijd="10:00", eindtijd="12:00", plaats="B")
        result = vergelijk_tijdvensters([tv1, tv2])
        assert result is not None


class TestPasClaudeToe:
    def test_negeer(self):
        r = _pas_claude_toe({"negeer": True})
        assert r.negeer is True

    def test_tijdvervang(self):
        r = _pas_claude_toe({"tijdvervang": ["12:00", "18:00"]})
        assert r.tijdvervang == ("12:00", "18:00")

    def test_start_na(self):
        r = _pas_claude_toe({"start_na": "12:00"})
        assert r.persoon_start_na == "12:00"

    def test_eind_voor(self):
        r = _pas_claude_toe({"eind_voor": "12:00"})
        assert r.persoon_eind_voor == "12:00"

    def test_hele_dag(self):
        r = _pas_claude_toe({"hele_dag": True})
        assert r.persoon_hele_dag is True

    def test_leeg_object(self):
        r = _pas_claude_toe({})
        assert r.negeer is False
        assert r.tijdvervang is None
        assert r.persoon_start_na is None


class TestRegexFallback:
    def test_tijdvervang(self):
        r = _regex_fallback("naar 12-18")
        assert r.tijdvervang == ("12:00", "18:00")

    def test_hele_dag(self):
        r = _regex_fallback("Anouk hele dag")
        assert r.persoon_hele_dag is True

    def test_na(self):
        r = _regex_fallback("Anouk na 12")
        assert r.persoon_start_na == "12:00"

    def test_tot(self):
        r = _regex_fallback("Tom tot 12")
        assert r.persoon_eind_voor == "12:00"

    def test_onbekend_patroon(self):
        r = _regex_fallback("iets onduidelijks")
        assert r.tijdvervang is None
        assert r.negeer is False


class TestVerwerkWijzigingen:
    def test_met_claude_cache_hit(self):
        cache = {"Naar 12-18": {"tijdvervang": ["12:00", "18:00"], "negeer": False}}
        r = verwerk_wijzigingen("Naar 12-18", claude_cache=cache)
        assert r.tijdvervang == ("12:00", "18:00")

    def test_met_claude_cache_miss_gebruikt_regex(self):
        cache = {}  # Cache niet leeg maar ook geen hit
        r = verwerk_wijzigingen("naar 8-10", claude_cache=cache)
        assert r.tijdvervang == ("08:00", "10:00")

    def test_claude_cache_none_gebruikt_service(self):
        """Als claude_cache=None, probeert het de Claude service (maar valt terug op regex)."""
        # Claude service mislukt → regex fallback
        r = verwerk_wijzigingen("Naar 12-18", claude_cache=None)
        # Regex pakt dit op
        assert r.tijdvervang == ("12:00", "18:00")

    def test_vanaf_patroon(self):
        r = verwerk_wijzigingen("Jan vanaf 12", claude_cache={})
        assert r.persoon_start_na == "12:00"

    def test_lege_string_na_strip(self):
        r = verwerk_wijzigingen("   ", claude_cache={})
        # Lege string na strip → negeer pattroon matcht niet → leeg resultaat
        # (strip geeft "   ".strip() = "" wat falsy is)
        # Eigenlijk: "   " is truthy maar strip geeft ""... wacht:
        # w = wijzigingen.strip() → "" → lege string?
        # Nee: "   ".strip() = "" maar in de code: if not wijzigingen: return resultaat
        # "   " is truthy, dus we gaan verder. w = "   ".strip() = ""
        # NEGEER_PATROON.search("") → None → geen negeer
        # claude_data = cache.get("") → None
        # _regex_fallback("") → leeg resultaat
        assert r.negeer is False
        assert r.tijdvervang is None


class TestPasWijzigingToe:
    def test_tijdvervang(self):
        tv = _maak_tv(begintijd="07:00", eindtijd="18:00")
        w = WijzigingenResultaat()
        w.tijdvervang = ("12:00", "18:00")
        nieuw = pas_wijziging_toe(tv, w)
        assert nieuw.begintijd == "12:00"
        assert nieuw.eindtijd == "18:00"
        assert "gewijzigd" in nieuw.origineel

    def test_eind_voor(self):
        tv = _maak_tv(begintijd="07:00", eindtijd="18:00")
        w = WijzigingenResultaat()
        w.persoon_eind_voor = "12:00"
        nieuw = pas_wijziging_toe(tv, w)
        assert nieuw.eindtijd == "12:00"
        assert nieuw.begintijd == "07:00"
        assert "tot" in nieuw.origineel

    def test_start_na(self):
        tv = _maak_tv(begintijd="07:00", eindtijd="18:00")
        w = WijzigingenResultaat()
        w.persoon_start_na = "12:00"
        nieuw = pas_wijziging_toe(tv, w)
        assert nieuw.begintijd == "12:00"
        assert nieuw.eindtijd == "18:00"
        assert "na" in nieuw.origineel

    def test_geen_wijziging(self):
        tv = _maak_tv(begintijd="07:00", eindtijd="18:00")
        w = WijzigingenResultaat()
        nieuw = pas_wijziging_toe(tv, w)
        assert nieuw is tv  # Zelfde object, niet gekopieerd

    def test_tijdvervang_behoudt_metadata(self):
        tv = _maak_tv(plaats="Bladel", type="LOS", nummer="3")
        w = WijzigingenResultaat()
        w.tijdvervang = ("10:00", "12:00")
        nieuw = pas_wijziging_toe(tv, w)
        assert nieuw.plaats == "Bladel"
        assert nieuw.type == "LOS"
        assert nieuw.nummer == "3"
