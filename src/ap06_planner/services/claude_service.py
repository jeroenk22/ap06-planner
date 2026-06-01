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

import anthropic

MODEL = "claude-sonnet-4-6"
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY niet gevonden. "
                "Voeg toe aan .env bestand."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def analyseer_tijdvenster_met_claude(
    tekst: str,
    wijzigingen: str | None = None,
) -> dict | None:
    """
    Gebruik Claude om een tijdvensterstring te analyseren die de reguliere parser
    niet kon verwerken.

    Returns:
        Dict met: {plaats, begintijd, eindtijd, type} of None bij fout.
    """
    prompt = f"""Analyseer deze planningsregel uit een AP06 monstername-planning.
Extraheer: plaatsnaam, begintijd (HH:MM), eindtijd (HH:MM), type (LAD of LOS).

Tijdvensterstring: "{tekst}"
{"Wijziging: " + wijzigingen if wijzigingen else ""}

Antwoord ALLEEN in dit JSON-formaat (geen uitleg, geen markdown):
{{"plaats": "...", "begintijd": "HH:MM", "eindtijd": "HH:MM", "type": "LAD"}}

Regels:
- "Bladel TonTrans 7-18 LAD17" → plaats=Bladel, begin=07:00, eind=18:00, type=LAD
- "Naar 12-18" in wijziging → vervang tijdvenster door 12:00-18:00
- "Heusden" → "Heusden (gem. Asten)" als plaatsnaam
- Tijden als "8.30" → "08:30"
"""

    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        tekst_resp = message.content[0].text.strip()
        return json.loads(tekst_resp)
    except Exception:
        return None


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
        resultaat = message.content[0].text.strip()
        if resultaat == "GEEN" or resultaat not in bekende_namen:
            return None
        return resultaat
    except Exception:
        return None
