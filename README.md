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

Eenmalige installatie — draai op de server in PowerShell **als administrator**:

```powershell
.\scripts\install_on_server.ps1
```

Dit script haalt de code op, maakt de virtual environment, zet de firewallpoort open en
registreert de app als geplande taak onder het SYSTEM-account. De app start daarmee
automatisch na een herstart van de server en herstart zelf bij een crash. Het script is
idempotent: opnieuw draaien rolt een update uit in plaats van te dupliceren.

Twee bestanden moet je daarna zelf plaatsen — ze staan bewust niet in de repo:

- `.env` — kopieer `.env.example` en vul de sleutels in
- `data/ap06.db` — de monsternemer-database met persoonsgegevens

Beheer van de draaiende app:

```powershell
Get-ScheduledTaskInfo -TaskName "AP06 Planner"   # status
Stop-ScheduledTask    -TaskName "AP06 Planner"   # stoppen
Start-ScheduledTask   -TaskName "AP06 Planner"   # starten
```

Handmatig starten zonder taak kan met `.\scripts\start_server.ps1`. De app is bereikbaar
op `http://<server-ip>:8501` vanaf het interne netwerk.

Aandachtspunten:

- **Working directory.** Alle paden (`data/ap06.db`, `logs/`) zijn relatief aan de
  working directory. `start_server.ps1` zet die zelf op de projectroot — start de app
  niet met een los `streamlit run` vanuit een andere map, anders wordt er stilletjes
  een lege database aangemaakt.
- **Databasepad.** Zet `DB_PATH` in `.env` als de database buiten de projectmap moet
  staan (bijvoorbeeld op een gedeelde schijf met een backup).
- **OSRM.** Er draait op dit moment geen eigen OSRM-instance; `OSRM_BASE_URL` hoort op
  `http://router.project-osrm.org` te staan. Laat de regel niet weg — de default in de
  code wijst naar een server die er niet is, wat elke routeberekening vertraagt.
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
