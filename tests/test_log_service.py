"""Tests voor log_service.py — logging initialisatie en bestandsnaam-helpers."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ap06_planner.services import log_service
from ap06_planner.services.log_service import (
    LOG_RETENTIE_DAGEN,
    LOGGER_CLAUDE,
    LOGGER_MENDRIX,
    LOGGER_OSRM,
    LOGGER_PLANNING,
    MAX_LOGBESTANDEN_PER_COMPONENT,
    _log_bestandsnaam,
    _ruim_oude_logs_op,
    _xlsx_naar_bestandsdeel,
    _XlsxFileHandler,
    debug_json_pad,
    initialiseer_logging,
    sla_xlsx_op,
    zet_actieve_xlsx,
)


class TestXlsxNaarBestandsdeel:
    def test_naam_zonder_extensie(self):
        assert _xlsx_naar_bestandsdeel("planning.xlsx") == "planning"

    def test_naam_met_pad(self):
        assert _xlsx_naar_bestandsdeel("uploads/AP06_week23.xlsx") == "AP06_week23"

    def test_onveilige_tekens_vervangen(self):
        resultaat = _xlsx_naar_bestandsdeel('planning:"test"<>.xlsx')
        assert '"' not in resultaat
        assert "<" not in resultaat
        assert ">" not in resultaat
        assert ":" not in resultaat

    def test_naam_zonder_speciale_tekens_ongewijzigd(self):
        assert _xlsx_naar_bestandsdeel("AP06 week 23.xlsx") == "AP06 week 23"


class TestLogBestandsnaam:
    def test_format_bevat_alle_onderdelen(self, monkeypatch):
        monkeypatch.setattr(
            log_service,
            "date",
            type(
                "d",
                (),
                {
                    "today": staticmethod(
                        lambda: type("dt", (), {"strftime": lambda self, f: "2026-06-15"})()
                    )
                },
            ),
        )
        naam = _log_bestandsnaam("planning", "AP06_week23", "log")
        assert "planning" in naam
        assert "AP06_week23" in naam
        assert naam.endswith(".log")

    def test_datum_staat_vooraan(self):
        naam = _log_bestandsnaam("mendrix", "test", "log")
        # Datum-patroon YYYY-MM-DD staat vooraan
        assert naam[:4].isdigit()


class TestInitialiseertLogging:
    def test_maakt_logdir_aan(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        initialiseer_logging("test.xlsx")
        assert (tmp_path / "logs").exists()

    def test_maakt_vijf_logbestanden_aan(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("planning_test.xlsx")
        logbestanden = list((tmp_path / "logs").iterdir())
        assert len(logbestanden) == 6  # gdrive uitgecomment, nager toegevoegd

    def test_logbestanden_bevatten_xlsx_naam(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("AP06_week23.xlsx")
        namen = [f.name for f in (tmp_path / "logs").iterdir()]
        assert all("AP06_week23" in naam for naam in namen)

    def test_loggers_hebben_filehandler(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("test.xlsx")
        for logger_naam in [LOGGER_PLANNING, LOGGER_MENDRIX, LOGGER_CLAUDE, LOGGER_OSRM]:
            logger = logging.getLogger(logger_naam)
            assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    def test_dubbele_aanroep_voegt_geen_extra_handlers_toe(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("dup.xlsx")
        handlers_na_1 = len(logging.getLogger(LOGGER_PLANNING).handlers)
        initialiseer_logging("dup.xlsx")
        handlers_na_2 = len(logging.getLogger(LOGGER_PLANNING).handlers)
        assert handlers_na_1 == handlers_na_2

    def test_propagate_uitgeschakeld(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("test.xlsx")
        for logger_naam in [LOGGER_PLANNING, LOGGER_MENDRIX, LOGGER_CLAUDE, LOGGER_OSRM]:
            assert logging.getLogger(logger_naam).propagate is False

    def test_append_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("app.xlsx")
        logger = logging.getLogger(LOGGER_PLANNING)
        logger.info("eerste regel")
        _verwijder_handlers()
        initialiseer_logging("app.xlsx")
        logger.info("tweede regel")
        logbestanden = [f for f in (tmp_path / "logs").iterdir() if "planning" in f.name]
        inhoud = logbestanden[0].read_text(encoding="utf-8")
        assert "eerste regel" in inhoud
        assert "tweede regel" in inhoud

    def test_handlers_stapelen_niet_op_bij_veel_bestanden(self, tmp_path, monkeypatch):
        """Een langlopend serverproces mag niet eindeloos logbestanden open houden."""
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        for nummer in range(MAX_LOGBESTANDEN_PER_COMPONENT + 4):
            initialiseer_logging(f"week{nummer}.xlsx")
        logger = logging.getLogger(LOGGER_PLANNING)
        eigen = [h for h in logger.handlers if isinstance(h, _XlsxFileHandler)]
        assert len(eigen) == MAX_LOGBESTANDEN_PER_COMPONENT

    def test_logregel_belandt_niet_in_logbestand_van_ander_bestand(self, tmp_path, monkeypatch):
        """Gelijktijdige gebruikers mogen niet in elkaars logbestanden schrijven."""
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("bestand_a.xlsx")
        initialiseer_logging("bestand_b.xlsx")
        logging.getLogger(LOGGER_PLANNING).info("regel voor b")

        logdir = tmp_path / "logs"
        (bestand_a,) = [f for f in logdir.iterdir() if "planning" in f.name and "_a" in f.name]
        (bestand_b,) = [f for f in logdir.iterdir() if "planning" in f.name and "_b" in f.name]
        assert "regel voor b" in bestand_b.read_text(encoding="utf-8")
        assert "regel voor b" not in bestand_a.read_text(encoding="utf-8")

    def test_zet_actieve_xlsx_stuurt_naar_juiste_bestand(self, tmp_path, monkeypatch):
        """Na een rerun uit de cache moeten vervolgacties weer in het eigen log landen."""
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        _verwijder_handlers()
        initialiseer_logging("bestand_a.xlsx")
        initialiseer_logging("bestand_b.xlsx")

        zet_actieve_xlsx("bestand_a.xlsx")
        logging.getLogger(LOGGER_PLANNING).info("mendrix-actie op a")

        logdir = tmp_path / "logs"
        (bestand_a,) = [f for f in logdir.iterdir() if "planning" in f.name and "_a" in f.name]
        assert "mendrix-actie op a" in bestand_a.read_text(encoding="utf-8")


class TestDebugJsonPad:
    def test_retourneert_path_object(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        pad = debug_json_pad("planning.xlsx")
        assert isinstance(pad, Path)

    def test_pad_eindigt_op_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        pad = debug_json_pad("planning.xlsx")
        assert pad.suffix == ".json"

    def test_pad_bevat_xlsx_naam(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        pad = debug_json_pad("AP06_week23.xlsx")
        assert "AP06_week23" in pad.name

    def test_pad_bevat_debug_label(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "logs")
        pad = debug_json_pad("test.xlsx")
        assert "debug" in pad.name

    def test_maakt_logdir_aan(self, tmp_path, monkeypatch):
        logdir = tmp_path / "logs"
        monkeypatch.setattr(log_service, "LOG_DIR", logdir)
        debug_json_pad("test.xlsx")
        assert logdir.exists()


class TestSlaXlsxOp:
    def test_sla_xlsx_op_schrijft_bestand(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx")
        sla_xlsx_op("planning.xlsx", b"PK\x03\x04inhoud")
        bestanden = list((tmp_path / "xlsx").iterdir())
        assert len(bestanden) == 1
        assert bestanden[0].read_bytes() == b"PK\x03\x04inhoud"

    def test_bestandsnaam_bevat_xlsx_naam(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx")
        sla_xlsx_op("AP06_week23.xlsx", b"inhoud")
        namen = [f.name for f in (tmp_path / "xlsx").iterdir()]
        assert any("AP06_week23" in naam for naam in namen)

    def test_bestandsnaam_eindigt_op_xlsx(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx")
        sla_xlsx_op("planning.xlsx", b"inhoud")
        namen = [f.name for f in (tmp_path / "xlsx").iterdir()]
        assert all(naam.endswith(".xlsx") for naam in namen)

    def test_overschrijft_bestaand_bestand_zelfde_dag(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx")
        sla_xlsx_op("planning.xlsx", b"eerste")
        sla_xlsx_op("planning.xlsx", b"tweede")
        bestanden = list((tmp_path / "xlsx").iterdir())
        assert len(bestanden) == 1
        assert bestanden[0].read_bytes() == b"tweede"

    def test_maakt_map_aan(self, tmp_path, monkeypatch):
        xlsx_dir = tmp_path / "xlsx"
        monkeypatch.setattr(log_service, "XLSX_DIR", xlsx_dir)
        sla_xlsx_op("test.xlsx", b"inhoud")
        assert xlsx_dir.exists()


class TestRuimOudeLogs:
    def test_verwijdert_oude_bestanden(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path)
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx")
        oud_bestand = tmp_path / "oud.log"
        oud_bestand.write_text("oud")
        oud_tijd = (datetime.now() - timedelta(days=LOG_RETENTIE_DAGEN + 1)).timestamp()
        import os

        os.utime(oud_bestand, (oud_tijd, oud_tijd))
        _ruim_oude_logs_op()
        assert not oud_bestand.exists()

    def test_verwijdert_oude_xlsx(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path)
        xlsx_dir = tmp_path / "xlsx"
        xlsx_dir.mkdir()
        monkeypatch.setattr(log_service, "XLSX_DIR", xlsx_dir)
        oud_xlsx = xlsx_dir / "2026-05-01 - upload - planning.xlsx"
        oud_xlsx.write_bytes(b"PK\x03\x04")
        oud_tijd = (datetime.now() - timedelta(days=LOG_RETENTIE_DAGEN + 1)).timestamp()
        import os

        os.utime(oud_xlsx, (oud_tijd, oud_tijd))
        _ruim_oude_logs_op()
        assert not oud_xlsx.exists()

    def test_bewaart_nieuwe_bestanden(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path)
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx")
        nieuw_bestand = tmp_path / "nieuw.log"
        nieuw_bestand.write_text("nieuw")
        _ruim_oude_logs_op()
        assert nieuw_bestand.exists()

    def test_doet_niets_zonder_logdir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_service, "LOG_DIR", tmp_path / "bestaat_niet")
        monkeypatch.setattr(log_service, "XLSX_DIR", tmp_path / "xlsx_bestaat_niet")
        _ruim_oude_logs_op()  # geen exception


@pytest.fixture(autouse=True)
def herstel_loggers():
    """Herstel alle component-loggers naar hun standaardstaat na elke test."""
    yield
    for naam in [LOGGER_PLANNING, LOGGER_MENDRIX, LOGGER_CLAUDE, LOGGER_OSRM]:
        logger = logging.getLogger(naam)
        for h in list(logger.handlers):
            h.close()
            logger.removeHandler(h)
        logger.propagate = True
        logger.setLevel(logging.WARNING)
    log_service._lokaal.xlsx_deel = None


def _verwijder_handlers():
    """Verwijder bestaande FileHandlers van alle component-loggers om isolatie te garanderen."""
    for naam in [LOGGER_PLANNING, LOGGER_MENDRIX, LOGGER_CLAUDE, LOGGER_OSRM]:
        logger = logging.getLogger(naam)
        for h in list(logger.handlers):
            h.close()
            logger.removeHandler(h)
