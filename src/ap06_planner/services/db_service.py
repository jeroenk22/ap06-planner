"""
db_service.py — SQLite database voor monsternemers.

De database bevat persoonsgegevens en staat NIET in de repository.
Locatie: data/ap06.db (configureerbaar via DB_PATH in .env)
"""

import sqlite3
from pathlib import Path

from ap06_planner.models.schemas import Monsternemer

DB_DEFAULT = Path("data/ap06.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS monsternemers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL DEFAULT 'AP06',
    voornaam        TEXT NOT NULL,
    tussenvoegsel   TEXT,
    achternaam      TEXT NOT NULL,
    adres           TEXT,
    postcode        TEXT,
    woonplaats      TEXT,
    land            TEXT,
    telefoon        TEXT,
    laadinstructie  TEXT,
    ophaaldagen     TEXT,          -- komma-gescheiden: "ma,wo,vr"
    uiterlijke_tijd     TEXT,          -- "21:30" — wens monsternemer
    uiterlijke_plantijd TEXT,          -- "21:30" — planningtechnische grens (overschreden → doorschuiven)
    bijzonderheden      TEXT,
    aantal_lege_bakken  INTEGER NOT NULL DEFAULT 2,
    sjabloon            INTEGER NOT NULL DEFAULT 0,
    ophalen             INTEGER NOT NULL DEFAULT 1  -- 0 = brengt zelf
)
"""


def _get_conn(db_path: Path = DB_DEFAULT) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialiseer_db(db_path: Path = DB_DEFAULT) -> None:
    """Maak de database aan als die nog niet bestaat."""
    with _get_conn(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)
        # Migratie: voeg kolommen toe als ze nog niet bestaan
        bestaande = {r[1] for r in conn.execute("PRAGMA table_info(monsternemers)")}
        if "aantal_lege_bakken" not in bestaande:
            conn.execute(
                "ALTER TABLE monsternemers ADD COLUMN aantal_lege_bakken INTEGER NOT NULL DEFAULT 2"
            )
        if "sjabloon" not in bestaande:
            conn.execute("ALTER TABLE monsternemers ADD COLUMN sjabloon INTEGER NOT NULL DEFAULT 0")
        if "uiterlijke_plantijd" not in bestaande:
            conn.execute("ALTER TABLE monsternemers ADD COLUMN uiterlijke_plantijd TEXT")
        if "land" not in bestaande:
            conn.execute("ALTER TABLE monsternemers ADD COLUMN land TEXT")
        if "ophalen" not in bestaande:
            conn.execute("ALTER TABLE monsternemers ADD COLUMN ophalen INTEGER NOT NULL DEFAULT 1")
        conn.commit()


def haal_alle_monsternemers(db_path: Path = DB_DEFAULT) -> list[Monsternemer]:
    """Haal alle monsternemers op uit de database."""
    initialiseer_db(db_path)
    try:
        with _get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM monsternemers ORDER BY achternaam, voornaam"
            ).fetchall()
        return [_row_naar_monsternemer(r) for r in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Database fout bij ophalen monsternemers: {e}") from e


def zoek_monsternemer(
    naam: str,
    db_path: Path = DB_DEFAULT,
) -> Monsternemer | None:
    """
    Zoek een monsternemer op naam (voornaam + achternaam).
    Fuzzy matching: vergelijkt lowercase en negeert tussenvoegsel-variaties.
    """
    initialiseer_db(db_path)
    naam_lower = naam.lower().strip()
    kandidaten = haal_alle_monsternemers(db_path)
    for m in kandidaten:
        if m.volledige_naam.lower() == naam_lower:
            return m
    # Probeer zonder tussenvoegsel
    for m in kandidaten:
        zonder_tv = f"{m.voornaam} {m.achternaam}".lower()
        if zonder_tv == naam_lower:
            return m
    # Fuzzy: voornaam + achternaam als subsets
    namen = naam_lower.split()
    for m in kandidaten:
        m_namen = m.volledige_naam.lower().split()
        if namen and namen[0] == m_namen[0] and namen[-1] == m_namen[-1]:
            return m
    return None


def voeg_monsternemer_toe(m: Monsternemer, db_path: Path = DB_DEFAULT) -> int:
    """Voeg een monsternemer toe. Retourneert het nieuwe ID."""
    initialiseer_db(db_path)
    try:
        with _get_conn(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO monsternemers
                (code, voornaam, tussenvoegsel, achternaam, adres, postcode,
                 woonplaats, land, telefoon, laadinstructie, ophaaldagen, uiterlijke_tijd,
                 uiterlijke_plantijd, bijzonderheden, aantal_lege_bakken, sjabloon, ophalen)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    m.code,
                    m.voornaam,
                    m.tussenvoegsel,
                    m.achternaam,
                    m.adres,
                    m.postcode,
                    m.woonplaats,
                    m.land,
                    m.telefoon,
                    m.laadinstructie,
                    ",".join(m.ophaaldagen),
                    m.uiterlijke_tijd,
                    m.uiterlijke_plantijd,
                    m.bijzonderheden,
                    m.aantal_lege_bakken,
                    int(m.sjabloon),
                    int(m.ophalen),
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        raise RuntimeError(f"Database fout bij opslaan monsternemer: {e}") from e


def update_monsternemer(m: Monsternemer, db_path: Path = DB_DEFAULT) -> bool:
    """Werk een bestaande monsternemer bij op ID. Retourneert True als succesvol."""
    initialiseer_db(db_path)
    try:
        with _get_conn(db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE monsternemers SET
                    code=?, voornaam=?, tussenvoegsel=?, achternaam=?, adres=?, postcode=?,
                    woonplaats=?, land=?, telefoon=?, laadinstructie=?, ophaaldagen=?, uiterlijke_tijd=?,
                    uiterlijke_plantijd=?, bijzonderheden=?, aantal_lege_bakken=?, sjabloon=?, ophalen=?
                WHERE id=?
                """,
                (
                    m.code,
                    m.voornaam,
                    m.tussenvoegsel,
                    m.achternaam,
                    m.adres,
                    m.postcode,
                    m.woonplaats,
                    m.land,
                    m.telefoon,
                    m.laadinstructie,
                    ",".join(m.ophaaldagen),
                    m.uiterlijke_tijd,
                    m.uiterlijke_plantijd,
                    m.bijzonderheden,
                    m.aantal_lege_bakken,
                    int(m.sjabloon),
                    int(m.ophalen),
                    m.id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise RuntimeError(f"Database fout bij bijwerken monsternemer: {e}") from e


def verwijder_monsternemer(monsternemer_id: int, db_path: Path = DB_DEFAULT) -> bool:
    """Verwijder een monsternemer op ID. Retourneert True als succesvol."""
    initialiseer_db(db_path)
    try:
        with _get_conn(db_path) as conn:
            cursor = conn.execute("DELETE FROM monsternemers WHERE id = ?", (monsternemer_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise RuntimeError(f"Database fout bij verwijderen monsternemer: {e}") from e


def _safe_row(row: sqlite3.Row, kolom: str):
    try:
        return row[kolom]
    except IndexError:
        return None


def _row_naar_monsternemer(row: sqlite3.Row) -> Monsternemer:
    ophaaldagen_str = row["ophaaldagen"] or ""
    ophaaldagen = [d.strip() for d in ophaaldagen_str.split(",") if d.strip()]
    return Monsternemer(
        id=row["id"],
        code=row["code"],
        voornaam=row["voornaam"],
        tussenvoegsel=row["tussenvoegsel"],
        achternaam=row["achternaam"],
        adres=row["adres"] or "",
        postcode=row["postcode"] or "",
        woonplaats=row["woonplaats"] or "",
        land=_safe_row(row, "land"),
        telefoon=row["telefoon"],
        laadinstructie=row["laadinstructie"],
        ophaaldagen=ophaaldagen,
        uiterlijke_tijd=row["uiterlijke_tijd"],
        uiterlijke_plantijd=_safe_row(row, "uiterlijke_plantijd"),
        bijzonderheden=row["bijzonderheden"],
        aantal_lege_bakken=row["aantal_lege_bakken"] or 2,
        sjabloon=bool(row["sjabloon"]),
        ophalen=bool(row["ophalen"]),
    )
