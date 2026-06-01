"""
osrm_service.py — Reistijdberekening via OSRM (Open Source Routing Machine).

Gebruikt de publieke OSRM demo server: http://router.project-osrm.org
Voor productie: draai je eigen OSRM op 192.168.4.105

Retourneert reistijd in minuten.
"""

import os
import requests

OSRM_BASE = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")


def bereken_reistijd_minuten(
    start_postcode: str,
    start_woonplaats: str,
    eind_postcode: str,
    eind_woonplaats: str,
) -> int | None:
    """
    Bereken de reistijd in minuten van start naar einde via OSRM.
    Gebruikt geocoding via Nominatim (OpenStreetMap) voor adres→coördinaten.

    Args:
        start_postcode / start_woonplaats: vertreklocatie (bijv. "5531 DD", "Bladel")
        eind_postcode / eind_woonplaats:   eindlocatie (bijv. "5345 CC", "Oss")

    Returns:
        Reistijd in minuten, of None bij een fout.
    """
    start_coords = _geocodeer(f"{start_postcode}, {start_woonplaats}, Nederland")
    eind_coords = _geocodeer(f"{eind_postcode}, {eind_woonplaats}, Nederland")

    if not start_coords or not eind_coords:
        return None

    start_lon, start_lat = start_coords
    eind_lon, eind_lat = eind_coords

    url = (
        f"{OSRM_BASE}/route/v1/driving/"
        f"{start_lon},{start_lat};{eind_lon},{eind_lat}"
        f"?overview=false"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            seconden = data["routes"][0]["duration"]
            return round(seconden / 60)
    except Exception:
        pass

    return None


def bereken_aankomsttijd(
    vertrekplaats: str,
    vertrekplaats_postcode: str,
    woonplaats: str,
    woonplaats_postcode: str,
    eind_tijdvenster: str,  # "18:00"
    uiterlijke_tijd: str | None,  # "21:30" uit monsternemer-database
) -> tuple[str, str]:
    """
    Bereken de gewensttijd (begin, eind) voor ophalen bij monsternemer.

    Regels:
    - Reistijd < 60 min → voeg 15 min buffer toe
    - Reistijd ≥ 60 min → voeg 30 min buffer toe
    - eindtijd = uiterlijke_tijd van monsternemer (of "23:59")
    """
    reistijd = bereken_reistijd_minuten(
        vertrekplaats_postcode, vertrekplaats,
        woonplaats_postcode, woonplaats,
    )

    if reistijd is None:
        # Fallback: geen reistijd bekend
        return "00:00", uiterlijke_tijd or "23:59"

    buffer = 15 if reistijd < 60 else 30
    totaal_minuten = reistijd + buffer

    # Bereken aankomsttijd
    eind_uren, eind_min = map(int, eind_tijdvenster.split(":"))
    aankomst_min_totaal = eind_uren * 60 + eind_min + totaal_minuten
    aankomst_uren = (aankomst_min_totaal // 60) % 24
    aankomst_min = aankomst_min_totaal % 60

    aankomsttijd = f"{aankomst_uren:02d}:{aankomst_min:02d}"
    eindtijd = uiterlijke_tijd or "23:59"

    return aankomsttijd, eindtijd


def _geocodeer(adres: str) -> tuple[float, float] | None:
    """Geocodeer een adres naar (lon, lat) via Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": adres, "format": "json", "limit": 1}
    headers = {"User-Agent": "AP06-Planner/0.1 (intern gebruik)"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        resultaten = resp.json()
        if resultaten:
            lon = float(resultaten[0]["lon"])
            lat = float(resultaten[0]["lat"])
            return lon, lat
    except Exception:
        pass

    return None
