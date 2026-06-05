"""
osrm_service.py — Reistijdberekening via OSRM (Open Source Routing Machine).

Geocoding:
  - Google Maps Geocoding API (primair, als GOOGLE_MAPS_API_KEY beschikbaar)
    → beter bij afgekorte/ambigue plaatsnamen
  - Nominatim/OpenStreetMap (fallback, geen API-key nodig)

Routing:
  - Lokale OSRM op 192.168.4.105 (primair)
  - router.project-osrm.org (fallback)
"""

import math
import os

import requests

OSRM_BASE = os.getenv("OSRM_BASE_URL", "http://192.168.4.105:5000")
OSRM_FALLBACK = "http://router.project-osrm.org"

# Cache: alleen succesvolle geocode-resultaten (nooit None opslaan)
_google_cache: dict[str, tuple[float, float]] = {}
_nominatim_cache: dict[str, tuple[float, float]] = {}


def _geocodeer_google(adres: str) -> tuple[float, float] | None:
    """Google Maps Geocoding API — cache alleen successen."""
    if adres in _google_cache:
        return _google_cache[adres]

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": adres, "key": api_key, "language": "nl", "region": "nl"}
    try:
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            coords = (float(loc["lng"]), float(loc["lat"]))
            _google_cache[adres] = coords
            return coords
    except Exception:
        pass
    return None


def _geocodeer_nominatim(adres: str) -> tuple[float, float] | None:
    """Nominatim/OSM geocoding — cache alleen successen."""
    if adres in _nominatim_cache:
        return _nominatim_cache[adres]

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": adres, "format": "json", "limit": 1}
    headers = {"User-Agent": "AP06-Planner/0.1 (intern gebruik)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        resultaten = resp.json()
        if resultaten:
            coords = (float(resultaten[0]["lon"]), float(resultaten[0]["lat"]))
            _nominatim_cache[adres] = coords
            return coords
    except Exception:
        pass
    return None


def _geocodeer(adres: str) -> tuple[str, tuple[float, float]] | None:
    """
    Geocodeer adres. Retourneert (bron, coords) of None.
    Volgorde: Google Maps → Nominatim → koppelteken-fallback.
    """
    result = _geocodeer_google(adres)
    if result:
        return "Google Maps", result

    result = _geocodeer_nominatim(adres)
    if result:
        return "Nominatim", result

    # Koppelteken-fallback: "Heeswijk-Dinther" → "Heeswijk Dinther"
    if "-" in adres:
        alt = adres.replace("-", " ")
        result = _geocodeer_google(alt)
        if result:
            return "Google Maps", result
        result = _geocodeer_nominatim(alt)
        if result:
            return "Nominatim", result

    return None


def _osrm_route(start_lon: float, start_lat: float, eind_lon: float, eind_lat: float) -> int | None:
    """Probeer lokale OSRM, daarna publieke server als fallback. Retourneert minuten."""
    servers = [OSRM_BASE]
    if OSRM_BASE != OSRM_FALLBACK:
        servers.append(OSRM_FALLBACK)

    for base in servers:
        url = f"{base}/route/v1/driving/{start_lon},{start_lat};{eind_lon},{eind_lat}?overview=false"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                return round(data["routes"][0]["duration"] / 60)
        except Exception:
            continue

    return None


def bereken_reistijd_minuten(
    start_postcode: str,
    start_woonplaats: str,
    eind_postcode: str,
    eind_woonplaats: str,
) -> int | None:
    """Bereken de reistijd in minuten van start naar einde via OSRM."""
    start_query = (
        f"{start_postcode}, {start_woonplaats}, Nederland"
        if start_postcode
        else f"{start_woonplaats}, Nederland"
    )
    eind_query = (
        f"{eind_postcode}, {eind_woonplaats}, Nederland"
        if eind_postcode
        else f"{eind_woonplaats}, Nederland"
    )
    start_result = _geocodeer(start_query)
    eind_result = _geocodeer(eind_query)

    if not start_result or not eind_result:
        return None

    _, start_coords = start_result
    _, eind_coords = eind_result
    return _osrm_route(*start_coords, *eind_coords)


def bereken_aankomsttijd(
    vertrekplaats: str,
    woonplaats: str,
    woonplaats_postcode: str,
    eind_tijdvenster: str,
    uiterlijke_tijd: str | None,
    vertrekplaats_postcode: str = "",
) -> tuple[str, str, str]:
    """
    Bereken de gewensttijd (begin, eind, debug) voor ophalen bij monsternemer.

    Regels:
        - Reistijd < 60 min → +15 min buffer, ≥ 60 min → +30 min buffer
        - Altijd afronden naar boven op kwartier (13:09 → 13:15)

    Returns:
        (gewensttijd_begin, gewensttijd_eind, debug_str)
    """
    eindtijd_str = uiterlijke_tijd or "23:59"

    eind_query = (
        f"{woonplaats_postcode}, {woonplaats}, Nederland"
        if woonplaats_postcode
        else f"{woonplaats}, Nederland"
    )
    eind_result = _geocodeer(eind_query)
    if not eind_result:
        debug = (
            f"{eind_tijdvenster} klaar in {vertrekplaats} → {woonplaats}: "
            f"geocoding thuisadres mislukt → gewensttijd {eind_tijdvenster}"
        )
        return eind_tijdvenster, eindtijd_str, debug

    geocodeer_bron, eind_coords = eind_result

    vertrek_query = (
        f"{vertrekplaats_postcode}, {vertrekplaats}, Nederland"
        if vertrekplaats_postcode
        else f"{vertrekplaats}, Nederland"
    )
    vertrek_result = _geocodeer(vertrek_query)
    if not vertrek_result:
        debug = (
            f"{eind_tijdvenster} klaar in {vertrekplaats} → {woonplaats}: "
            f"geocoding vertrekplaats mislukt → gewensttijd {eind_tijdvenster}"
        )
        return eind_tijdvenster, eindtijd_str, debug

    vertrek_bron, vertrek_coords = vertrek_result
    bron_label = vertrek_bron

    reistijd = _osrm_route(*vertrek_coords, *eind_coords)

    if reistijd is None:
        debug = (
            f"{eind_tijdvenster} klaar in {vertrekplaats} → {woonplaats}: "
            f"route onbekend (OSRM fout) → gewensttijd {eind_tijdvenster}"
        )
        return eind_tijdvenster, eindtijd_str, debug

    buffer = 15 if reistijd < 60 else 30
    drempel = "< 60 min" if reistijd < 60 else "≥ 60 min"

    eind_uren, eind_min = map(int, eind_tijdvenster.split(":"))
    aankomst_min_totaal = eind_uren * 60 + eind_min + reistijd + buffer
    aankomst_min_totaal = math.ceil(aankomst_min_totaal / 15) * 15

    aankomst_uren = (aankomst_min_totaal // 60) % 24
    aankomst_min = aankomst_min_totaal % 60
    aankomsttijd = f"{aankomst_uren:02d}:{aankomst_min:02d}"

    debug = (
        f"{eind_tijdvenster} klaar in {vertrekplaats} → {woonplaats}: "
        f"{reistijd} min ({drempel} → +{buffer} min buffer) → gewensttijd {aankomsttijd} "
        f"[{bron_label} + OSRM]"
    )

    return aankomsttijd, eindtijd_str, debug
