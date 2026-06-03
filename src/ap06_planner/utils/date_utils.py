"""date_utils.py — Datum helpers voor ophaalplanning."""

from datetime import date, datetime

DAGAFKORTINGEN = {
    "ma": 0, "di": 1, "wo": 2, "do": 3,
    "vr": 4, "za": 5, "zo": 6,
}

DAGNAMEN_NL = {
    0: "maandag", 1: "dinsdag", 2: "woensdag", 3: "donderdag",
    4: "vrijdag", 5: "zaterdag", 6: "zondag",
}


def is_ophaaldag(dag: date, ophaaldagen: list[str]) -> bool:
    """Controleer of een dag een ophaaldag is voor de monsternemer."""
    dagnummer = dag.weekday()
    return dagnummer in {DAGAFKORTINGEN.get(d, -1) for d in ophaaldagen}


def format_datum_nl(dag: date) -> str:
    """Formatteer een datum als 'maandag 16-06-2026'."""
    dagnaam = DAGNAMEN_NL[dag.weekday()]
    return f"{dagnaam} {dag.strftime('%d-%m-%Y')}"


def voeg_minuten_toe(tijdstr: str, minuten: int) -> str:
    """Voeg minuten toe aan een tijdstring 'HH:MM'. Retourneert 'HH:MM'."""
    try:
        uren, mins = map(int, tijdstr.split(":"))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Ongeldige tijdstring: {tijdstr!r}") from e
    totaal = uren * 60 + mins + minuten
    return f"{(totaal // 60) % 24:02d}:{totaal % 60:02d}"


def parse_datum(datum_str: str) -> date | None:
    """Parse een datum-string in diverse formaten."""
    formaten = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]
    for fmt in formaten:
        try:
            return datetime.strptime(datum_str, fmt).date()
        except ValueError:
            continue
    return None
