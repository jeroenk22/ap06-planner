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

## Stadia

| Stadium | Status | Beschrijving |
|---------|--------|--------------|
| 1 | 🚧 In ontwikkeling | xlsx upload → JSON debug output |
| 2 | ⏳ Later | MendriX SOAP check op bestaande orders |
| 3 | ⏳ Later | Automatisch orders aanmaken in MendriX |
| 4 | ⏳ Later | Volledig automatisch (WhatsApp/mail intake) |

## Privacy
De monsternemer-database (`data/ap06.db`) bevat persoonsgegevens en staat
**niet** in de repository. Importeer de monsternemer-gegevens handmatig via
het beheerTabblad in de app.
