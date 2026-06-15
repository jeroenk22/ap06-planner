"""
log_service.py — Centrale logging setup voor AP06 Planner.

Maakt per xlsx-inlezing zes logbestanden aan in de logs/ map:
  {datum} - planning  - {xlsx}.log  — algemeen planningsproces
  {datum} - mendrix   - {xlsx}.log  — SOAP-interacties met Mendrix
  {datum} - claude    - {xlsx}.log  — Claude API-calls en tokengebruik
  {datum} - osrm      - {xlsx}.log  — geocoding en reistijdberekeningen
  {datum} - gdrive    - {xlsx}.log  — Google Drive uploads en opruimen
  {datum} - textmebot - {xlsx}.log  — WhatsApp berichten via TextMeBot
  {datum} - debug     - {xlsx}.json — volledige JSON output (Stadium 1)

Retentie: bestanden ouder dan LOG_RETENTIE_DAGEN worden automatisch verwijderd.
"""

import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

LOG_DIR = Path("logs")
XLSX_DIR = LOG_DIR / "xlsx"
LOG_RETENTIE_DAGEN = 30

# Logger-namen per component — gebruik deze namen in de services
LOGGER_PLANNING = "ap06.planning"
LOGGER_MENDRIX = "ap06.mendrix"
LOGGER_CLAUDE = "ap06.claude"
LOGGER_OSRM = "ap06.osrm"
LOGGER_GDRIVE = "ap06.gdrive"
LOGGER_TEXTMEBOT = "ap06.textmebot"

_COMPONENT_LOGGERS = {
    "planning": LOGGER_PLANNING,
    "mendrix": LOGGER_MENDRIX,
    "claude": LOGGER_CLAUDE,
    "osrm": LOGGER_OSRM,
    # "gdrive": LOGGER_GDRIVE,  # TODO: terug aanzetten zodra Drive-upload actief is
    "textmebot": LOGGER_TEXTMEBOT,
}


class _KortLevelFormatter(logging.Formatter):
    """Formatter met verkorte level-namen voor compacte, leesbare logregels."""

    _NIVEAUS = {
        logging.DEBUG:    "DEBUG",
        logging.INFO:     "INFO ",
        logging.WARNING:  "WARN ",
        logging.ERROR:    "ERROR",
        logging.CRITICAL: "CRIT ",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.kort_level = self._NIVEAUS.get(record.levelno, record.levelname[:5])
        return super().format(record)


def _xlsx_naar_bestandsdeel(xlsx_naam: str) -> str:
    """Haal de bestandsnaam zonder extensie op en saniteer voor gebruik in een bestandsnaam."""
    naam = Path(xlsx_naam).stem
    # Vervang tekens die niet toegestaan zijn in Windows-bestandsnamen
    naam = re.sub(r'[\\/*?:"<>|]', "-", naam)
    return naam


def _log_bestandsnaam(component: str, xlsx_deel: str, extensie: str) -> str:
    """Bouw de logbestandsnaam op: '{datum} - {component} - {xlsx}.{extensie}'."""
    datum = date.today().strftime("%Y-%m-%d")
    return f"{datum} - {component} - {xlsx_deel}.{extensie}"


def _ruim_oude_logs_op() -> None:
    """Verwijder log- en xlsx-bestanden ouder dan LOG_RETENTIE_DAGEN dagen."""
    grens = datetime.now() - timedelta(days=LOG_RETENTIE_DAGEN)
    for zoekmap in (LOG_DIR, XLSX_DIR):
        if not zoekmap.exists():
            continue
        for pad in zoekmap.iterdir():
            if pad.is_file():
                gewijzigd = datetime.fromtimestamp(pad.stat().st_mtime)
                if gewijzigd < grens:
                    try:
                        pad.unlink()
                    except OSError:
                        pass  # bestand al verwijderd of vergrendeld — sla over


def initialiseer_logging(xlsx_naam: str) -> None:
    """
    Stel logging in voor een xlsx-inlezing.

    Voegt FileHandlers toe aan de vier component-loggers (planning, mendrix,
    claude, osrm). Als dezelfde xlsx op dezelfde dag opnieuw wordt ingelezen,
    worden de regels aan het bestaande logbestand toegevoegd (mode='a').

    Verwijdert ook automatisch logbestanden ouder dan LOG_RETENTIE_DAGEN.
    Aanroepen zodra de xlsx-bestandsnaam bekend is, vóór de verwerking start.
    """
    LOG_DIR.mkdir(exist_ok=True)
    _ruim_oude_logs_op()

    xlsx_deel = _xlsx_naar_bestandsdeel(xlsx_naam)
    formatter = _KortLevelFormatter(
        fmt="[%(asctime)s] [%(kort_level)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    for component, logger_naam in _COMPONENT_LOGGERS.items():
        logger = logging.getLogger(logger_naam)
        logger.setLevel(logging.DEBUG)

        pad = LOG_DIR / _log_bestandsnaam(component, xlsx_deel, "log")

        # Voeg alleen een nieuwe handler toe als die er nog niet is voor dit pad
        al_aanwezig = any(
            isinstance(h, logging.FileHandler)
            and Path(h.baseFilename).resolve() == pad.resolve()
            for h in logger.handlers
        )
        if not al_aanwezig:
            handler = logging.FileHandler(pad, encoding="utf-8", mode="a")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Voorkom dubbele output via de root logger
        logger.propagate = False


def sla_xlsx_op(xlsx_naam: str, inhoud: bytes) -> None:
    """
    Sla de geüploade xlsx op in logs/xlsx/ voor 30 dagen.
    Bestandsnaam: '{datum} - {xlsx_naam}.xlsx'
    Overschrijft een bestaand bestand van dezelfde dag stilletjes.
    """
    XLSX_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_deel = _xlsx_naar_bestandsdeel(xlsx_naam)
    pad = XLSX_DIR / _log_bestandsnaam("upload", xlsx_deel, "xlsx")
    try:
        pad.write_bytes(inhoud)
    except OSError:
        pass  # schrijffout (schijf vol, rechten) — niet fataal


def debug_json_pad(xlsx_naam: str) -> Path:
    """Geeft het pad terug waar de debug JSON voor deze inlezing opgeslagen wordt."""
    LOG_DIR.mkdir(exist_ok=True)
    xlsx_deel = _xlsx_naar_bestandsdeel(xlsx_naam)
    return LOG_DIR / _log_bestandsnaam("debug", xlsx_deel, "json")
