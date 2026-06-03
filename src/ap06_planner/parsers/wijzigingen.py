"""
wijzigingen.py — Verwerkt de 'wijzigingen' kolom.

Gevonden patronen in de data:
  "Naar 12-18"        → vervang tijdvenster door 12:00-18:00
  "naar 8-10"         → idem
  "naar 12-18"        → idem (kleine letter)
  "naar 10.30-12.30"  → vervang tijdvenster door 10:30-12:30
  "Anouk na 12"       → Anouk werkt NA 12:00 op deze locatie
  "Tom tot 12"        → Tom werkt TOT 12:00 op deze locatie
  "Jeanne tot 12"     → Jeanne werkt TOT 12:00 op deze locatie
  "Johan na 12"       → Johan werkt NA 12:00 op deze locatie
  "Danielle hele dag" → Danielle werkt de hele dag (geen splitsing)
  "vervallen"         → regel overslaan
  "intrekken"         → regel overslaan
  "ingetrokken"       → regel overslaan
  "dagblok"           → negeren
  "ochtendblok"       → negeren
"""

import re

from ap06_planner.models.schemas import Tijdvenster
from ap06_planner.parsers.tijdvenster import normaliseer_tijd

# Tijdvervangpatroon: "Naar 12-18" of "naar 8.30-10.30"
TIJDVERVANG_PATROON = re.compile(
    r"\bnaar\s+(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\b",
    re.IGNORECASE,
)

# Persoon-splitsing: "Anouk na 12" / "Anouk vanaf 12", "Tom tot 12"
PERSOON_NA_PATROON = re.compile(
    r"^(\w+)\s+(?:na|vanaf)\s+(\d+(?:[.,]\d+)?)\s*$",
    re.IGNORECASE,
)
PERSOON_TOT_PATROON = re.compile(
    r"^(\w+)\s+tot\s+(\d+(?:[.,]\d+)?)\s*$",
    re.IGNORECASE,
)
PERSOON_HELE_DAG_PATROON = re.compile(
    r"^(\w+)\s+hele\s+dag\s*$",
    re.IGNORECASE,
)

# Negeerpatronen
NEGEER_PATROON = re.compile(
    r"\b(dagblok|ochtendblok)\b",
    re.IGNORECASE,
)


class WijzigingenResultaat:
    """Resultaat van wijzigingen-verwerking."""

    def __init__(self):
        self.tijdvervang: tuple[str, str] | None = None  # (begin, eind)
        self.persoon_start_na: str | None = None  # "12:00"
        self.persoon_eind_voor: str | None = None  # "12:00"
        self.persoon_hele_dag: bool = False
        self.negeer: bool = False


def verwerk_wijzigingen(
    wijzigingen: str | None,
    monsternemer_voornaam: str | None = None,
    claude_cache: dict[str, dict] | None = None,
) -> WijzigingenResultaat:
    """
    Verwerk de inhoud van de wijzigingen-kolom. Claude-first, regex als fallback.

    Args:
        wijzigingen: tekst uit de wijzigingen-kolom
        monsternemer_voornaam: voornaam van de huidige monsternemer (voor context)
        claude_cache: pre-computed batch resultaten van interpreteer_wijzigingen_batch
    """
    resultaat = WijzigingenResultaat()

    if not wijzigingen:
        return resultaat

    w = wijzigingen.strip()

    # Snel pad: dagblok/ochtendblok → negeer de wijziging, niet de regel
    if NEGEER_PATROON.search(w):
        return resultaat

    # Claude-first: gebruik pre-computed cache of directe call
    claude_data: dict | None = None
    if claude_cache is not None:
        claude_data = claude_cache.get(w)
    else:
        from ap06_planner.services.claude_service import interpreteer_wijzigingen

        claude_data = interpreteer_wijzigingen(w)

    if claude_data:
        return _pas_claude_toe(claude_data)

    # Fallback: regex (Claude niet beschikbaar of API-fout)
    return _regex_fallback(w)


def _pas_claude_toe(data: dict) -> WijzigingenResultaat:
    r = WijzigingenResultaat()
    if data.get("negeer"):
        r.negeer = True
    elif tv := data.get("tijdvervang"):
        r.tijdvervang = (tv[0], tv[1])
    elif t := data.get("start_na"):
        r.persoon_start_na = t
    elif t := data.get("eind_voor"):
        r.persoon_eind_voor = t
    elif data.get("hele_dag"):
        r.persoon_hele_dag = True
    return r


def _regex_fallback(w: str) -> WijzigingenResultaat:
    resultaat = WijzigingenResultaat()

    tijdmatch = TIJDVERVANG_PATROON.search(w)
    if tijdmatch:
        resultaat.tijdvervang = (
            normaliseer_tijd(tijdmatch.group(1)),
            normaliseer_tijd(tijdmatch.group(2)),
        )
        return resultaat

    if PERSOON_HELE_DAG_PATROON.match(w):
        resultaat.persoon_hele_dag = True
        return resultaat

    na_match = PERSOON_NA_PATROON.match(w)
    if na_match:
        resultaat.persoon_start_na = normaliseer_tijd(na_match.group(2))
        return resultaat

    tot_match = PERSOON_TOT_PATROON.match(w)
    if tot_match:
        resultaat.persoon_eind_voor = normaliseer_tijd(tot_match.group(2))
        return resultaat

    return resultaat


def pas_wijziging_toe(
    tijdvenster: Tijdvenster,
    wijziging: WijzigingenResultaat,
) -> Tijdvenster:
    """
    Pas een WijzigingenResultaat toe op een Tijdvenster.
    Retourneert een nieuw (aangepast) Tijdvenster.
    """
    if wijziging.tijdvervang:
        begin, eind = wijziging.tijdvervang
        return Tijdvenster(
            plaats=tijdvenster.plaats,
            klant_naam=tijdvenster.klant_naam,
            begintijd=begin,
            eindtijd=eind,
            type=tijdvenster.type,
            nummer=tijdvenster.nummer,
            origineel=f"{tijdvenster.origineel} [gewijzigd → {begin}-{eind}]",
        )

    if wijziging.persoon_eind_voor:
        return Tijdvenster(
            plaats=tijdvenster.plaats,
            klant_naam=tijdvenster.klant_naam,
            begintijd=tijdvenster.begintijd,
            eindtijd=wijziging.persoon_eind_voor,
            type=tijdvenster.type,
            nummer=tijdvenster.nummer,
            origineel=f"{tijdvenster.origineel} [tot {wijziging.persoon_eind_voor}]",
        )

    if wijziging.persoon_start_na:
        return Tijdvenster(
            plaats=tijdvenster.plaats,
            klant_naam=tijdvenster.klant_naam,
            begintijd=wijziging.persoon_start_na,
            eindtijd=tijdvenster.eindtijd,
            type=tijdvenster.type,
            nummer=tijdvenster.nummer,
            origineel=f"{tijdvenster.origineel} [na {wijziging.persoon_start_na}]",
        )

    return tijdvenster
