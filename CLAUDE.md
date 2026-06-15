# AP06 Planner

## Wat deze app doet
Verwerkt xlsx-planningsbestanden (AP06 monstername) automatisch naar gestructureerde
rijinstructies per monsternemer. De app leest planningsbestanden van de klant in,
koppelt deze aan de monsternemer-database, berekent ophaaldagen rekening houdend
met nationale feestdagen, en genereert per monsternemer een JSON-object met alle
benodigde informatie voor de chauffeur.

## Stack
- Python 3.13.13
- Streamlit 1.58.0  (UI — upload, beheer, debug output)
- Anthropic SDK 0.105.2  (claude-sonnet-4-6 — intelligente xlsx-analyse)
- openpyxl 3.1.5+  (xlsx inlezen met data_only=True voor formuleresolutie)
- SQLite (ingebouwd in Python)  (monsternemer database)
- OSRM  (gratis reistijdberekening, geen API-key nodig)
- Nager.Date API  (Nederlandse nationale feestdagen)
- Ruff 0.15.14  (linter + formatter)

## Commando's
```bash
# Installeer dependencies (venv aanbevolen)
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# of: .venv\Scripts\activate.bat  # Windows CMD

pip install -e ".[dev]"

# Start de Streamlit app
streamlit run src/ap06_planner/main.py

# Run tests
pytest

# Lint + format
ruff check .
ruff format .
```

## Projectstructuur
```
src/ap06_planner/
  main.py          → Streamlit hoofdapp (multipage)
  pages/
    01_planning.py → Upload xlsx, verwerk, toon JSON
    02_beheer.py   → Monsternemer database beheren (CRUD)
  parsers/
    xlsx_parser.py → xlsx inlezen, tabblad-selectie, header-detectie
    tijdvenster.py → "Bladel TonTrans 7-18 LAD17" → {plaats, start, eind}
    wijzigingen.py → "Naar 12-18", "Anouk na 12", "vervallen" verwerken
  services/
    claude_service.py  → Claude API voor complexe/ambigue cases
    osrm_service.py    → Reistijd berekening (A→B in minuten)
    nager_service.py   → NL nationale feestdagen via Nager.Date API
    db_service.py      → SQLite CRUD voor monsternemers
    mendrix_service.py → Mendrix SOAP Custom Link integratie
docs/
  Mendrix_soap_customlink_docs.md → ALTIJD raadplegen bij elke wijziging aan mendrix_service.py
  examples/                       → XML-voorbeeldbestanden Mendrix Custom Link; raadplegen bij
                                    nieuwe SOAP-calls of bij twijfel over request/response-structuur
  models/
    schemas.py     → Dataklassen (MonsternemeRecord, PlanningRow, etc.)
  utils/
    date_utils.py  → Datum helpers (eerstvolgende ophaaldag, etc.)
data/
  ap06.db          → SQLite database (NIET in repo — bevat persoonsgegevens!)
```

## Kritieke xlsx-parsing regels (geleerd uit voorbeeldbestanden)
1. Laad ALTIJD met `data_only=True` — anders krijg je formules zoals `=AK4`
   ipv de werkelijke waarden
2. Selecteer tabbladen met datumdagnaam-patroon: `\d{1,2}-\d{1,2}\s+(Maandag|...|Zondag)`
   Sla over: Blad2, Blad129, en andere utility-tabs
3. Detecteer de headerrij dynamisch (scan rijen 1-5 op aanwezigheid van 'Monsternemer')
4. Er zijn 2 kolomformaten:
   - Standaard (headers op rij 3): kolom B=Monsternemer, D=wijzigingen, E=Locatie, F=Klant
   - Eurofins Agro (headers op rij 2): kolom A=Monsternemer, D=wijzigingen, E=Klant
5. Datum staat op rij 1 kolom C (of rij 1 kolom B bij Eurofins) als datetime object
6. Tijdvenster formaten: `7-18`, `8.30-10.30`, `11.30-13.30`, `5.30-7.30`
7. Skip rijen waarbij Monsternemer leeg is
8. Skip rijen met "vervallen"/"intrekken"/"ingetrokken" in wijzigingen
9. Negeer "dagblok"/"ochtendblok" in wijzigingen

## Conventies
- Branch strategie: main (protected) → develop → feature/xxx, fix/xxx, chore/xxx
- Commits: Conventional Commits (feat:, fix:, chore:, docs:, test:)
- Geen `Co-Authored-By: Claude ...` regel in commit messages
- PR: nooit direct naar main, altijd via PR met passing tests
- Package manager: pip + venv

## Privacy & beveiliging
- data/ap06.db staat in .gitignore — bevat echte persoonsgegevens
- NOOIT persoonsgegevens committen (namen, adressen, telefoonnummers, postcodes)
- ANTHROPIC_API_KEY alleen via .env (nooit hardcoden)
- .env staat in .gitignore

## Wat Claude NIET mag doen
- Nooit direct committen naar main
- Nooit .env bestanden aanmaken met echte secrets
- Nooit dependencies toevoegen zonder expliciete vraag
- Nooit bestaande tests verwijderen
- Nooit data/ap06.db aanmaken of overschrijven zonder bevestiging
- Nooit de ANTHROPIC_API_KEY logen of printen

---

## Karpathy Gedragsregels

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Stel aannames expliciet. Bij meerdere interpretaties: presenteer ze — kies niet stilletjes.
Stop als iets onduidelijk is. Benoem wat onduidelijk is. Vraag het.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- Geen features voorbij wat gevraagd is
- Geen abstracties voor eenmalig gebruik
- Als 200 regels naar 50 kan: herschrijf

### 3. Surgical Changes
**Touch only what you must.**

Bij het aanpassen van bestaande code:
- Verbeter geen aangrenzende code, comments of formatting
- Verwijder imports/variabelen/functies die JOUW wijzigingen ongebruikt maken
- Match de bestaande stijl

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Multi-stap taken: stel kort een plan op:
```
1. [Stap] → verify: [check]
2. [Stap] → verify: [check]
```

### 5. Tests na elke codewijziging
Bij elke codewijziging altijd controleren:
- Bestaande tests nog groen?
- Moeten bestaande tests aangepast worden?
- Zijn er tests die niet meer relevant zijn?
- Zijn er nieuwe tests nodig?

---

## Security
- Nooit API keys, passwords of secrets in code of commits
- Gebruik altijd .env.example voor configuratie voorbeelden
- data/ map bevat persoonsgegevens — behandel als gevoelig

## Evaluatie & Kwaliteit
- **Code coverage:** minimaal 80% (afgedwongen in CI)
- **Linting:** Ruff — zero errors verplicht in CI
