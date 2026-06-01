"""
beheer.py — Beheer de monsternemer-database via Streamlit UI.

Functies:
- Overzicht van alle monsternemers
- Monsternemer toevoegen
- Monsternemer verwijderen
- Importeren vanuit xlsx (AP06 mockdata formaat)
"""

from io import BytesIO

import streamlit as st
import pandas as pd
from openpyxl import load_workbook

from ap06_planner.services.db_service import (
    haal_alle_monsternemers,
    voeg_monsternemer_toe,
    verwijder_monsternemer,
    initialiseer_db,
)
from ap06_planner.models.schemas import Monsternemer


def render():
    st.title("👥 Monsternemer beheer")
    st.caption(
        "⚠️ Deze data bevat persoonsgegevens. De database is lokaal en staat niet in de repo."
    )

    initialiseer_db()

    tab_overzicht, tab_toevoegen, tab_import = st.tabs(
        ["📋 Overzicht", "➕ Toevoegen", "📥 Importeren vanuit xlsx"]
    )

    with tab_overzicht:
        _render_overzicht()

    with tab_toevoegen:
        _render_toevoegen()

    with tab_import:
        _render_import()


def _render_overzicht():
    monsternemers = haal_alle_monsternemers()

    if not monsternemers:
        st.info("Geen monsternemers in de database. Importeer ze via het 'Importeren' tabblad.")
        return

    st.caption(f"{len(monsternemers)} monsternemers in database")

    # Maak een tabel
    data = []
    for m in monsternemers:
        data.append({
            "ID": m.id,
            "Naam": m.volledige_naam,
            "Woonplaats": m.woonplaats,
            "Postcode": m.postcode,
            "Ophaaldagen": ", ".join(m.ophaaldagen),
            "Uiterlijke tijd": m.uiterlijke_tijd or "—",
            "Ophalen": "✅" if m.ophalen else "❌ (brengt zelf)",
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🗑️ Monsternemer verwijderen")
    verwijder_id = st.number_input("ID van te verwijderen monsternemer", min_value=1, step=1)
    if st.button("Verwijder", type="secondary"):
        if verwijder_monsternemer(int(verwijder_id)):
            st.success(f"Monsternemer #{verwijder_id} verwijderd.")
            st.rerun()
        else:
            st.error(f"Geen monsternemer gevonden met ID {verwijder_id}.")


def _render_toevoegen():
    st.subheader("Nieuwe monsternemer toevoegen")

    with st.form("toevoegen_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            voornaam = st.text_input("Voornaam *")
        with col2:
            tussenvoegsel = st.text_input("Tussenvoegsel")
        with col3:
            achternaam = st.text_input("Achternaam *")

        col4, col5 = st.columns(2)
        with col4:
            adres = st.text_input("Adres (straat + huisnummer)")
            postcode = st.text_input("Postcode")
        with col5:
            woonplaats = st.text_input("Woonplaats")
            telefoon = st.text_input("Telefoonnummer")

        ophaaldagen_opties = ["ma", "di", "wo", "do", "vr", "za", "zo"]
        ophaaldagen = st.multiselect("Ophaaldagen *", options=ophaaldagen_opties)

        laadinstructie = st.text_area("Laadinstructie chauffeur")
        uiterlijke_tijd = st.text_input("Uiterlijke tijd (HH:MM)", placeholder="21:30")
        bijzonderheden = st.text_input("Bijzonderheden (bijv. 'Sleutel nodig')")
        ophalen = st.checkbox("Wij halen op", value=True)

        submitted = st.form_submit_button("Toevoegen", type="primary")

    if submitted:
        if not voornaam or not achternaam or not ophaaldagen:
            st.error("Vul minstens voornaam, achternaam en ophaaldagen in.")
            return

        m = Monsternemer(
            id=None,
            code="AP06",
            voornaam=voornaam.strip(),
            tussenvoegsel=tussenvoegsel.strip() or None,
            achternaam=achternaam.strip(),
            adres=adres.strip(),
            postcode=postcode.strip().upper(),
            woonplaats=woonplaats.strip(),
            telefoon=telefoon.strip() or None,
            laadinstructie=laadinstructie.strip() or None,
            ophaaldagen=ophaaldagen,
            uiterlijke_tijd=uiterlijke_tijd.strip() or None,
            bijzonderheden=bijzonderheden.strip() or None,
            ophalen=ophalen,
        )
        nieuw_id = voeg_monsternemer_toe(m)
        st.success(f"✅ {m.volledige_naam} toegevoegd (ID: {nieuw_id}).")


def _render_import():
    st.subheader("Importeren vanuit AP06 xlsx-bestand")
    st.caption(
        "Verwacht het standaard AP06 monsternemer-bestand met kolommen: "
        "Code, Voornaam, Tussenvoegsel, Achternaam, Adres, Postcode, Plaats, "
        "Land, Mobiel, Laadinstructie, Ophaaldagen, Sjabloon, Uiterlijke tijd, Bijzonderheden"
    )

    uploaded = st.file_uploader(
        "Kies het monsternemer-xlsx bestand",
        type=["xlsx"],
        key="import_upload",
    )

    if not uploaded:
        return

    bytes_data = BytesIO(uploaded.read())
    wb = load_workbook(bytes_data, data_only=True)
    ws = wb.active

    preview_data = []
    monsternemers_te_importeren = []

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if all(v is None for v in row):
            break
        if len(row) < 9:
            continue

        code = str(row[0]).strip() if row[0] else "AP06"
        voornaam = str(row[1]).strip() if row[1] else ""
        tussenvoegsel = str(row[2]).strip() if row[2] else None
        achternaam = str(row[3]).strip() if row[3] else ""
        adres = str(row[4]).strip() if row[4] else ""
        postcode = str(row[5]).strip() if row[5] else ""
        woonplaats = str(row[6]).strip() if row[6] else ""
        telefoon = str(row[8]).strip().replace("'", "") if row[8] else None
        laadinstructie = str(row[9]).strip() if (len(row) > 9 and row[9]) else None
        ophaaldagen_str = str(row[10]).strip() if (len(row) > 10 and row[10]) else ""
        ophaaldagen = [d.strip() for d in ophaaldagen_str.split(",") if d.strip()]
        uiterlijke_tijd = None
        if len(row) > 13 and row[13]:
            ut = row[13]
            if hasattr(ut, "strftime"):
                uiterlijke_tijd = ut.strftime("%H:%M")
            else:
                uiterlijke_tijd = str(ut).strip()
        bijzonderheden = str(row[14]).strip() if (len(row) > 14 and row[14]) else None

        if not voornaam or not achternaam:
            continue

        m = Monsternemer(
            id=None, code=code,
            voornaam=voornaam, tussenvoegsel=tussenvoegsel or None,
            achternaam=achternaam, adres=adres, postcode=postcode,
            woonplaats=woonplaats, telefoon=telefoon,
            laadinstructie=laadinstructie, ophaaldagen=ophaaldagen,
            uiterlijke_tijd=uiterlijke_tijd, bijzonderheden=bijzonderheden,
            ophalen=True,
        )
        monsternemers_te_importeren.append(m)
        preview_data.append({
            "Naam": m.volledige_naam,
            "Woonplaats": woonplaats,
            "Ophaaldagen": ophaaldagen_str,
        })

    wb.close()

    if not preview_data:
        st.warning("Geen geldige monsternemers gevonden in het bestand.")
        return

    st.info(f"Gevonden: {len(preview_data)} monsternemers")
    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

    if st.button("✅ Importeer alle monsternemers", type="primary"):
        geimporteerd = 0
        for m in monsternemers_te_importeren:
            voeg_monsternemer_toe(m)
            geimporteerd += 1
        st.success(f"✅ {geimporteerd} monsternemers geïmporteerd.")
        st.rerun()
