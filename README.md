# AP06 Planner

Verwerkt xlsx-planningsbestanden (AP06 monstername) naar rijinstructies per monsternemer.

## Snel starten

```bash
# 1. Kloon de repo
git clone https://github.com/jeroenk22/ap06-planner.git
cd ap06-planner
git checkout develop

# 2. Maak een virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# of: .venv\Scripts\activate.bat  # Windows CMD

# 3. Installeer dependencies
pip install -e ".[dev]"

# 4. Kopieer .env.example en vul je API key in
cp .env.example .env
# Bewerk .env en vul ANTHROPIC_API_KEY in

# 5. Start de app
streamlit run src/ap06_planner/main.py
```

De app opent automatisch op http://localhost:8501

## Draaien op de interne server

```powershell
# Vanaf de projectroot op de server
.\scripts\start_server.ps1
```

De app is dan bereikbaar op `http://<server-ip>:8501` vanaf het interne netwerk.

Aandachtspunten:

- **Working directory.** Alle paden (`data/ap06.db`, `logs/`) zijn relatief aan de
  working directory. `start_server.ps1` zet die zelf op de projectroot — start de app
  niet met een los `streamlit run` vanuit een andere map, anders wordt er stilletjes
  een lege database aangemaakt.
- **Databasepad.** Zet `DB_PATH` in `.env` als de database buiten de projectmap moet
  staan (bijvoorbeeld op een gedeelde schijf met een backup).
- **OSRM.** Zet `OSRM_BASE_URL` op de lokale instance (`http://192.168.4.105:5000`) of
  laat de regel weg — dat is de default in de code.
- **Als service.** Registreer `start_server.ps1` via NSSM of de Taakplanner zodat de
  app een herstart van de server overleeft.
- **Rechten.** `.env` en `data/ap06.db` bevatten secrets en persoonsgegevens; beperk de
  NTFS-rechten op die bestanden tot het serviceaccount.

## Stadia

| Stadium | Status | Beschrijving |
|---------|--------|--------------|
| 1 | ✅ Afgerond | xlsx upload → JSON debug output per monsternemer |
| 2 | ✅ Afgerond | Mendrix SOAP check: bestaande orders ophalen en tijden vergelijken |
| 3 | ✅ Afgerond | Automatisch orders aanmaken in Mendrix voor niet-geplande monsternemers |
| 4 | 🧪 In test | WhatsApp-samenvatting via TextMeBot na verwerking |

## Privacy
De monsternemer-database (`data/ap06.db`) bevat persoonsgegevens en staat
**niet** in de repository. Importeer de monsternemer-gegevens handmatig via
het beheerTabblad in de app.
