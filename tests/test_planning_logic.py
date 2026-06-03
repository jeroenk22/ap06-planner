"""Tests voor niet-UI logica in planning.py — _haversine_km, _kies_laatste_tv, _verwerk_monsternemer."""

import math
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ap06_planner.models.schemas import Monsternemer, PlanningRegel, Tijdvenster
from ap06_planner.pages.planning import (
    _haversine_km,
    _kies_laatste_tv,
    _verwerk_monsternemer,
)


# ─── Hulpfuncties ────────────────────────────────────────────────────────────

def _tv(plaats="Bladel", begintijd="07:00", eindtijd="18:00", **kwargs) -> Tijdvenster:
    return Tijdvenster(
        plaats=plaats,
        klant_naam="TonTrans",
        begintijd=begintijd,
        eindtijd=eindtijd,
        type="LAD",
        nummer=None,
        origineel=f"{plaats} {begintijd}-{eindtijd}",
        **kwargs,
    )


def _monsternemer(**kwargs) -> Monsternemer:
    defaults = dict(
        id=1,
        code="AP06",
        voornaam="Jan",
        tussenvoegsel=None,
        achternaam="de Vries",
        adres="Straat 1",
        postcode="1234AB",
        woonplaats="Amsterdam",
        land="Nederland",
        telefoon="0612345678",
        laadinstructie="Bel aan",
        ophaaldagen=["ma", "wo", "vr"],
        uiterlijke_tijd="21:30",
        uiterlijke_plantijd=None,
        bijzonderheden=None,
        aantal_lege_bakken=2,
        sjabloon=False,
        ophalen=True,
    )
    defaults.update(kwargs)
    return Monsternemer(**defaults) # type: ignore[arg-type]


def _regel(
    monsternemer_naam="Jan de Vries",
    locatie_raw="Bladel TonTrans 7-18 LAD17",
    wijzigingen=None,
    overgeslagen=False,
) -> PlanningRegel:
    return PlanningRegel(
        monsternemer_naam=monsternemer_naam,
        wijzigingen=wijzigingen,
        locatie_raw=locatie_raw,
        klant_raw=None,
        overgeslagen=overgeslagen,
    )


# ─── _haversine_km ───────────────────────────────────────────────────────────

class TestHaversineKm:
    def test_zelfde_punt_is_nul(self):
        assert _haversine_km(5.0, 51.0, 5.0, 51.0) == pytest.approx(0.0, abs=0.1)

    def test_amsterdam_eindhoven_orde(self):
        # Amsterdam ~(4.9, 52.4) → Eindhoven ~(5.5, 51.4) ≈ 110 km
        km = _haversine_km(4.9, 52.4, 5.5, 51.4)
        assert 100 < km < 130

    def test_positief(self):
        assert _haversine_km(0.0, 0.0, 1.0, 1.0) > 0


# ─── _kies_laatste_tv ────────────────────────────────────────────────────────

class TestKiesLaatsteTv:
    def test_lege_lijst(self):
        result, warnings = _kies_laatste_tv([], None, None)
        assert result is None
        assert warnings == []

    def test_een_tijdvenster(self):
        tv = _tv(eindtijd="18:00")
        result, warnings = _kies_laatste_tv([tv], None, None)
        assert result is tv
        assert warnings == []

    def test_hoogste_eindtijd_wint(self):
        tv1 = _tv(plaats="A", eindtijd="12:00")
        tv2 = _tv(plaats="B", eindtijd="18:00")
        result, _ = _kies_laatste_tv([tv1, tv2], None, None)
        assert result.plaats == "B"

    def test_gelijke_eindtijd_geen_woonplaats(self):
        tv1 = _tv(plaats="A", eindtijd="18:00")
        tv2 = _tv(plaats="B", eindtijd="18:00")
        result, warnings = _kies_laatste_tv([tv1, tv2], None, None)
        assert result is not None
        assert any("geen woonplaats" in w for w in warnings)

    def test_gelijke_eindtijd_met_tiebreak_geocoding_mislukt(self):
        tv1 = _tv(plaats="A", eindtijd="18:00")
        tv2 = _tv(plaats="B", eindtijd="18:00")
        with patch("ap06_planner.pages.planning._geocodeer", return_value=None):
            result, warnings = _kies_laatste_tv([tv1, tv2], "Amsterdam", "1234AB")
        assert result is not None
        assert any("geocoding" in w for w in warnings)

    def test_gelijke_eindtijd_tiebreak_via_afstand(self):
        tv1 = _tv(plaats="Dichtbij", eindtijd="18:00")
        tv2 = _tv(plaats="Ver", eindtijd="18:00")

        thuis_coords = (5.0, 52.0)
        dichtbij_coords = (5.1, 52.1)  # ~15 km
        ver_coords = (6.5, 51.5)  # ~150 km

        call_count = {"n": 0}

        def fake_geocodeer(adres):
            call_count["n"] += 1
            if "Amsterdam" in adres:
                return ("Nominatim", thuis_coords)
            if "Dichtbij" in adres:
                return ("Nominatim", dichtbij_coords)
            if "Ver" in adres:
                return ("Nominatim", ver_coords)
            return None

        with patch("ap06_planner.pages.planning._geocodeer", side_effect=fake_geocodeer):
            result, warnings = _kies_laatste_tv(
                [tv1, tv2], "Amsterdam", "1234AB", bereken_tiebreak=True
            )
        assert result.plaats == "Ver"

    def test_geen_tiebreak_geeft_eerste(self):
        tv1 = _tv(plaats="A", eindtijd="18:00")
        tv2 = _tv(plaats="B", eindtijd="18:00")
        result, warnings = _kies_laatste_tv(
            [tv1, tv2], "Amsterdam", "1234AB", bereken_tiebreak=False
        )
        assert result.plaats == "A"
        assert warnings == []

    def test_tiebreak_alle_plaatsen_niet_geocodeerbaar_geeft_eerste(self):
        """Als geen van de kandidaten geocodeerbaar is → eerste geretourneerd."""
        tv1 = _tv(plaats="A", eindtijd="18:00")
        tv2 = _tv(plaats="B", eindtijd="18:00")

        thuis_coords = (5.0, 52.0)
        call_count = {"n": 0}

        def fake_geocodeer(adres):
            call_count["n"] += 1
            if "Amsterdam" in adres:
                return ("Nominatim", thuis_coords)
            return None  # Alle plaatsnamen mislukken

        with patch("ap06_planner.pages.planning._geocodeer", side_effect=fake_geocodeer):
            result, warnings = _kies_laatste_tv(
                [tv1, tv2], "Amsterdam", "1234AB", bereken_tiebreak=True
            )
        assert result.plaats == "A"  # Fallback: eerste kandidaat


# ─── _verwerk_monsternemer ───────────────────────────────────────────────────

class TestVerwerkMonsternemer:
    """Grondig testen van de planningslogica voor één monsternemer."""

    def _verwerk(self, naam, regels, datum, dagnaam="maandag",
                 bekende_namen=None, bekende_monsternemers=None,
                 monsternemer=None, claude_tv_cache=None,
                 is_feestdag=False, eerstvolgende=None):
        """Helper die alle externe afhankelijkheden mockt."""
        bekende_namen = bekende_namen or []
        bekende_monsternemers = bekende_monsternemers or []
        m = monsternemer

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=is_feestdag), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(eerstvolgende or datum, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "21:30", "30 min reistijd debug")):
            return _verwerk_monsternemer(
                naam=naam,
                regels=regels,
                datum=datum,
                dagnaam=dagnaam,
                bekende_namen=bekende_namen,
                bekende_monsternemers=bekende_monsternemers,
                claude_tv_cache=claude_tv_cache,
            )

    def test_basis_ophaaldag(self):
        """Monsternemer op een ophaaldag — normaal pad."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)  # weekday() == 0
        regels = [_regel()]

        result = self._verwerk("Jan de Vries", regels, maandag, monsternemer=m)

        assert result is not None
        assert result["naam_monsternemer"] == "Jan de Vries"
        assert result["huidige_dag_is_ophaaldag"] is True

    def test_geen_ophaaldag_geeft_volgende(self):
        """Maandag voor iemand die alleen dinsdag opgehaald wordt."""
        m = _monsternemer(ophaaldagen=["di"])
        maandag = date(2026, 6, 1)
        dinsdag = date(2026, 6, 2)
        regels = [_regel()]

        result = self._verwerk("Jan de Vries", regels, maandag, monsternemer=m,
                               eerstvolgende=dinsdag)

        assert result is not None
        assert result["huidige_dag_is_ophaaldag"] is False
        assert "dinsdag" in result["inplannen_op"]

    def test_niet_in_database(self):
        """Monsternemer niet gevonden → niet_in_database flag."""
        maandag = date(2026, 6, 1)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=None), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "23:59", "debug")):
            result = _verwerk_monsternemer(
                naam="Onbekende Persoon",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert result["niet_in_database"] is True

    def test_geen_geldige_ophaaldagen_geeft_none(self):
        """Monsternemer met ophaaldagen=['geen'] → return None."""
        m = _monsternemer(ophaaldagen=["geen"])  # Ongeldige afkorting
        maandag = date(2026, 6, 1)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is None

    def test_feestdag_verschuift_ophaling(self):
        """Op een feestdag wordt de ophaling verschoven."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 4, 20)  # Hypothetische feestdag
        woensdag = date(2026, 4, 22)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=True), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(woensdag, True)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert "verschoven" in (result["inplannen_toelichting"] or "")

    def test_claude_cache_tijdvenster(self):
        """Claude TV cache wordt gebruikt als beschikbaar."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="Bladel 7-18 LAD17")]
        cache = {
            ("Bladel 7-18 LAD17", None): {
                "plaats": "Bladel",
                "begintijd": "07:00",
                "eindtijd": "18:00",
                "type": "LAD",
                "nummer": "17",
                "overgeslagen": False,
            }
        }

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=cache,
            )

        assert result is not None
        assert result["laatste_tijdvenster_plaats"] == "Bladel"

    def test_claude_cache_geen_eindtijd_warning(self):
        """Claude geeft geen eindtijd → warning + fallback naar 23:59."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="Bladel 7-18 LAD")]
        cache = {
            ("Bladel 7-18 LAD", None): {
                "plaats": "Bladel",
                "begintijd": "07:00",
                "eindtijd": None,  # Geen eindtijd!
                "type": "LAD",
                "nummer": None,
                "overgeslagen": False,
            }
        }

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "23:59", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=cache,
            )

        assert result is not None
        assert any("geen eindtijd" in w for w in result["warnings"])
        assert "23:59" in (result["laatste_tijdvenster"] or "")

    def test_claude_cache_overgeslagen(self):
        """Claude markeert een regel als overgeslagen."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="dagblok")]
        cache = {("dagblok", None): {"overgeslagen": True}}

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("10:00", "23:59", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=cache,
            )

        assert result is not None
        assert result["laatste_tijdvenster"] is None  # Geen tijdvenster

    def test_regex_fallback_geen_tijdvenster(self):
        """Regel zonder tijdvenster wordt bijgehouden in warnings."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="geen tijdvenster hier")]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("10:00", "23:59", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=None,
            )

        assert result is not None
        assert any("Geen tijdvenster" in w for w in result["warnings"])

    def test_uiterlijke_plantijd_overschreden(self):
        """Als aankomsttijd > uiterlijke plantijd → verschuif naar volgende ophaaldag."""
        m = _monsternemer(ophaaldagen=["ma"], uiterlijke_plantijd="18:00")
        maandag = date(2026, 6, 1)
        woensdag = date(2026, 6, 3)
        regels = [_regel()]

        # bereken_aankomsttijd geeft 20:00 terug, dat is > uiterlijke_plantijd=18:00
        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(woensdag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("20:00", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert "verschoven" in (result["inplannen_toelichting"] or "")
        assert "woensdag" in result["inplannen_op"]
        assert result["gewensttijd"] == "10:00 - 21:30"  # default uiterlijke_tijd uit _monsternemer

    def test_uiterlijke_plantijd_overschreden_zonder_uiterlijke_tijd(self):
        """Bij verschuiven zonder uiterlijke_tijd wordt 23:59 als eindtijd gebruikt."""
        m = _monsternemer(ophaaldagen=["ma"], uiterlijke_plantijd="18:00", uiterlijke_tijd=None)
        maandag = date(2026, 6, 1)
        woensdag = date(2026, 6, 3)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(woensdag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("20:00", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert result["gewensttijd"] == "10:00 - 23:59"

    def test_uiterlijke_plantijd_overschreden_met_uiterlijke_tijd(self):
        """Bij verschuiven wordt uiterlijke_tijd van monsternemer gerespecteerd als eindtijd."""
        m = _monsternemer(ophaaldagen=["ma"], uiterlijke_plantijd="18:00", uiterlijke_tijd="20:00")
        maandag = date(2026, 6, 1)
        woensdag = date(2026, 6, 3)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(woensdag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("20:00", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert "verschoven" in (result["inplannen_toelichting"] or "")
        assert result["gewensttijd"] == "10:00 - 20:00"

    def test_uiterlijke_tijd_conflict(self):
        """Als aankomsttijd > uiterlijke tijd (maar niet plantijd) → tijdconflict warning."""
        m = _monsternemer(ophaaldagen=["ma"], uiterlijke_tijd="18:00", uiterlijke_plantijd=None)
        maandag = date(2026, 6, 1)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:00", "18:00", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert any("tijdconflict" in w for w in result["warnings"])

    def test_naam_matching_via_claude(self):
        """Als naam niet in DB, probeer Claude matching."""
        m = _monsternemer()
        maandag = date(2026, 6, 1)
        regels = [_regel(monsternemer_naam="Jan vd Vries")]

        with patch("ap06_planner.pages.planning.zoek_monsternemer",
                   side_effect=[None, m]), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam",
                   return_value="Jan de Vries"), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan vd Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=["Jan de Vries"],
                bekende_monsternemers=[m],
            )

        assert result is not None
        assert any("gematcht" in w.lower() for w in result["warnings"])

    def test_min_eind_cap_via_wijziging(self):
        """persoon_eind_voor uit wijziging wordt toegepast als cap op eindtijd."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="Bladel 7-18 LAD", wijzigingen="Tom tot 12")]
        cache = {
            ("Bladel 7-18 LAD", "Tom tot 12"): {
                "plaats": "Bladel",
                "begintijd": "07:00",
                "eindtijd": "18:00",
                "type": "LAD",
                "nummer": None,
                "overgeslagen": False,
            }
        }

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("14:00", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=cache,
            )

        assert result is not None
        # Cap: min("12:00", "18:00") = "12:00"
        assert "12:00" in (result["laatste_tijdvenster"] or "")

    def test_geen_datum_geen_ophaaldagen_berekening(self):
        """Zonder datum wordt ophaaldag-logica overgeslagen."""
        m = _monsternemer(ophaaldagen=["ma"])
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=None,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        assert result["inplannen_op"] == ""

    def test_output_structuur(self):
        """Controleer dat het output-dict alle verwachte sleutels heeft."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel()]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("19:45", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
            )

        assert result is not None
        verwachte_sleutels = {
            "dagnaam", "datum", "naam_monsternemer", "adres", "postcode",
            "woonplaats", "telefoon", "laatste_tijdvenster_plaats",
            "laatste_tijdvenster", "standaard_ophaaldagen",
            "huidige_dag_is_ophaaldag", "inplannen_op", "inplannen_toelichting",
            "laadinstructie", "bijzonderheden_laden", "algemene_instructie_ap06",
            "gewensttijd", "niet_in_database", "warnings",
        }
        assert verwachte_sleutels.issubset(result.keys())

    def test_regex_pad_met_persoon_eind_voor_cap(self):
        """Regex-pad: wijziging met persoon_eind_voor wordt als cap toegepast."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="Bladel 7-18 LAD", wijzigingen="Tom tot 12")]
        # Geen claude_tv_cache → regex-pad

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("14:00", "21:30", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=None,
            )

        assert result is not None
        # Cap: min("12:00", "18:00") = "12:00"
        assert "12:00" in (result["laatste_tijdvenster"] or "")

    def test_wijziging_negeer_in_regex_pad(self):
        """Wijziging met negeer=True slaat de regel over (regex-pad)."""
        m = _monsternemer(ophaaldagen=["ma"])
        maandag = date(2026, 6, 1)
        regels = [_regel(locatie_raw="Bladel 7-18 LAD", wijzigingen="dagblok")]

        with patch("ap06_planner.pages.planning.zoek_monsternemer", return_value=m), \
             patch("ap06_planner.pages.planning.match_monsternemer_naam", return_value=None), \
             patch("ap06_planner.pages.planning.is_feestdag", return_value=False), \
             patch("ap06_planner.pages.planning.eerstvolgende_ophaaldag",
                   return_value=(maandag, False)), \
             patch("ap06_planner.pages.planning.bereken_aankomsttijd",
                   return_value=("10:00", "23:59", "debug")):
            result = _verwerk_monsternemer(
                naam="Jan de Vries",
                regels=regels,
                datum=maandag,
                dagnaam="maandag",
                bekende_namen=[],
                bekende_monsternemers=[],
                claude_tv_cache=None,  # Gebruik regex fallback
            )

        assert result is not None
        # Regel overgeslagen → geen tijdvensters
        assert result["laatste_tijdvenster"] is None
