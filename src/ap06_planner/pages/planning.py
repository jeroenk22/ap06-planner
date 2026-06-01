"""
planning.py — Upload en verwerk xlsx-planningsbestanden.
Stadium 1: Upload → JSON debug output per monsternemer.
"""

import json
from io import BytesIO

import streamlit as st

from ap06_planner.parsers.xlsx_parser import lees_planningsbestand
from ap06_planner.parsers.tijdvenster import parse_tijdvenster, vergelijk_tijdvensters
from ap06_planner.parsers.wijzigingen import verwerk_wijzigingen, pas_wijziging_toe
from ap06_planner.services.db_service import zoek_monsternemer, haal_alle_monsternemers
from ap06_planner.services.nager_service import is_feestdag, eerstvolgende_ophaaldag
from ap06_planner.services.claude_service import match_monsternemer_naam
from ap06_planner.utils.date_utils import is_ophaaldag, format_datum_nl, parse_datum
from ap06_planner.models.schemas import ALGEMENE_INSTRUCTIE_AP06, PlanningOutput


def render():
    st.title("📋 Planning verwerken")
    st.caption("Upload een xlsx-planningsbestand om rijinstructies te genereren.")

    uploaded = st.file_uploader(
        "Kies een xlsx-planningsbestand",
        type=["xlsx"],
        help="Het bestand van de klant met de AP06 monstername-planning.",
    )

    if not uploaded:
        st.info("Upload een xlsx-bestand om te beginnen.")
        return

    with st.spinner("Bestand inlezen..."):
        bestand_bytes = BytesIO(uploaded.read())
        try:
            tabbladen = lees_planningsbestand(bestand_bytes)
        except Exception as e:
            st.error(f"Fout bij inlezen xlsx: {e}")
            return

    if not tabbladen:
        st.warning("Geen geldige plannings-tabbladen gevonden in dit bestand.")
        return

    st.success(f"✅ {len(tabbladen)} tabblad(en) geladen: {[t['tabblad'] for t in tabbladen]}")

    # Laad bekende monsternemers voor naam-matching
    bekende_monsternemers = haal_alle_monsternemers()
    bekende_namen = [m.volledige_naam for m in bekende_monsternemers]

    alle_output: list[dict] = []

    for tab in tabbladen:
        datum_str = tab.get("datum")
        dagnaam = tab.get("dagnaam", "onbekend")
        regels = tab.get("regels", [])

        datum = parse_datum(datum_str) if datum_str else None

        st.subheader(f"📅 {dagnaam.capitalize()} {datum_str or '??'} — {tab['tabblad']}")

        # Groepeer regels per monsternemer
        per_monsternemer: dict[str, list] = {}
        for r in regels:
            if not r.overgeslagen:
                per_monsternemer.setdefault(r.monsternemer_naam, []).append(r)

        st.caption(
            f"{len(regels)} regels, {sum(r.overgeslagen for r in regels)} overgeslagen, "
            f"{len(per_monsternemer)} unieke monsternemers"
        )

        for naam, naam_regels in per_monsternemer.items():
            output = _verwerk_monsternemer(
                naam=naam,
                regels=naam_regels,
                datum=datum,
                dagnaam=dagnaam,
                bekende_namen=bekende_namen,
                bekende_monsternemers=bekende_monsternemers,
            )
            alle_output.append(output)

    # Toon JSON output
    st.divider()
    st.subheader("🔍 Debug JSON output")
    st.caption("Dit is de ruwe output van Stadium 1. Controleer op correctheid.")

    col1, col2 = st.columns([3, 1])
    with col2:
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(alle_output, indent=2, ensure_ascii=False),
            file_name=f"ap06_output_{alle_output[0].get('datum', 'datum') if alle_output else 'output'}.json",
            mime="application/json",
        )

    st.json(alle_output)


def _verwerk_monsternemer(
    naam: str,
    regels: list,
    datum,
    dagnaam: str,
    bekende_namen: list[str],
    bekende_monsternemers: list,
) -> dict:
    """Verwerk alle regels van één monsternemer naar een output-dict."""

    warnings: list[str] = []

    # Zoek monsternemer in database
    monsternemer = zoek_monsternemer(naam)
    if not monsternemer and bekende_namen:
        # Probeer Claude voor naam-matching
        gematchte_naam = match_monsternemer_naam(naam, bekende_namen)
        if gematchte_naam:
            monsternemer = zoek_monsternemer(gematchte_naam)
            if monsternemer:
                warnings.append(f"Naam gematcht via Claude: '{naam}' → '{gematchte_naam}'")

    niet_in_db = monsternemer is None
    if niet_in_db:
        warnings.append(f"Monsternemer '{naam}' NIET gevonden in database!")

    # Verzamel alle tijdvensters (met wijzigingen verwerkt)
    tijdvensters = []
    for r in regels:
        # Locatie: prefer 'locatie_raw', fallback 'klant_raw'
        locatie_tekst = r.locatie_raw or r.klant_raw or ""
        tv = parse_tijdvenster(locatie_tekst)
        if not tv:
            continue

        # Verwerk wijzigingen
        if r.wijzigingen:
            wijziging = verwerk_wijzigingen(r.wijzigingen)
            if not wijziging.negeer:
                tv = pas_wijziging_toe(tv, wijziging)

        tijdvensters.append(tv)

    # Laatste tijdvenster bepalen
    laatste_tv = vergelijk_tijdvensters(tijdvensters) if tijdvensters else None

    # Ophaaldag-logica
    ophaaldagen = monsternemer.ophaaldagen if monsternemer else []
    huidige_dag_is_ophaaldag = is_ophaaldag(datum, ophaaldagen) if datum and ophaaldagen else False

    # Inplanning
    inplannen_op_str = ""
    inplannen_toelichting = None
    gewensttijd_begin = "10:00"
    gewensttijd_eind = "23:59"

    if datum and ophaaldagen:
        if huidige_dag_is_ophaaldag:
            if is_feestdag(datum):
                # Feestdag! Zoek eerstvolgende ophaaldag
                volgende, _ = eerstvolgende_ophaaldag(datum, ophaaldagen)
                inplannen_op_str = format_datum_nl(volgende)
                inplannen_toelichting = f"Feestdag op {datum.strftime('%d-%m-%Y')} → verschoven"
                gewensttijd_begin = "10:00"
            else:
                inplannen_op_str = format_datum_nl(datum)
                if laatste_tv:
                    gewensttijd_begin = laatste_tv.eindtijd
                    # Reistijdberekening volgt in latere iteratie
        else:
            # Niet zijn ophaaldag → eerstvolgende ophaaldag
            volgende, _ = eerstvolgende_ophaaldag(datum, ophaaldagen)
            inplannen_op_str = format_datum_nl(volgende)
            inplannen_toelichting = "Monsters van vandaag (geen ophaaldag)"
            gewensttijd_begin = "10:00"

    return {
        "dagnaam": dagnaam,
        "datum": datum.strftime("%d-%m-%Y") if datum else None,
        "naam_monsternemer": naam,
        "adres": monsternemer.adres if monsternemer else None,
        "postcode": monsternemer.postcode if monsternemer else None,
        "woonplaats": monsternemer.woonplaats if monsternemer else None,
        "telefoon": monsternemer.telefoon if monsternemer else None,
        "laatste_tijdvenster_plaats": laatste_tv.plaats if laatste_tv else None,
        "laatste_tijdvenster": (
            f"{laatste_tv.begintijd} - {laatste_tv.eindtijd}" if laatste_tv else None
        ),
        "standaard_ophaaldagen": ophaaldagen,
        "huidige_dag_is_ophaaldag": huidige_dag_is_ophaaldag,
        "inplannen_op": inplannen_op_str,
        "inplannen_toelichting": inplannen_toelichting,
        "laadinstructie": monsternemer.laadinstructie if monsternemer else None,
        "bijzonderheden_laden": monsternemer.bijzonderheden if monsternemer else None,
        "algemene_instructie_ap06": ALGEMENE_INSTRUCTIE_AP06,
        "gewensttijd": f"{gewensttijd_begin} - {gewensttijd_eind}",
        "niet_in_database": niet_in_db,
        "warnings": warnings,
    }
