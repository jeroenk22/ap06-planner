"""
nager_service.py — Controleert Nederlandse nationale feestdagen via Nager.Date API.
API docs: https://date.nager.at/nl/api
"""

import logging
from datetime import date, timedelta

import requests

_log = logging.getLogger("ap06.nager")

NAGER_BASE_URL = "https://date.nager.at/api/v3"
COUNTRY_CODE = "NL"

_feestdagen_cache: dict[int, set[date]] = {}


def haal_feestdagen(jaar: int) -> set[date]:
    """Haal alle NL nationale feestdagen op voor een jaar. Resultaat wordt gecached."""
    if jaar in _feestdagen_cache:
        _log.debug("Feestdagen %d uit cache (%d feestdagen)", jaar, len(_feestdagen_cache[jaar]))
        return _feestdagen_cache[jaar]

    url = f"{NAGER_BASE_URL}/PublicHolidays/{jaar}/{COUNTRY_CODE}"
    _log.debug("Ophalen feestdagen %d via %s", jaar, url)
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        feestdagen = {date.fromisoformat(item["date"]) for item in data}
        _feestdagen_cache[jaar] = feestdagen
        _log.info(
            "Feestdagen %d opgehaald: %d feestdagen — %s",
            jaar,
            len(feestdagen),
            ", ".join(sorted(d.strftime("%d-%m") for d in feestdagen)),
        )
        return feestdagen
    except requests.HTTPError as e:
        _log.warning(
            "HTTP-fout bij ophalen feestdagen %d: %s — geen feestdagen aangenomen",
            jaar,
            e,
            exc_info=True,
        )
        return set()
    except requests.RequestException as e:
        _log.warning(
            "Netwerkfout bij ophalen feestdagen %d: %s — geen feestdagen aangenomen",
            jaar,
            type(e).__name__,
            exc_info=True,
        )
        return set()
    except Exception as e:
        _log.warning(
            "Onverwachte fout bij ophalen feestdagen %d: %s — geen feestdagen aangenomen",
            jaar,
            type(e).__name__,
            exc_info=True,
        )
        return set()


def is_feestdag(dag: date) -> bool:
    """Controleer of een dag een NL nationale feestdag is."""
    feestdagen = haal_feestdagen(dag.year)
    gevonden = dag in feestdagen
    if gevonden:
        _log.debug("Feestdag gedetecteerd: %s", dag.strftime("%d-%m-%Y"))
    return gevonden


DAGNUMMER_NAAR_AFKORTING = {
    0: "ma",
    1: "di",
    2: "wo",
    3: "do",
    4: "vr",
    5: "za",
    6: "zo",
}

AFKORTING_NAAR_DAGNUM = {v: k for k, v in DAGNUMMER_NAAR_AFKORTING.items()}


def eerstvolgende_ophaaldag(
    vanaf: date,
    ophaaldagen: list[str],
    sla_feestdagen_over: bool = True,
) -> tuple[date, bool]:
    """
    Zoek de eerstvolgende ophaaldag vanaf een gegeven datum.

    Args:
        vanaf: de planningsdatum
        ophaaldagen: lijst van afkortingen, bijv. ["ma", "wo"]
        sla_feestdagen_over: als True, sla feestdagen over en neem de volgende ophaaldag

    Returns:
        Tuple van (datum, is_feestdag_omzeild)
    """
    if not ophaaldagen:
        _log.debug("Geen ophaaldagen opgegeven voor %s — datum ongewijzigd", vanaf)
        return vanaf, False

    dagnummers = {AFKORTING_NAAR_DAGNUM[d] for d in ophaaldagen if d in AFKORTING_NAAR_DAGNUM}
    _log.debug(
        "Zoek eerstvolgende ophaaldag vanaf %s (ophaaldagen: %s)",
        vanaf.strftime("%d-%m-%Y"),
        ", ".join(ophaaldagen),
    )

    kandidaat = vanaf
    max_iter = 30
    feestdag_omzeild = False

    for _ in range(max_iter):
        if kandidaat.weekday() in dagnummers:
            if sla_feestdagen_over and is_feestdag(kandidaat):
                _log.debug(
                    "%s is ophaaldag maar feestdag — doorschuiven naar volgende dag",
                    kandidaat.strftime("%d-%m-%Y"),
                )
                feestdag_omzeild = True
                kandidaat += timedelta(days=1)
                continue
            _log.debug(
                "Ophaaldag gevonden: %s%s",
                kandidaat.strftime("%d-%m-%Y"),
                " (feestdag omzeild)" if feestdag_omzeild else "",
            )
            return kandidaat, feestdag_omzeild

        kandidaat += timedelta(days=1)

    _log.warning(
        "Geen ophaaldag gevonden binnen 30 dagen vanaf %s (ophaaldagen: %s) — fallback op startdatum",
        vanaf.strftime("%d-%m-%Y"),
        ", ".join(ophaaldagen),
    )
    return vanaf, False
