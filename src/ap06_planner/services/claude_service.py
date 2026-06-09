"""
claude_service.py — Claude API integratie voor intelligente xlsx-analyse.

Gebruikt claude-sonnet-4-6 voor het verwerken van ambigue of inconsistente
data uit de planningsbestanden. Claude lost op:
- Onbekende tijdvenster-formaten
- Ambigue plaatsnamen ("Heusden" → "Heusden (gem. Asten)")
- Complexe wijzigingen-combinaties
- Naam-matching van monsternemers

LETOP: API-calls worden alleen gedaan als de reguliere parsers falen.
"""

import json
import os
import re

import anthropic

_MARKDOWN_CODE_BLOCK = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
_STRIP_LAD_LOS_NR = re.compile(r"\b(LAD|LOS)\d+\b", re.IGNORECASE)


def _parse_json(tekst: str):
    """Parse JSON uit Claude-output, ook bij markdown wrapping of extra tekst."""
    tekst = tekst.strip()
    if not tekst:
        raise json.JSONDecodeError("Lege Claude-respons", "", 0)
    # Haal JSON uit code block als aanwezig
    m = _MARKDOWN_CODE_BLOCK.search(tekst)
    if m:
        tekst = m.group(1).strip()
    # Zoek het eerste [ of { als er nog preamble-tekst voor staat
    if tekst and tekst[0] not in ("[", "{", '"'):
        for i, c in enumerate(tekst):
            if c in ("[", "{"):
                tekst = tekst[i:]
                break
    return json.loads(tekst)


MODEL = "claude-sonnet-4-6"
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY niet gevonden. Voeg toe aan .env bestand.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


_PLANNINGSREGEL_SYSTEM = """Je analyseert planningsregels uit een AP06 monstername-planning.
Elke regel heeft een locatiestring en een optionele wijziging. Je retourneert het definitieve tijdvenster na toepassing van de wijziging.

Je krijgt een JSON-array van objecten met "locatie" en "wijziging" (kan null zijn).
Retourneer een JSON-array in exact dezelfde volgorde.

Schema per item:
{"plaats": "...", "begintijd": "HH:MM", "eindtijd": "HH:MM", "type": "LAD" | "LOS", "nummer": "..." | null, "overgeslagen": false}

Stap 1 — extraheer uit de locatiestring:
- "plaats" is ALTIJD de Nederlandse gemeente — nooit de bedrijfsnaam
- Het tijdvenster staat ALTIJD als twee getallen gescheiden door een streepje in de locatiestring
- Extraheer begintijd en eindtijd altijd rechtstreeks uit de locatiestring
- "Bladel TonTrans 7-18 LAD17"    → plaats=Bladel, begintijd=07:00, eindtijd=18:00, type=LAD, nummer="17"
- "Bemmel JB 15-17 LAD"           → plaats=Bemmel, begintijd=15:00, eindtijd=17:00, type=LAD, nummer=null
- "Kerkwijk Spek 7.15-9.15 LAD"  → plaats=Kerkwijk, begintijd=07:15, eindtijd=09:15, type=LAD, nummer=null
- "Zundert Dams 6-18 LAD1"        → plaats=Zundert, begintijd=06:00, eindtijd=18:00, type=LAD, nummer="1"
- "Dams Zunder 6-18 LAD15"        → plaats=Zundert (Zunder=afkorting, Dams=bedrijf)
- "Axel Alphen 16-18 LAD1"        → plaats=Axel
- "Hazerswoude-Rijndijk hertog 7-9 LOS" → plaats=Hazerswoude-Rijndijk, type=LOS
- Schrijf afgekorte plaatsnamen volledig: "Zunder"→"Zundert", "Heeswijk"→"Heeswijk-Dinther"
- Tijdnotatie: "6"→"06:00", "7"→"07:00", "8.30"→"08:30", "7.15"→"07:15", "15.30"→"15:30"
- type: "LAD" als LAD aanwezig, "LOS" als LOS aanwezig, anders "LAD"
- nummer: getal direct na LAD/LOS als string, of null

Stap 2 — pas wijziging toe op het tijdvenster uit stap 1:
- "Naar 12-18" → vervang begintijd+eindtijd door "12:00" en "18:00"
- "[naam] na 12" / "[naam] vanaf 12" → begintijd wordt "12:00" (eindtijd ongewijzigd)
- "[naam] tot 12" → eindtijd wordt "12:00" (begintijd ongewijzigd)
- "[naam] hele dag" → geen aanpassing aan tijden
- "dagblok" / "ochtendblok" → overgeslagen: true
- null of lege wijziging → geen aanpassing

Antwoord ALLEEN met een JSON-array. Geen uitleg, geen markdown."""


def verwerk_planningsregels_batch(
    regels: list[dict],
) -> tuple[list[dict] | None, str | None]:
    """
    Verwerk een lijst van {locatie, wijziging} paren via Claude.
    Dedupliceert op genormaliseerde locatie (LAD/LOS-nummers gestript) voor
    betrouwbaarheid bij batches met veel gelijksoortige entries (bijv. LAD1..LAD44).
    Retourneert resultaten in dezelfde volgorde als de invoer.
    """
    if not regels:
        return [], None

    # Dedupliceer: strip trailing LAD/LOS-nummers als batch-sleutel
    def _norm(loc: str) -> str:
        return _STRIP_LAD_LOS_NR.sub(lambda m: m.group(1).upper(), loc).strip()

    sleutel_naar_idx: dict[tuple, int] = {}
    uniq_regels: list[dict] = []
    for r in regels:
        sleutel = (_norm(r.get("locatie", "")), r.get("wijziging"))
        if sleutel not in sleutel_naar_idx:
            sleutel_naar_idx[sleutel] = len(uniq_regels)
            uniq_regels.append({"locatie": r.get("locatie", ""), "wijziging": r.get("wijziging")})

    # Verwerk unieke items in chunks van 10
    chunk_size = 10
    alle_uniq: list[dict] = []
    tekst_blok = None
    totaal_input = 0
    totaal_cache_create = 0
    totaal_cache_read = 0
    try:
        client = _get_client()
        for i in range(0, len(uniq_regels), chunk_size):
            chunk = uniq_regels[i : i + chunk_size]
            message = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": _PLANNINGSREGEL_SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": json.dumps(chunk, ensure_ascii=False)}],
            )
            u = message.usage
            totaal_input += u.input_tokens
            totaal_cache_create += getattr(u, "cache_creation_input_tokens", 0) or 0
            totaal_cache_read += getattr(u, "cache_read_input_tokens", 0) or 0
            tekst_blok = next(b for b in message.content if b.type == "text")
            chunk_resultaten = _parse_json(tekst_blok.text)
            if len(chunk_resultaten) != len(chunk):
                return None, (
                    f"Claude retourneerde {len(chunk_resultaten)} resultaten "
                    f"voor {len(chunk)} invoer-regels (chunk {i // chunk_size + 1})"
                )
            alle_uniq.extend(chunk_resultaten)

        import sys

        print(
            f"[Claude batch] {len(uniq_regels)} unieke items ({len(regels)} totaal) | "
            f"input={totaal_input} cache_create={totaal_cache_create} cache_read={totaal_cache_read} tokens "
            f"| limit=30K/min",
            file=sys.stderr,
        )

        # Map terug naar originele volgorde
        resultaten = []
        for r in regels:
            sleutel = (_norm(r.get("locatie", "")), r.get("wijziging"))
            idx = sleutel_naar_idx[sleutel]
            resultaten.append(alle_uniq[idx])
        return resultaten, None

    except json.JSONDecodeError as e:
        preview = repr(tekst_blok.text[:300]) if tekst_blok else "geen tekst-blok"
        return None, f"Claude JSON-fout: {e} — respons: {preview}"
    except Exception as e:
        return None, f"Claude API-fout: {e}"


def analyseer_tijdvenster_met_claude(tekst: str) -> dict | None:
    """Analyseer één locatiestring. Voor meerdere: gebruik verwerk_planningsregels_batch."""
    resultaten, _ = verwerk_planningsregels_batch([{"locatie": tekst, "wijziging": None}])
    if not resultaten:
        return None
    return resultaten[0]


_WIJZIGINGEN_SYSTEM = """Je verwerkt cellen uit de 'wijzigingen' kolom van een AP06 monstername-planning.
Je krijgt een JSON-array van teksten. Retourneer een JSON-array in exact dezelfde volgorde.

Schema per item:
{"tijdvervang": ["HH:MM","HH:MM"] | null, "start_na": "HH:MM" | null, "eind_voor": "HH:MM" | null, "hele_dag": false, "negeer": false}

Regels:
- "Naar 12-18", "naar 6-8", "Naar 14-16" → tijdvervang bijv. ["14:00","16:00"]
- "[naam] na 12", "[naam] vanaf 12", "[naam] va 12" → start_na: "12:00"
- "[naam] tot 12" → eind_voor: "12:00"
- "[naam] hele dag" → hele_dag: true
- "dagblok", "ochtendblok" → negeer: true
- Alleen een naam of onduidelijk → alles null/false
- Tijden: "6"→"06:00", "8.30"→"08:30", "14"→"14:00", "12"→"12:00"

Antwoord ALLEEN met een JSON-array. Geen uitleg, geen markdown."""


def interpreteer_wijzigingen_batch(wijzigingen: list[str | None]) -> dict[str, dict] | None:
    """
    Verwerk een lijst wijzigingen in één API-call met prompt caching.
    Returns dict mapping tekst → resultaat, of None bij API-fout.
    """
    uniek = list(dict.fromkeys(w for w in wijzigingen if w))
    if not uniek:
        return {}
    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": _WIJZIGINGEN_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": json.dumps(uniek, ensure_ascii=False)}],
        )
        tekst_blok = next(b for b in message.content if b.type == "text")
        resultaten = _parse_json(tekst_blok.text)
        return dict(zip(uniek, resultaten, strict=False))
    except Exception:
        return None


def interpreteer_wijzigingen(wijzigingen: str) -> dict | None:
    """Verwerk één wijziging via Claude. Voor meerdere: gebruik interpreteer_wijzigingen_batch."""
    resultaat = interpreteer_wijzigingen_batch([wijzigingen])
    if resultaat is None:
        return None
    return resultaat.get(wijzigingen)


def match_monsternemer_naam(
    naam_in_xlsx: str,
    bekende_namen: list[str],
) -> str | None:
    """
    Gebruik Claude om een naam uit het xlsx te matchen met bekende monsternemers.
    Handig bij spellingsvariaties: "Jolanda vd Vorst" → "Jolanda van der Vorst"

    Returns:
        De gematchte naam uit bekende_namen, of None als geen match.
    """
    if not bekende_namen:
        return None

    prompt = f"""Match de naam "{naam_in_xlsx}" met de meest waarschijnlijke naam
uit deze lijst. Antwoord ALLEEN met de exacte naam uit de lijst, of "GEEN" als er
geen redelijke match is.

Lijst:
{chr(10).join(f"- {n}" for n in bekende_namen)}

Regels:
- "vd" = "van der", "v/d" = "van der"
- Spellingsvariaties tellen als match (Gabrielle/Gabriëlle)
- Kijk naar achternaam als primaire match-sleutel
"""

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        tekst_blok = next(b for b in message.content if b.type == "text")
        resultaat = tekst_blok.text.strip()
        if resultaat == "GEEN" or resultaat not in bekende_namen:
            return None
        return resultaat
    except Exception:
        return None


def match_naam_mendrix(
    zoek_naam: str,
    kandidaten: list[str],
) -> str | None:
    """
    Gebruik Claude om zoek_naam te matchen met een naam uit de Mendrix-kandidatenlijst.
    Kandidaten kunnen een prefix bevatten zoals 'AP06/ONAFH -' of 'AP06 -'.

    Returns:
        De best matchende naam uit kandidaten (exact zoals hij staat), of None.
    """
    if not kandidaten:
        return None

    prompt = f"""Je krijgt een naam en een lijst met namen uit een ritplanningssysteem (Mendrix).
Zoek welke naam uit de lijst het beste overeenkomt met de gegeven naam.
Namen in de lijst kunnen een prefix hebben zoals "AP06/ONAFH -" of "AP06 -" — die mag je negeren bij het matchen.

Naam om te matchen: "{zoek_naam}"

Kandidatenlijst:
{chr(10).join(f"- {n}" for n in kandidaten)}

Antwoord ALLEEN met de exacte naam uit de lijst, of "GEEN" als er geen redelijke match is.
"""

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        tekst_blok = next(b for b in message.content if b.type == "text")
        resultaat = tekst_blok.text.strip()
        if resultaat == "GEEN":
            return None
        # Exacte match
        if resultaat in kandidaten:
            return resultaat
        # Tolerante match: antwoord is substring van een kandidaat of vice versa
        for k in kandidaten:
            if resultaat in k or k in resultaat:
                return k
        return None
    except Exception:
        return None
