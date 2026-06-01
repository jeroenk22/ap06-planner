# Python Best Practices — AP06 Planner

## Richtlijnen

### openpyxl xlsx inlezen
```python
# ALTIJD data_only=True gebruiken om formule-resultaten te krijgen!
wb = load_workbook(pad, data_only=True)
```

### SQLite
```python
# Gebruik context manager voor automatisch commit/rollback
with sqlite3.connect(db_path) as conn:
    conn.execute(...)
    conn.commit()
```

### Null-veilig werken
```python
# Gebruik walrus operator voor gecombineerde check + toewijzing
if (tv := parse_tijdvenster(tekst)) is not None:
    verwerk(tv)
```

### Streamlit session state
```python
# Gebruik session_state voor persistente data tussen reruns
if "monsternemers" not in st.session_state:
    st.session_state.monsternemers = haal_alle_monsternemers()
```

## Gevonden tijdvenster-formaten
| Formaat | Voorbeeld | Geparsed |
|---------|-----------|---------|
| Heel uur | `7-18` | `07:00 - 18:00` |
| Half uur (punt) | `8.30-10.30` | `08:30 - 10:30` |
| Vroeg | `5.30-7.30` | `05:30 - 07:30` |
