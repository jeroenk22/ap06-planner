"""Tests voor niet-UI logica in beheer.py — _dict_naar_monsternemer en Streamlit rendering."""

from pathlib import Path

import pytest

from ap06_planner.models.schemas import Monsternemer
from ap06_planner.pages.beheer import _dict_naar_monsternemer


def _form_data(**kwargs) -> dict:
    """Standaard formulierdata zoals beheer.py die produceert."""
    defaults = dict(
        voornaam="Jan",
        tussenvoegsel="de",
        achternaam="Vries",
        adres="Straat 1",
        postcode="1234ab",
        woonplaats="Amsterdam",
        land="Nederland",
        telefoon="0612345678",
        ophaaldagen=["ma", "wo"],
        laadinstructie="Bel aan",
        uiterlijke_tijd="21:30",
        uiterlijke_plantijd="20:00",
        bijzonderheden="Hond aanwezig",
        aantal_lege_bakken=2,
        sjabloon=False,
        ophalen=True,
    )
    defaults.update(kwargs)
    return defaults


class TestDictNaarMonsternemer:
    def test_basis(self):
        data = _form_data()
        m = _dict_naar_monsternemer(data)
        assert m.voornaam == "Jan"
        assert m.achternaam == "Vries"
        assert m.tussenvoegsel == "de"

    def test_postcode_uppercase(self):
        """Postcode wordt naar hoofdletters omgezet."""
        data = _form_data(postcode="1234ab")
        m = _dict_naar_monsternemer(data)
        assert m.postcode == "1234AB"

    def test_lege_tussenvoegsel_wordt_none(self):
        data = _form_data(tussenvoegsel="")
        m = _dict_naar_monsternemer(data)
        assert m.tussenvoegsel is None

    def test_lege_bijzonderheden_wordt_none(self):
        data = _form_data(bijzonderheden="")
        m = _dict_naar_monsternemer(data)
        assert m.bijzonderheden is None

    def test_lege_telefoon_wordt_none(self):
        data = _form_data(telefoon="")
        m = _dict_naar_monsternemer(data)
        assert m.telefoon is None

    def test_lege_laadinstructie_wordt_none(self):
        data = _form_data(laadinstructie="")
        m = _dict_naar_monsternemer(data)
        assert m.laadinstructie is None

    def test_lege_uiterlijke_tijd_wordt_none(self):
        data = _form_data(uiterlijke_tijd="")
        m = _dict_naar_monsternemer(data)
        assert m.uiterlijke_tijd is None

    def test_lege_uiterlijke_plantijd_wordt_none(self):
        data = _form_data(uiterlijke_plantijd="")
        m = _dict_naar_monsternemer(data)
        assert m.uiterlijke_plantijd is None

    def test_lege_land_wordt_none(self):
        data = _form_data(land="")
        m = _dict_naar_monsternemer(data)
        assert m.land is None

    def test_whitespace_gestript(self):
        data = _form_data(voornaam="  Jan  ", achternaam="  Smit  ")
        m = _dict_naar_monsternemer(data)
        assert m.voornaam == "Jan"
        assert m.achternaam == "Smit"

    def test_bestaande_monsternemer_behoudt_id_en_code(self):
        bestaande = Monsternemer(
            id=42,
            code="AP99",
            voornaam="Oud",
            tussenvoegsel=None,
            achternaam="Naam",
            adres="",
            postcode="",
            woonplaats="",
            land=None,
            telefoon=None,
            laadinstructie=None,
            ophaaldagen=[],
            uiterlijke_tijd=None,
            uiterlijke_plantijd=None,
            bijzonderheden=None,
        )
        data = _form_data()
        m = _dict_naar_monsternemer(data, bestaande=bestaande)
        assert m.id == 42
        assert m.code == "AP99"

    def test_nieuwe_monsternemer_heeft_ap06_code(self):
        data = _form_data()
        m = _dict_naar_monsternemer(data)
        assert m.id is None
        assert m.code == "AP06"

    def test_sjabloon_en_ophalen_flags(self):
        data = _form_data(sjabloon=True, ophalen=False)
        m = _dict_naar_monsternemer(data)
        assert m.sjabloon is True
        assert m.ophalen is False

    def test_ophaaldagen_bewaard(self):
        data = _form_data(ophaaldagen=["di", "do", "za"])
        m = _dict_naar_monsternemer(data)
        assert m.ophaaldagen == ["di", "do", "za"]

    def test_aantal_lege_bakken(self):
        data = _form_data(aantal_lege_bakken=5)
        m = _dict_naar_monsternemer(data)
        assert m.aantal_lege_bakken == 5


class TestBeheerRenderViaAppTest:
    """Test Streamlit rendering van beheer.render() via AppTest.from_file."""

    def test_render_lege_database(self):
        """render() met lege DB — alle tabs renderen zonder fout."""
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            pytest.skip("streamlit.testing.v1 niet beschikbaar")

        helpers_dir = Path(__file__).parent / "helpers"
        at = AppTest.from_file(str(helpers_dir / "beheer_lege_db.py"), default_timeout=15)
        at.run()
        assert not at.exception


class TestDbServiceMigratie:
    """Test database migratie — kolommen die in oudere DB's ontbreken."""

    def test_migratie_voegt_ontbrekende_kolommen_toe(self, tmp_path):
        """Simuleer een oude DB zonder de nieuwere kolommen."""
        import sqlite3
        db = tmp_path / "oud.db"

        # Maak een DB met alleen de basiskolommen (zonder nieuwe kolommen)
        conn = sqlite3.connect(db)
        conn.execute("""
            CREATE TABLE monsternemers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT NOT NULL DEFAULT 'AP06',
                voornaam        TEXT NOT NULL,
                tussenvoegsel   TEXT,
                achternaam      TEXT NOT NULL,
                adres           TEXT,
                postcode        TEXT,
                woonplaats      TEXT,
                telefoon        TEXT,
                laadinstructie  TEXT,
                ophaaldagen     TEXT,
                uiterlijke_tijd TEXT,
                bijzonderheden  TEXT
            )
        """)
        conn.commit()
        conn.close()

        # initialiseer_db moet de ontbrekende kolommen toevoegen
        from ap06_planner.services.db_service import initialiseer_db, haal_alle_monsternemers
        initialiseer_db(db)

        # DB mag nu geen fout gooien bij ophalen
        result = haal_alle_monsternemers(db)
        assert result == []

    def test_migratie_idempotent_op_bestaande_db(self, tmp_path):
        """Tweede aanroep van initialiseer_db crasht niet."""
        from ap06_planner.services.db_service import (
            initialiseer_db, voeg_monsternemer_toe, haal_alle_monsternemers
        )
        from ap06_planner.models.schemas import Monsternemer
        db = tmp_path / "test.db"
        initialiseer_db(db)
        initialiseer_db(db)  # Tweede keer, kolommen bestaan al
        assert haal_alle_monsternemers(db) == []


class TestDbServiceFouten:
    """Test error handling in db_service."""

    def test_voeg_toe_db_fout_raises(self, tmp_path):
        """Database fout bij INSERT gooit RuntimeError."""
        import sqlite3
        from unittest.mock import patch, MagicMock
        from ap06_planner.services.db_service import voeg_monsternemer_toe
        from ap06_planner.models.schemas import Monsternemer

        db = tmp_path / "test.db"
        m = Monsternemer(
            id=None, code="AP06", voornaam="Jan", tussenvoegsel=None,
            achternaam="Smit", adres="", postcode="", woonplaats="",
            land=None, telefoon=None, laadinstructie=None, ophaaldagen=[],
            uiterlijke_tijd=None, uiterlijke_plantijd=None, bijzonderheden=None,
        )

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value.execute.side_effect = \
            sqlite3.OperationalError("disk full")

        with patch("ap06_planner.services.db_service.initialiseer_db"), \
             patch("ap06_planner.services.db_service._get_conn", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="Database fout"):
                voeg_monsternemer_toe(m, db)

    def test_haal_alle_db_fout_raises(self, tmp_path):
        """Database fout bij SELECT gooit RuntimeError."""
        import sqlite3
        from unittest.mock import patch, MagicMock
        from ap06_planner.services.db_service import haal_alle_monsternemers

        db = tmp_path / "test.db"
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value.execute.side_effect = \
            sqlite3.OperationalError("locked")

        with patch("ap06_planner.services.db_service.initialiseer_db"), \
             patch("ap06_planner.services.db_service._get_conn", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="Database fout"):
                haal_alle_monsternemers(db)

    def test_update_db_fout_raises(self, tmp_path):
        """Database fout bij UPDATE gooit RuntimeError."""
        import sqlite3
        from unittest.mock import patch, MagicMock
        from ap06_planner.services.db_service import update_monsternemer
        from ap06_planner.models.schemas import Monsternemer

        db = tmp_path / "test.db"
        m = Monsternemer(
            id=1, code="AP06", voornaam="Jan", tussenvoegsel=None,
            achternaam="Smit", adres="", postcode="", woonplaats="",
            land=None, telefoon=None, laadinstructie=None, ophaaldagen=[],
            uiterlijke_tijd=None, uiterlijke_plantijd=None, bijzonderheden=None,
        )

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value.execute.side_effect = \
            sqlite3.OperationalError("disk full")

        with patch("ap06_planner.services.db_service.initialiseer_db"), \
             patch("ap06_planner.services.db_service._get_conn", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="Database fout"):
                update_monsternemer(m, db)

    def test_verwijder_db_fout_raises(self, tmp_path):
        """Database fout bij DELETE gooit RuntimeError."""
        import sqlite3
        from unittest.mock import patch, MagicMock
        from ap06_planner.services.db_service import verwijder_monsternemer

        db = tmp_path / "test.db"
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value.execute.side_effect = \
            sqlite3.OperationalError("locked")

        with patch("ap06_planner.services.db_service.initialiseer_db"), \
             patch("ap06_planner.services.db_service._get_conn", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="Database fout"):
                verwijder_monsternemer(1, db)
