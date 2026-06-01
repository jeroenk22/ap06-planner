"""
tijdvenster.py — Verwerkt tijdvensterstrings.

Voorbeelden uit de data:
  "Bladel TonTrans 7-18 LAD17"      → {plaats: Bladel, start: 07:00, eind: 18:00, type: LAD, nr: 17}
  "Zundert Dams 6-18 LAD1"          → {plaats: Zundert, start: 06:00, eind: 18:00, type: LAD, nr: 1}
  "Veendam VanOosten 10-12 LAD2"    → {plaats: Veendam, start: 10:00, eind: 12:00, type: LAD, nr: 2}
  "Eersel VanMeer 8.30-10.30 LAD"   → {plaats: Eersel, start: 08:30, eind: 10:30, type: LAD}
  "Marrum JB 7-9 LOS"               → {plaats: Marrum, start: 07:00, eind: 09:00, type: LOS}
  "Oude-tonge BAX 5.30-7.30 LAD"   → {plaats: Oude-tonge, start: 05:30, eind: 07:30}

Tijdvenster patroon: \d+[.]\d+-\d+[.]\d+ of \d+-\d+
"""

import re

from ap06_planner.models.schemas import Tijdvenster

# Patroon: "7-18", "8.30-10.30", "11.30-13.30", "5.30-7.30"
TIJDVENSTER_PATROON = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)"
)

# Type: LAD of LOS, optioneel gevolgd door een nummer
TYPE_PATROON = re.compile(r"\b(LAD|LOS)(\d+(?:\.\d+)?)?\b")


def normaliseer_tijd(tijdstr: str) -> str:
    """
    Converteert "7", "7.30", "18", "10.30" naar "07:00", "07:30", "18:00", "10:30".
    Ondersteunt zowel punt als komma als decimaalteken.
    """
    tijdstr = tijdstr.replace(",", ".")
    if "." in tijdstr:
        uren, minuten = tijdstr.split(".", 1)
        return f"{int(uren):02d}:{int(minuten):02d}"
    return f"{int(tijdstr):02d}:00"


def parse_tijdvenster(tekst: str) -> Tijdvenster | None:
    """
    Parseer een tijdvensterstring naar een Tijdvenster object.
    Geeft None terug als er geen tijdvenster gevonden wordt.
    """
    if not tekst:
        return None

    tekst = tekst.strip()

    # Zoek tijdvenster
    tv_match = TIJDVENSTER_PATROON.search(tekst)
    if not tv_match:
        return None

    start_raw = tv_match.group(1)
    eind_raw = tv_match.group(2)
    begintijd = normaliseer_tijd(start_raw)
    eindtijd = normaliseer_tijd(eind_raw)

    # Zoek type (LAD/LOS) en nummer
    type_match = TYPE_PATROON.search(tekst)
    lad_los_type = type_match.group(1) if type_match else "LAD"
    nummer = type_match.group(2) if (type_match and type_match.group(2)) else None

    # Klant-naam: woord(en) tussen plaatsnaam en tijdvenster
    # Tekst voor het tijdvenster: "Bladel TonTrans 7-18 LAD17"
    voor_tijdvenster = tekst[: tv_match.start()].strip()
    delen = voor_tijdvenster.split()
    if len(delen) >= 2:
        plaats = delen[0]
        klant_naam = " ".join(delen[1:])
    elif len(delen) == 1:
        plaats = delen[0]
        klant_naam = ""
    else:
        plaats = ""
        klant_naam = ""

    return Tijdvenster(
        plaats=plaats,
        klant_naam=klant_naam,
        begintijd=begintijd,
        eindtijd=eindtijd,
        type=lad_los_type,
        nummer=nummer,
        origineel=tekst,
    )


def vergelijk_tijdvensters(tv_lijst: list[Tijdvenster]) -> Tijdvenster | None:
    """
    Kies het laatste tijdvenster uit een lijst:
    1. Hoogste begintijd
    2. Bij gelijke begintijd: verste van woonplaats (niet hier bepaald — geef alle kandidaten)
    Retourneert het tijdvenster met de hoogste begintijd.
    """
    if not tv_lijst:
        return None
    # Sorteer op begintijd (hh:mm string sortering werkt correct)
    return max(tv_lijst, key=lambda tv: tv.begintijd)
