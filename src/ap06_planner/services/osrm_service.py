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

import logging
import math
import os

import requests

_log = logging.getLogger("ap06.osrm")

OSRM_BASE = os.getenv("OSRM_BASE_URL", "http://192.168.4.105:5000")
OSRM_FALLBACK = "http://router.project-osrm.org"

# Reistijdbuffers: bij korte ritten (+15 min), bij lange ritten (+30 min)
_REISTIJD_DREMPEL_MIN = 60
_BUFFER_KORT_MIN = 15
_BUFFER_LANG_MIN = 30

# Afronden naar boven op kwartieren (15 minuten)
_KWARTIER_MIN = 15

# Cache: alleen succesvolle geocode-resultaten (nooit None opslaan)
_google_cache: dict[str, tuple[float, float]] = {}
_nominatim_cache: dict[str, tuple[float, float]] = {}


def _adres_query(postcode: str, woonplaats: str) -> str:
    """Bouw een geocoding-zoekstring: 'postcode, woonplaats, Nederland' of 'woonplaats, Nederland'."""
    if postcode:
        return f"{postcode}, {woonplaats}, Nederland"
    return f"{woonplaats}, Nederland"


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
        status = data.get("status")
        if status == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            coords = (float(loc["lng"]), float(loc["lat"]))
            _google_cache[adres] = coords
            _log.debug("Google geocode OK: %s → %.4f, %.4f", adres, coords[1], coords[0])
            return coords
        if status in ("OVER_QUERY_LIMIT", "REQUEST_DENIED"):
            _log.warning(
                "Google geocoding limiet/auth: status=%s voor '%s' — "
                "controleer API-key quota of billing in Google Cloud Console",
                status,
                adres,
            )
        elif status == "ZERO_RESULTS":
            _log.debug("Google geocode: adres niet gevonden: '%s'", adres)
        elif status:
            _log.warning("Google geocode onverwacht: status=%s voor '%s'", status, adres)
    except Exception as e:
        _log.debug("Google geocode fout voor '%s': %s", adres, e, exc_info=True)
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
        if resp.status_code == 429:
            _log.warning("Nominatim rate limit (429) voor '%s' — te veel requests", adres)
            return None
        resp.raise_for_status()
        resultaten = resp.json()
        if resultaten:
            coords = (float(resultaten[0]["lon"]), float(resultaten[0]["lat"]))
            _nominatim_cache[adres] = coords
            _log.debug("Nominatim geocode OK: %s → %.4f, %.4f", adres, coords[1], coords[0])
            return coords
    except Exception as e:
        _log.debug("Nominatim geocode fout voor '%s': %s", adres, e, exc_info=True)
    return None


def _geocodeer(adres: str) -> tuple[str, tuple[float, float]] | None:
    """
    Geocodeer adres. Retourneert (bron, coords) of None.
    Volgorde: Google Maps → Nominatim → koppelteken-fallback.
    INFO alleen bij eerste succesvolle API-call; cache-hits zijn DEBUG.
    """
    google_gecached = adres in _google_cache
    result = _geocodeer_google(adres)
    if result:
        if google_gecached:
            _log.debug("Geocode cache (Google): '%s'", adres)
        else:
            _log.info("Geocode OK via Google Maps: '%s'", adres)
        return "Google Maps", result

    nominatim_gecached = adres in _nominatim_cache
    result = _geocodeer_nominatim(adres)
    if result:
        if nominatim_gecached:
            _log.debug("Geocode cache (Nominatim): '%s'", adres)
        else:
            _log.info("Geocode OK via Nominatim (Google mislukt): '%s'", adres)
        return "Nominatim", result

    # Koppelteken-fallback: "Heeswijk-Dinther" → "Heeswijk Dinther"
    if "-" in adres:
        alt = adres.replace("-", " ")
        result = _geocodeer_google(alt)
        if result:
            _log.info("Geocode OK via Google Maps (koppelteken-fallback): '%s' → '%s'", adres, alt)
            return "Google Maps", result
        result = _geocodeer_nominatim(alt)
        if result:
            _log.info("Geocode OK via Nominatim (koppelteken-fallback): '%s' → '%s'", adres, alt)
            return "Nominatim", result

    _log.warning("Geocoding mislukt voor '%s' — geen resultaat van Google Maps of Nominatim", adres)
    return None


def _osrm_route(start_lon: float, start_lat: float, eind_lon: float, eind_lat: float) -> int | None:
    """Probeer lokale OSRM, daarna publieke server als fallback. Retourneert minuten."""
    servers = [OSRM_BASE]
    if OSRM_BASE != OSRM_FALLBACK:
        servers.append(OSRM_FALLBACK)

    for base in servers:
        url = (
            f"{base}/route/v1/driving/{start_lon},{start_lat};{eind_lon},{eind_lat}?overview=false"
        )
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 429:
                _log.warning("OSRM rate limit (429) via %s", base)
                continue
            if resp.status_code >= 500:
                _log.warning("OSRM serverfout HTTP %d via %s", resp.status_code, base)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                minuten = round(data["routes"][0]["duration"] / 60)
                _log.debug("OSRM route via %s: %d min", base, minuten)
                return minuten
        except Exception:
            _log.debug("OSRM fout via %s", base, exc_info=True)
            continue

    _log.warning(
        "OSRM route mislukt voor alle servers: %.4f,%.4f → %.4f,%.4f",
        start_lat,
        start_lon,
        eind_lat,
        eind_lon,
    )
    return None


def bereken_reistijd_minuten(
    start_postcode: str,
    start_woonplaats: str,
    eind_postcode: str,
    eind_woonplaats: str,
) -> int | None:
    """Bereken de reistijd in minuten van start naar einde via OSRM."""
    start_query = _adres_query(start_postcode, start_woonplaats)
    eind_query = _adres_query(eind_postcode, eind_woonplaats)
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

    eind_query = _adres_query(woonplaats_postcode, woonplaats)
    eind_result = _geocodeer(eind_query)
    if not eind_result:
        _log.warning("Aankomsttijd niet berekend: thuisadres '%s' niet geocodeerbaar", eind_query)
        debug = (
            f"{eind_tijdvenster} klaar in {vertrekplaats} → {woonplaats}: "
            f"geocoding thuisadres mislukt → gewensttijd {eind_tijdvenster}"
        )
        return eind_tijdvenster, eindtijd_str, debug

    geocodeer_bron, eind_coords = eind_result

    vertrek_query = _adres_query(vertrekplaats_postcode, vertrekplaats)
    vertrek_result = _geocodeer(vertrek_query)
    if not vertrek_result:
        _log.warning(
            "Aankomsttijd niet berekend: vertrekplaats '%s' niet geocodeerbaar", vertrek_query
        )
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

    buffer = _BUFFER_KORT_MIN if reistijd < _REISTIJD_DREMPEL_MIN else _BUFFER_LANG_MIN
    drempel = (
        f"< {_REISTIJD_DREMPEL_MIN} min"
        if reistijd < _REISTIJD_DREMPEL_MIN
        else f"≥ {_REISTIJD_DREMPEL_MIN} min"
    )

    eind_uren, eind_min = map(int, eind_tijdvenster.split(":"))
    aankomst_min_totaal = eind_uren * 60 + eind_min + reistijd + buffer
    aankomst_min_totaal = math.ceil(aankomst_min_totaal / _KWARTIER_MIN) * _KWARTIER_MIN

    aankomst_uren = (aankomst_min_totaal // 60) % 24
    aankomst_min = aankomst_min_totaal % 60
    aankomsttijd = f"{aankomst_uren:02d}:{aankomst_min:02d}"

    debug = (
        f"{eind_tijdvenster} klaar in {vertrekplaats} → {woonplaats}: "
        f"{reistijd} min ({drempel} → +{buffer} min buffer) → gewensttijd {aankomsttijd} "
        f"[{bron_label} + OSRM]"
    )

    _log.info(
        "%s → %s: %d min + %d min buffer → aankomst %s",
        vertrekplaats,
        woonplaats,
        reistijd,
        buffer,
        aankomsttijd,
    )
    return aankomsttijd, eindtijd_str, debug
