"""
nager_service.py — Controleert Nederlandse nationale feestdagen via Nager.Date API.
API docs: https://date.nager.at/nl/api
"""

from datetime import date, timedelta

import requests

NAGER_BASE_URL = "https://date.nager.at/api/v3"
COUNTRY_CODE = "NL"

_feestdagen_cache: dict[int, set[date]] = {}


def haal_feestdagen(jaar: int) -> set[date]:
    """Haal alle NL nationale feestdagen op voor een jaar. Resultaat wordt gecached."""
    if jaar in _feestdagen_cache:
        return _feestdagen_cache[jaar]

    url = f"{NAGER_BASE_URL}/PublicHolidays/{jaar}/{COUNTRY_CODE}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        feestdagen = {date.fromisoformat(item["date"]) for item in data}
        _feestdagen_cache[jaar] = feestdagen
        return feestdagen
    except Exception:
        # Bij API-fout: geen feestdagen aannemen (veilige fallback)
        return set()


def is_feestdag(dag: date) -> bool:
    """Controleer of een dag een NL nationale feestdag is."""
    feestdagen = haal_feestdagen(dag.year)
    return dag in feestdagen


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
        return vanaf, False

    dagnummers = {AFKORTING_NAAR_DAGNUM[d] for d in ophaaldagen if d in AFKORTING_NAAR_DAGNUM}

    kandidaat = vanaf
    max_iter = 30  # bescherming tegen oneindige lus
    feestdag_omzeild = False

    for _ in range(max_iter):
        if kandidaat.weekday() in dagnummers:
            if sla_feestdagen_over and is_feestdag(kandidaat):
                feestdag_omzeild = True
                kandidaat += timedelta(days=1)
                continue
            return kandidaat, feestdag_omzeild

        kandidaat += timedelta(days=1)

    return vanaf, False  # Fallback
