"""
xlsx_parser.py — Leest AP06-planningsbestanden in.

Kritieke bevindingen uit analyse van 6 voorbeeldbestanden:
- Laad ALTIJD met data_only=True (anders formules zoals =AK4 in plaats van waarden)
- Tabblad-selectie: kies tabs met "dd-mm Dagnaam" patroon, sla Blad2/Blad129 over
- Header-detectie: scan rijen 1-5 op aanwezigheid van 'Monsternemer'
- 2 kolomformaten: standaard (E=Locatie, F=Klant) en Eurofins (E=Klant)
- Datum: rij 1 kolom C (of B bij Eurofins) als datetime object
- Leeg monsternemer = skip; "vervallen"/"intrekken"/"ingetrokken" in wijzigingen = skip
"""

import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from ap06_planner.models.schemas import PlanningRegel

# Patroon voor geldige plannings-tabbladen: "11-5 maandag", "13-4 Maandag", "9-5 Zaterdag"
GELDIG_TABBLAD_PATROON = re.compile(
    r"\d{1,2}-\d{1,2}\s+(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)",
    re.IGNORECASE,
)

SKIP_WIJZIGINGEN = re.compile(
    r"\b(vervallen|intrekken|ingetrokken)\b",
    re.IGNORECASE,
)


def selecteer_tabbladen(sheetnames: list[str]) -> list[str]:
    """Selecteer tabbladen met een datumDagnaam-patroon. Sla utility-tabs over."""
    return [s for s in sheetnames if GELDIG_TABBLAD_PATROON.search(s)]


def detecteer_datum(ws, eurofins_formaat: bool) -> str | None:
    """Extraheer de planningsdatum (dd-mm-jjjj) uit de eerste rij."""
    col_idx = 1 if eurofins_formaat else 2  # B of C (0-indexed)
    for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
        if len(row) > col_idx and isinstance(row[col_idx], datetime):
            dt = row[col_idx]
            return dt.strftime("%d-%m-%Y")
    return None


def detecteer_dagnaam(ws) -> str | None:
    """Extraheer de dagnaam (bijv. 'maandag') uit rij 1."""
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
        for cel in row:
            if isinstance(cel, str) and cel.lower() in {
                "maandag", "dinsdag", "woensdag", "donderdag",
                "vrijdag", "zaterdag", "zondag"
            }:
                return cel.lower()
    return None


def detecteer_headers(ws) -> tuple[int, dict[str, int]] | tuple[None, None]:
    """
    Zoek de headerrij (max rij 5) en retourneer (rijnummer, kolom→index dict).
    Ondersteunt zowel standaard- als Eurofins Agro-formaat.
    """
    for rij_nr, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), 1):
        row_lower = [
            str(v).strip().lower() if v is not None else "" for v in row
        ]
        if "monsternemer" in row_lower:
            kolommap = {}
            for idx, header in enumerate(row_lower):
                if header:
                    kolommap[header] = idx
            return rij_nr, kolommap
    return None, None


def is_eurofins_formaat(kolommap: dict[str, int]) -> bool:
    """
    Eurofins Agro formaat heeft 'laadlocatie' als kolom, standaard heeft 'locatie'.
    In Eurofins staat het tijdvenster in de 'klant' kolom (niet in 'locatie').
    """
    return "laadlocatie" in kolommap


def lees_planningsbestand(
    bron: Path | BytesIO,
) -> list[dict]:
    """
    Hoofdfunctie: lees een xlsx-planningsbestand in.
    Retourneert een lijst van dicts met {tabblad, datum, dagnaam, regels: [PlanningRegel]}.
    """
    wb = load_workbook(bron, data_only=True, read_only=False)

    geselecteerde_tabs = selecteer_tabbladen(wb.sheetnames)
    if not geselecteerde_tabs:
        # Fallback: gebruik het eerste tabblad als er geen match is
        geselecteerde_tabs = [wb.sheetnames[0]]

    resultaten = []

    for tab_naam in geselecteerde_tabs:
        ws = wb[tab_naam]

        header_rij, kolommap = detecteer_headers(ws)
        if header_rij is None:
            continue

        eurofins = is_eurofins_formaat(kolommap)
        datum = detecteer_datum(ws, eurofins_formaat=eurofins)
        dagnaam = detecteer_dagnaam(ws)

        # Tabblad-naam geeft ook datuminfo: "13-4 Maandag"
        if dagnaam is None:
            match = GELDIG_TABBLAD_PATROON.search(tab_naam)
            if match:
                dagnaam = match.group(1).lower()

        regels = _verwerk_rijen(ws, header_rij, kolommap, eurofins)

        resultaten.append({
            "tabblad": tab_naam,
            "datum": datum,
            "dagnaam": dagnaam,
            "regels": regels,
        })

    wb.close()
    return resultaten


def _verwerk_rijen(
    ws,
    header_rij: int,
    kolommap: dict[str, int],
    eurofins: bool,
) -> list[PlanningRegel]:
    """Verwerk alle datarijen onder de headerrij."""
    regels = []

    # Bepaal kolomindices op basis van formaat
    idx_monsternemer = kolommap.get("monsternemer")
    idx_wijzigingen = kolommap.get("wijzigingen")

    if eurofins:
        idx_locatie = None
        idx_klant = kolommap.get("klant")  # tijdvenster staat hier
    else:
        idx_locatie = kolommap.get("locatie")
        idx_klant = kolommap.get("klant")

    for row in ws.iter_rows(min_row=header_rij + 1, values_only=True):
        # Skip volledig lege rijen
        if all(v is None for v in row):
            continue

        monsternemer_naam = _cel(row, idx_monsternemer)
        if not monsternemer_naam:
            continue  # Geen monsternemer = skip

        wijzigingen = _cel(row, idx_wijzigingen)
        locatie_raw = _cel(row, idx_locatie) if idx_locatie is not None else None
        klant_raw = _cel(row, idx_klant) if idx_klant is not None else None

        # Skip bij "vervallen" / "intrekken" / "ingetrokken"
        if wijzigingen and SKIP_WIJZIGINGEN.search(wijzigingen):
            regels.append(PlanningRegel(
                monsternemer_naam=monsternemer_naam,
                wijzigingen=wijzigingen,
                locatie_raw=locatie_raw,
                klant_raw=klant_raw,
                overgeslagen=True,
                reden_overgeslagen=f"wijzigingen: '{wijzigingen}'",
            ))
            continue

        regels.append(PlanningRegel(
            monsternemer_naam=monsternemer_naam,
            wijzigingen=wijzigingen,
            locatie_raw=locatie_raw,
            klant_raw=klant_raw,
        ))

    return regels


def _cel(row: tuple, idx: int | None) -> str | None:
    """Haal celwaarde op en strip whitespace. Geeft None bij lege cellen."""
    if idx is None or idx >= len(row):
        return None
    val = row[idx]
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None
