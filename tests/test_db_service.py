"""Tests voor db_service — SQLite CRUD met tijdelijke database."""

import sqlite3
from pathlib import Path

import pytest

from ap06_planner.models.schemas import Monsternemer
from ap06_planner.services.db_service import (
    haal_alle_monsternemers,
    initialiseer_db,
    update_monsternemer,
    verwijder_monsternemer,
    voeg_monsternemer_toe,
    zoek_monsternemer,
)


def _m(**kwargs) -> Monsternemer:
    """Hulpfunctie: maak een test-monsternemer met defaults."""
    defaults = dict(
        id=None,
        code="AP06",
        voornaam="Jan",
        tussenvoegsel=None,
        achternaam="de Vries",
        adres="Straat 1",
        postcode="1234AB",
        woonplaats="Amsterdam",
        land="Nederland",
        telefoon="0612345678",
        laadinstructie=None,
        ophaaldagen=["ma", "wo"],
        uiterlijke_tijd="21:30",
        uiterlijke_plantijd="20:00",
        bijzonderheden=None,
        aantal_lege_bakken=2,
        sjabloon=False,
        ophalen=True,
    )
    defaults.update(kwargs)
    return Monsternemer(**defaults)


class TestInitialiseerDb:
    def test_maakt_bestand_aan(self, tmp_path):
        db = tmp_path / "test.db"
        initialiseer_db(db)
        assert db.exists()

    def test_idempotent(self, tmp_path):
        db = tmp_path / "test.db"
        initialiseer_db(db)
        initialiseer_db(db)  # Mag niet crashen

    def test_maakt_submap_aan(self, tmp_path):
        db = tmp_path / "sub" / "diep" / "test.db"
        initialiseer_db(db)
        assert db.exists()


class TestHaalAlleMonsternemers:
    def test_leeg(self, tmp_path):
        db = tmp_path / "test.db"
        assert haal_alle_monsternemers(db) == []

    def test_na_toevoegen(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(), db)
        alle = haal_alle_monsternemers(db)
        assert len(alle) == 1

    def test_gesorteerd_op_achternaam(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(voornaam="Piet", achternaam="Zoomer"), db)
        voeg_monsternemer_toe(_m(voornaam="An", achternaam="Aerts"), db)
        alle = haal_alle_monsternemers(db)
        assert alle[0].achternaam == "Aerts"
        assert alle[1].achternaam == "Zoomer"


class TestVoegMonsternemerrToe:
    def test_retourneert_id(self, tmp_path):
        db = tmp_path / "test.db"
        nieuw_id = voeg_monsternemer_toe(_m(), db)
        assert isinstance(nieuw_id, int)
        assert nieuw_id > 0

    def test_ophaaldagen_worden_opgeslagen(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(ophaaldagen=["ma", "wo", "vr"]), db)
        alle = haal_alle_monsternemers(db)
        assert alle[0].ophaaldagen == ["ma", "wo", "vr"]

    def test_lege_ophaaldagen(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(ophaaldagen=[]), db)
        alle = haal_alle_monsternemers(db)
        assert alle[0].ophaaldagen == []

    def test_met_tussenvoegsel(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(tussenvoegsel="van der"), db)
        alle = haal_alle_monsternemers(db)
        assert alle[0].tussenvoegsel == "van der"
        assert "van der" in alle[0].volledige_naam

    def test_sjabloon_en_ophalen_flags(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(sjabloon=True, ophalen=False), db)
        alle = haal_alle_monsternemers(db)
        assert alle[0].sjabloon is True
        assert alle[0].ophalen is False

    def test_velden_bewaard(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(
            voornaam="Marie",
            achternaam="Pietersen",
            adres="Dorpsstraat 5",
            postcode="5678XY",
            woonplaats="Eindhoven",
            telefoon="0698765432",
            laadinstructie="Bel eerst aan",
            bijzonderheden="Hond aanwezig",
            aantal_lege_bakken=3,
        ), db)
        m = haal_alle_monsternemers(db)[0]
        assert m.voornaam == "Marie"
        assert m.adres == "Dorpsstraat 5"
        assert m.laadinstructie == "Bel eerst aan"
        assert m.bijzonderheden == "Hond aanwezig"
        assert m.aantal_lege_bakken == 3


class TestZoekMonsternemer:
    def test_exacte_naam(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(voornaam="Jan", tussenvoegsel=None, achternaam="Smit"), db)
        gevonden = zoek_monsternemer("Jan Smit", db)
        assert gevonden is not None
        assert gevonden.achternaam == "Smit"

    def test_naam_met_tussenvoegsel_exact(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(voornaam="Jan", tussenvoegsel="de", achternaam="Vries"), db)
        gevonden = zoek_monsternemer("Jan de Vries", db)
        assert gevonden is not None

    def test_naam_zonder_tussenvoegsel_fallback(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(voornaam="Jan", tussenvoegsel="de", achternaam="Vries"), db)
        gevonden = zoek_monsternemer("Jan Vries", db)
        assert gevonden is not None
        assert gevonden.achternaam == "Vries"

    def test_fuzzy_voornaam_achternaam(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(voornaam="Jan", tussenvoegsel="van", achternaam="Dam"), db)
        gevonden = zoek_monsternemer("Jan Dam", db)
        assert gevonden is not None

    def test_niet_gevonden(self, tmp_path):
        db = tmp_path / "test.db"
        initialiseer_db(db)
        assert zoek_monsternemer("Onbekende Persoon", db) is None

    def test_case_insensitive(self, tmp_path):
        db = tmp_path / "test.db"
        voeg_monsternemer_toe(_m(voornaam="Jan", achternaam="Smit"), db)
        gevonden = zoek_monsternemer("jan smit", db)
        assert gevonden is not None

    def test_fuzzy_via_derde_loop(self, tmp_path):
        """Fuzzy-match gebruikt derde loop (voornaam+achternaam subset)."""
        db = tmp_path / "test.db"
        # "Maria van den Berg" — exact mist, zonder_tv = "Maria Berg" ≠ "Maria van Berg"
        voeg_monsternemer_toe(_m(voornaam="Maria", tussenvoegsel="van den", achternaam="Berg"), db)
        # Zoek "Maria van Berg" → exact mist, zonder_tv "Maria Berg" ≠ "Maria van Berg"
        # Fuzzy: names=["maria","van","berg"], first="maria", last="berg" → match!
        gevonden = zoek_monsternemer("Maria van Berg", db)
        assert gevonden is not None
        assert gevonden.voornaam == "Maria"


class TestSafeRowEnMigratie:
    def test_safe_row_ontbrekende_kolom(self, tmp_path):
        """_safe_row retourneert None als kolom niet bestaat (IndexError pad)."""
        import sqlite3
        from ap06_planner.services.db_service import _safe_row

        # Maak een row zonder 'land' kolom via een echte query
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE t (id INTEGER, naam TEXT)")
        conn.execute("INSERT INTO t VALUES (1, 'test')")
        row = conn.execute("SELECT * FROM t").fetchone()

        result = _safe_row(row, "land")  # Kolom bestaat niet
        assert result is None
        conn.close()

    def test_safe_row_bestaande_kolom(self, tmp_path):
        """_safe_row retourneert de waarde als kolom bestaat."""
        import sqlite3
        from ap06_planner.services.db_service import _safe_row

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE t (id INTEGER, land TEXT)")
        conn.execute("INSERT INTO t VALUES (1, 'Nederland')")
        row = conn.execute("SELECT * FROM t").fetchone()

        result = _safe_row(row, "land")
        assert result == "Nederland"
        conn.close()


class TestUpdateMonsternemer:
    def test_update_voornaam(self, tmp_path):
        db = tmp_path / "test.db"
        nieuw_id = voeg_monsternemer_toe(_m(voornaam="Jan"), db)
        gewijzigd = _m(id=nieuw_id, voornaam="Piet")
        assert update_monsternemer(gewijzigd, db) is True
        assert haal_alle_monsternemers(db)[0].voornaam == "Piet"

    def test_niet_bestaand_id(self, tmp_path):
        db = tmp_path / "test.db"
        initialiseer_db(db)
        m = _m(id=9999)
        assert update_monsternemer(m, db) is False

    def test_update_ophaaldagen(self, tmp_path):
        db = tmp_path / "test.db"
        nieuw_id = voeg_monsternemer_toe(_m(ophaaldagen=["ma"]), db)
        gewijzigd = _m(id=nieuw_id, ophaaldagen=["di", "do", "za"])
        update_monsternemer(gewijzigd, db)
        alle = haal_alle_monsternemers(db)
        assert alle[0].ophaaldagen == ["di", "do", "za"]

    def test_update_zonder_bestaande_db_werkt(self, tmp_path):
        """update_monsternemer roept initialiseer_db aan — mag niet crashen op lege DB."""
        db = tmp_path / "nieuw.db"
        m = _m(id=1)
        result = update_monsternemer(m, db)
        assert result is False  # Tabel bestaat, maar rij niet


class TestVerwijderMonsternemer:
    def test_verwijder_bestaand(self, tmp_path):
        db = tmp_path / "test.db"
        nieuw_id = voeg_monsternemer_toe(_m(), db)
        assert verwijder_monsternemer(nieuw_id, db) is True
        assert haal_alle_monsternemers(db) == []

    def test_verwijder_niet_bestaand(self, tmp_path):
        db = tmp_path / "test.db"
        initialiseer_db(db)
        assert verwijder_monsternemer(9999, db) is False

    def test_verwijder_een_van_twee(self, tmp_path):
        db = tmp_path / "test.db"
        id1 = voeg_monsternemer_toe(_m(voornaam="Jan"), db)
        voeg_monsternemer_toe(_m(voornaam="Piet"), db)
        verwijder_monsternemer(id1, db)
        alle = haal_alle_monsternemers(db)
        assert len(alle) == 1
        assert alle[0].voornaam == "Piet"

    def test_verwijder_zonder_bestaande_db_werkt(self, tmp_path):
        """verwijder_monsternemer roept initialiseer_db aan — mag niet crashen."""
        db = tmp_path / "nieuw.db"
        assert verwijder_monsternemer(1, db) is False
