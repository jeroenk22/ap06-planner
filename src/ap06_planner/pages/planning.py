"""
planning.py — Upload en verwerk xlsx-planningsbestanden.
Stadium 1: Upload → JSON debug output per monsternemer.
"""

import hashlib
import json
import math
import os
import re
from datetime import timedelta
from html import escape as html_escape
from io import BytesIO

import streamlit as st

from ap06_planner.models.schemas import ALGEMENE_INSTRUCTIE_AP06, Tijdvenster
from ap06_planner.parsers.tijdvenster import parse_tijdvenster
from ap06_planner.parsers.wijzigingen import pas_wijziging_toe, verwerk_wijzigingen
from ap06_planner.parsers.xlsx_parser import lees_planningsbestand
from ap06_planner.services.claude_service import (
    match_monsternemer_naam,
    verwerk_planningsregels_batch,
)
from ap06_planner.services.db_service import haal_alle_monsternemers, zoek_monsternemer
from ap06_planner.services.mendrix_service import (
    haal_mendrix_namen_en_ids,
    haal_mendrix_namen_ids_en_xml,
    maak_mendrix_order,
    update_mendrix_tijdvenster,
    werkdagen_van_week,
    zoek_mendrix_order,
)
from ap06_planner.services.nager_service import eerstvolgende_ophaaldag, is_feestdag
from ap06_planner.services.osrm_service import _geocodeer, bereken_aankomsttijd
from ap06_planner.utils.date_utils import DAGAFKORTINGEN, format_datum_nl, is_ophaaldag, parse_datum

_DAGBLOK_RE = re.compile(r"\b(?:dagblok|ochtendblok)\b", re.IGNORECASE)

_MENDRIX_KLEUR_HEX = {"groen": "#2e7d32", "geel": "#e65100", "rood": "#c62828"}


def _tijdafwijking_kleur(planning_begin: str, mendrix_van: str) -> str:
    """Vergelijk planning begintijd met Mendrix van-tijd. Groen < 30 min, geel >= 30 min."""
    try:
        ph, pm = int(planning_begin[:2]), int(planning_begin[3:5])
        mh, mm = int(mendrix_van[:2]), int(mendrix_van[3:5])
        diff = abs(ph * 60 + pm - (mh * 60 + mm))
        if diff >= 30:
            return "geel"
        return "groen"
    except (ValueError, IndexError):
        return "groen"


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

    raw_bytes = uploaded.read()
    file_hash = hashlib.md5(raw_bytes).hexdigest()
    cache_key = f"planning_{file_hash}"

    mendrix_cache_key = f"mendrix_{cache_key}"

    if st.session_state.get("_actieve_cache_key") != cache_key:  # pragma: no cover
        prev = st.session_state.get("_actieve_cache_key")  # pragma: no cover
        if prev:  # pragma: no cover
            st.session_state.pop(f"mendrix_{prev}", None)  # pragma: no cover
        st.session_state["_actieve_cache_key"] = cache_key  # pragma: no cover
        st.session_state["mendrix_update_resultaten"] = {}  # pragma: no cover
        st.session_state["mendrix_bijgewerkte_tijden"] = {}  # pragma: no cover

    if cache_key in st.session_state:
        alle_output = st.session_state[cache_key]["alle_output"]
        tab_resultaten = st.session_state[cache_key]["tab_resultaten"]
    else:
        with st.spinner("Bestand inlezen..."):
            bestand_bytes = BytesIO(raw_bytes)
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
        tab_resultaten: list[dict] = []

        st.markdown(
            """
<style>
[data-testid="stStatusWidget"] [data-testid="stSpinnerIcon"] {
    animation: spin 0.8s linear infinite !important;
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
""",
            unsafe_allow_html=True,
        )

        with st.status("Planning verwerken…", expanded=True) as status:
            for i, tab in enumerate(tabbladen, 1):
                datum_str = tab.get("datum")
                dagnaam = tab.get("dagnaam", "onbekend")
                regels = tab.get("regels", [])
                datum = parse_datum(datum_str) if datum_str else None

                per_monsternemer: dict[str, list] = {}
                for r in regels:
                    if not r.overgeslagen:
                        per_monsternemer.setdefault(r.monsternemer_naam, []).append(r)

                status.write(
                    f"📅 Tabblad {i}/{len(tabbladen)}: "
                    f"{dagnaam.capitalize()} {datum_str or '??'} "
                    f"— {len(per_monsternemer)} monsternemers"
                )

                batch_input = [
                    {
                        "locatie": r.locatie_raw or r.klant_raw or "",
                        "wijziging": _DAGBLOK_RE.sub("", r.wijzigingen or "").strip() or None,
                    }
                    for r in regels
                    if not r.overgeslagen and (r.locatie_raw or r.klant_raw)
                ]
                claude_tv_cache: dict[tuple, dict] = {}
                batch_fout = None
                if batch_input:
                    status.write(f"   ↳ AI analyseert {len(batch_input)} locaties…")
                    batch_resultaten_lijst, batch_fout = verwerk_planningsregels_batch(batch_input)
                    if not batch_fout and batch_resultaten_lijst:
                        for invoer, uitvoer in zip(batch_input, batch_resultaten_lijst, strict=False):
                            claude_tv_cache[(invoer["locatie"], invoer["wijziging"])] = uitvoer

                status.write(
                    f"   ↳ Ophaaldata en reistijden bepalen voor {len(per_monsternemer)} monsternemers…"
                )

                overgeslagen_namen: list[str] = []
                for naam, naam_regels in per_monsternemer.items():
                    output = _verwerk_monsternemer(
                        naam=naam,
                        regels=naam_regels,
                        datum=datum,
                        dagnaam=dagnaam,
                        bekende_namen=bekende_namen,
                        bekende_monsternemers=bekende_monsternemers,
                        claude_tv_cache=claude_tv_cache,
                    )
                    if output is not None:
                        alle_output.append(output)
                    else:
                        overgeslagen_namen.append(naam)

                tab_resultaten.append(
                    {
                        "datum_str": datum_str,
                        "datum": datum,
                        "dagnaam": dagnaam,
                        "regels": regels,
                        "per_monsternemer": per_monsternemer,
                        "kolommap": tab.get("kolommap", {}),
                        "batch_fout": batch_fout,
                        "overgeslagen_namen": overgeslagen_namen,
                    }
                )

            status.update(
                label=f"✅ Verwerking klaar — {len(alle_output)} monsternemers",
                state="complete",
                expanded=False,
            )

        st.session_state[cache_key] = {
            "alle_output": alle_output,
            "tab_resultaten": tab_resultaten,
        }

    for res in tab_resultaten:
        datum_str = res["datum_str"]
        dagnaam = res["dagnaam"]
        regels = res["regels"]
        per_monsternemer = res["per_monsternemer"]

        st.subheader(f"📅 {dagnaam.capitalize()} {datum_str or '??'}")
        st.caption(
            f"{len(regels)} regels, {sum(r.overgeslagen for r in regels)} overgeslagen, "
            f"{len(per_monsternemer)} unieke monsternemers"
        )
        if res["batch_fout"]:
            st.warning(
                f"⚠️ Claude batch-verwerking mislukt: {res['batch_fout']} — regex-fallback actief"
            )
        with st.expander("🔧 Debug: gedetecteerde kolommen", expanded=False):
            st.json(res["kolommap"])

        if res["overgeslagen_namen"]:
            with st.expander(
                f"⏭️ Overgeslagen ({len(res['overgeslagen_namen'])}) — geen geldige ophaaldagen",
                expanded=True,
            ):
                st.caption(
                    "Deze monsternemers staan in het xlsx maar hebben geen geldige ophaaldagen in de database."
                )
                for n in res["overgeslagen_namen"]:
                    st.write(f"- {n}")

    # Mendrix-pass — altijd vers ophalen (los van xlsx-cache)
    mendrix_xml_per_order: dict[int, str] = {}
    if os.getenv("MENDRIX_SOAP_URL"):  # pragma: no cover
        if mendrix_cache_key not in st.session_state:  # pragma: no cover
            _mendrix_cache: dict[str, dict] = {}  # pragma: no cover
            _mendrix_xml: dict[int, str] = {}  # pragma: no cover
            _mendrix_keys = {  # pragma: no cover
                "mendrix_order_id", "mendrix_naam", "mendrix_van", "mendrix_tot",
                "mendrix_tijdvenster", "mendrix_andere_order_id", "mendrix_andere_datum", "mendrix_andere_naam",
            }
            for output in alle_output:  # pragma: no cover
                for k in _mendrix_keys:  # pragma: no cover
                    output.pop(k, None)  # pragma: no cover
                inplan_str = output.get("inplannen_op", "")  # pragma: no cover
                datum_deel = inplan_str.split()[-1] if inplan_str else ""  # pragma: no cover
                if datum_deel and datum_deel not in _mendrix_cache:  # pragma: no cover
                    try:  # pragma: no cover
                        d = parse_datum(datum_deel)  # pragma: no cover
                        if d:  # pragma: no cover
                            namen_ids, order_xmls = haal_mendrix_namen_ids_en_xml(d)  # pragma: no cover
                            _mendrix_cache[datum_deel] = namen_ids  # pragma: no cover
                            _mendrix_xml.update(order_xmls)  # pragma: no cover
                        else:  # pragma: no cover
                            _mendrix_cache[datum_deel] = {}  # pragma: no cover
                    except Exception:  # pragma: no cover
                        _mendrix_cache[datum_deel] = {}  # pragma: no cover
                namen_ids = _mendrix_cache.get(datum_deel, {})  # pragma: no cover
                order_id, mendrix_naam = zoek_mendrix_order(output["naam_monsternemer"], namen_ids)  # pragma: no cover
                output["mendrix_order_id"] = order_id  # pragma: no cover
                output["mendrix_naam"] = mendrix_naam  # pragma: no cover
                if mendrix_naam and mendrix_naam in namen_ids:  # pragma: no cover
                    info = namen_ids[mendrix_naam]  # pragma: no cover
                    van = info.get("van")  # pragma: no cover
                    tot = info.get("tot")  # pragma: no cover
                    output["mendrix_van"] = van or ""  # pragma: no cover
                    output["mendrix_tot"] = tot or ""  # pragma: no cover
                    output["mendrix_tijdvenster"] = f"{van}-{tot}" if van and tot else ""  # pragma: no cover

            # Vul week-cache aan voor tweede pass
            weken: set[tuple[int, int]] = set()  # pragma: no cover
            for output in alle_output:  # pragma: no cover
                inplan_str = output.get("inplannen_op", "")  # pragma: no cover
                datum_deel = inplan_str.split()[-1] if inplan_str else ""  # pragma: no cover
                if datum_deel:  # pragma: no cover
                    d = parse_datum(datum_deel)  # pragma: no cover
                    if d:  # pragma: no cover
                        weken.add(d.isocalendar()[:2])  # pragma: no cover
            from datetime import date as _date  # pragma: no cover
            for jaar, week in weken:  # pragma: no cover
                ankerdag = _date.fromisocalendar(jaar, week, 1)  # pragma: no cover
                for dag in werkdagen_van_week(ankerdag):  # pragma: no cover
                    dag_str = dag.strftime("%d-%m-%Y")  # pragma: no cover
                    if dag_str not in _mendrix_cache:  # pragma: no cover
                        try:  # pragma: no cover
                            _mendrix_cache[dag_str] = haal_mendrix_namen_en_ids(dag)  # pragma: no cover
                        except Exception:  # pragma: no cover
                            _mendrix_cache[dag_str] = {}  # pragma: no cover

            # Tweede pass: ❌-monsternemers op andere datum in dezelfde week
            for output in alle_output:  # pragma: no cover
                if output.get("mendrix_order_id") is not None or "mendrix_order_id" not in output:  # pragma: no cover
                    continue  # pragma: no cover
                inplan_str = output.get("inplannen_op", "")  # pragma: no cover
                eigen_datum = inplan_str.split()[-1] if inplan_str else ""  # pragma: no cover
                eigen_d = parse_datum(eigen_datum) if eigen_datum else None  # pragma: no cover
                eigen_week = eigen_d.isocalendar()[:2] if eigen_d else None  # pragma: no cover
                kandidaat_datums = []  # pragma: no cover
                for dag_str, namen_ids in _mendrix_cache.items():  # pragma: no cover
                    if dag_str == eigen_datum or not namen_ids:  # pragma: no cover
                        continue  # pragma: no cover
                    d_cached = parse_datum(dag_str)  # pragma: no cover
                    if not d_cached:  # pragma: no cover
                        continue  # pragma: no cover
                    if eigen_week and d_cached.isocalendar()[:2] != eigen_week:  # pragma: no cover
                        continue  # pragma: no cover
                    if eigen_d and d_cached <= eigen_d:  # pragma: no cover
                        continue  # pragma: no cover
                    kandidaat_datums.append(((d_cached - eigen_d).days if eigen_d else 0, dag_str, namen_ids))  # pragma: no cover
                for _, dag_str, namen_ids in sorted(kandidaat_datums):  # pragma: no cover
                    order_id, mendrix_naam = zoek_mendrix_order(output["naam_monsternemer"], namen_ids, gebruik_ai_fallback=False)  # pragma: no cover
                    if order_id:  # pragma: no cover
                        output["mendrix_andere_order_id"] = order_id  # pragma: no cover
                        output["mendrix_andere_datum"] = dag_str  # pragma: no cover
                        output["mendrix_andere_naam"] = mendrix_naam  # pragma: no cover
                        break  # pragma: no cover

            st.session_state[mendrix_cache_key] = _mendrix_xml  # pragma: no cover

        mendrix_xml_per_order = st.session_state.get(mendrix_cache_key, {})  # pragma: no cover

    # Actuele planning overzicht — gegroepeerd op plandag
    st.divider()
    _col_title, _col_btn = st.columns([6, 1])
    _col_title.subheader("📋 Actuele planning")
    if os.getenv("MENDRIX_SOAP_URL") and _col_btn.button("🔄 Mendrix", help="Mendrix-orders opnieuw ophalen"):  # pragma: no cover
        st.session_state.pop(mendrix_cache_key, None)  # pragma: no cover
        st.session_state["mendrix_update_resultaten"] = {}  # pragma: no cover
        st.session_state["mendrix_bijgewerkte_tijden"] = {}  # pragma: no cover
        st.rerun()  # pragma: no cover

    if os.getenv("MENDRIX_SOAP_URL") and "mendrix_update_resultaten" not in st.session_state:  # pragma: no cover
        st.session_state.mendrix_update_resultaten = {}  # pragma: no cover
        st.session_state.mendrix_bijgewerkte_tijden = {}  # pragma: no cover

    plandag_output: dict[str, list[dict]] = {}
    for rec in alle_output:
        plandag = rec.get("inplannen_op") or rec.get("datum") or "—"
        al_ingepland = {r["naam_monsternemer"] for r in plandag_output.get(plandag, [])}
        if rec.get("naam_monsternemer") not in al_ingepland:
            plandag_output.setdefault(plandag, []).append(rec)

    def _plandag_sorteersleutel(dag: str) -> str:
        # "woensdag 03-06-2026" → "2026-06-03" voor sortering
        delen = dag.split()
        if len(delen) == 2:
            d, m, y = delen[1].split("-")
            return f"{y}-{m}-{d}"
        return dag

    for plandag in sorted(plandag_output, key=_plandag_sorteersleutel):
        records = sorted(plandag_output[plandag], key=lambda r: r.get("naam_monsternemer", ""))
        # Dag met hoofdletter
        plandag_label = plandag[0].upper() + plandag[1:] if plandag else plandag
        st.markdown(f"### {plandag_label}")

        for rec in records:
            naam = rec.get("naam_monsternemer", "")
            ophaaldagen = rec.get("standaard_ophaaldagen") or []
            gewensttijd = rec.get("gewensttijd") or "—"
            toelichting = rec.get("inplannen_toelichting") or ""

            # "Monsters van vandaag" niet tonen
            toon_toelichting = toelichting if "geen ophaaldag" not in toelichting else ""

            ophaaldagen_str = f"({', '.join(ophaaldagen)})" if ophaaldagen else ""
            naam_label = f"{naam} {ophaaldagen_str}".strip()

            mendrix_order_id = rec.get("mendrix_order_id")
            mendrix_naam = rec.get("mendrix_naam")
            mendrix_tijdvenster = rec.get("mendrix_tijdvenster", "")
            mendrix_van = rec.get("mendrix_van", "")
            if mendrix_order_id:  # pragma: no cover
                bijgewerkt = st.session_state.get("mendrix_bijgewerkte_tijden", {}).get(mendrix_order_id)  # pragma: no cover
                if bijgewerkt:  # pragma: no cover
                    mendrix_van, mendrix_tot_bijgewerkt = bijgewerkt  # pragma: no cover
                    mendrix_tijdvenster = f"{mendrix_van}-{mendrix_tot_bijgewerkt}"  # pragma: no cover
            mendrix_icon = ""
            mendrix_tip = ""
            mendrix_tv_html = ""
            bijwerken_data = None
            if "mendrix_order_id" in rec:
                if mendrix_order_id:
                    mendrix_icon = "✅"
                    mendrix_tip = f"Order #{mendrix_order_id} ({mendrix_naam})"
                    if mendrix_tijdvenster:  # pragma: no cover
                        gewensttijd_str = rec.get("gewensttijd") or ""  # pragma: no cover
                        gewenst_begin = gewensttijd_str.split(" - ")[0]  # pragma: no cover
                        kleur = (  # pragma: no cover
                            _tijdafwijking_kleur(gewenst_begin, mendrix_van)
                            if (gewenst_begin and mendrix_van)
                            else "groen"
                        )
                        hex_kleur = _MENDRIX_KLEUR_HEX[kleur]  # pragma: no cover
                        mendrix_tv_html = (  # pragma: no cover
                            f'<span style="color:{hex_kleur};font-weight:600">'
                            f"{html_escape(mendrix_tijdvenster)}</span>"
                        )
                        if kleur == "geel":  # pragma: no cover
                            bijwerken_data = {  # pragma: no cover
                                "order_id": mendrix_order_id,
                                "planning_begin": gewenst_begin,
                                "planning_eind": gewensttijd_str.split(" - ")[-1],
                            }
                elif rec.get("mendrix_andere_order_id"):
                    mendrix_icon = "⚠️"
                    mendrix_tip = (
                        f"Order #{rec['mendrix_andere_order_id']} staat op "
                        f"{rec['mendrix_andere_datum']} ({rec.get('mendrix_andere_naam', '')})"
                    )
                else:
                    mendrix_icon = "❌"
                    mendrix_tip = "Nog geen order in Mendrix"

            col_naam, col_tijd, col_mendrix, col_reden = st.columns([4, 2, 2, 4])
            with col_naam:
                st.write(naam_label)
            with col_tijd:
                st.write(gewensttijd)
            with col_mendrix:
                if mendrix_icon:
                    if mendrix_tv_html:
                        st.markdown(
                            f"{mendrix_icon} {mendrix_tv_html}<br>"
                            f'<span style="font-size:0.8em;color:#888">{html_escape(mendrix_tip)}</span>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption(f"{mendrix_icon} {mendrix_tip}")
            with col_reden:
                if bijwerken_data:  # pragma: no cover
                    sleutel = f"upd_{bijwerken_data['order_id']}"  # pragma: no cover
                    resultaat = st.session_state.mendrix_update_resultaten.get(sleutel)  # pragma: no cover
                    if resultaat is None:  # pragma: no cover
                        if st.button("🔄 Bijwerken", key=sleutel):  # pragma: no cover
                            cached_xml = mendrix_xml_per_order.get(bijwerken_data["order_id"])  # pragma: no cover
                            succes, melding = update_mendrix_tijdvenster(  # pragma: no cover
                                bijwerken_data["order_id"],
                                bijwerken_data["planning_begin"],
                                bijwerken_data["planning_eind"],
                                cached_xml=cached_xml,
                            )
                            st.session_state.mendrix_update_resultaten[sleutel] = (succes, melding)  # pragma: no cover
                            if succes:  # pragma: no cover
                                st.session_state.mendrix_bijgewerkte_tijden[bijwerken_data["order_id"]] = (  # pragma: no cover
                                    bijwerken_data["planning_begin"],
                                    bijwerken_data["planning_eind"],
                                )
                            st.rerun()  # pragma: no cover
                    elif resultaat[0]:  # pragma: no cover
                        st.success("✓ bijgewerkt")  # pragma: no cover
                    else:  # pragma: no cover
                        st.error(resultaat[1])  # pragma: no cover
                elif mendrix_icon == "❌" and rec.get("adres") and not rec.get("niet_in_database"):  # pragma: no cover
                    sleutel = f"new_{rec['naam_monsternemer']}_{rec.get('inplannen_op', '')}"  # pragma: no cover
                    resultaat = st.session_state.mendrix_update_resultaten.get(sleutel)  # pragma: no cover
                    if resultaat is None:  # pragma: no cover
                        if st.button("➕ Aanmaken", key=sleutel):  # pragma: no cover
                            gewensttijd_str = rec.get("gewensttijd") or ""  # pragma: no cover
                            delen = gewensttijd_str.split(" - ")  # pragma: no cover
                            inplan_d = parse_datum(rec.get("inplannen_op", "").split()[-1])  # pragma: no cover
                            if inplan_d and len(delen) == 2:  # pragma: no cover
                                succes, melding = maak_mendrix_order(  # pragma: no cover
                                    naam=rec["naam_monsternemer"],
                                    adres=rec.get("adres") or "",
                                    postcode=rec.get("postcode") or "",
                                    woonplaats=rec.get("woonplaats") or "",
                                    telefoon=rec.get("telefoon"),
                                    bijzonderheden=rec.get("bijzonderheden_laden"),
                                    laadinstructie=rec.get("laadinstructie"),
                                    uiterlijke_plantijd=rec.get("uiterlijke_plantijd"),
                                    algemene_instructie_ap06=rec.get("algemene_instructie_ap06", ""),
                                    ophaaldagen=rec.get("standaard_ophaaldagen") or [],
                                    inplan_datum=inplan_d,
                                    gewensttijd_begin=delen[0],
                                    gewensttijd_eind=delen[1],
                                )
                            else:  # pragma: no cover
                                succes, melding = False, "Ongeldige inplandatum of gewensttijd"  # pragma: no cover
                            st.session_state.mendrix_update_resultaten[sleutel] = (succes, melding)  # pragma: no cover
                            if succes:  # pragma: no cover
                                st.session_state.pop(mendrix_cache_key, None)  # pragma: no cover
                            st.rerun()  # pragma: no cover
                    elif resultaat[0]:  # pragma: no cover
                        st.success(f"✓ {resultaat[1]}")  # pragma: no cover
                    else:  # pragma: no cover
                        st.error(resultaat[1])  # pragma: no cover
                elif toon_toelichting:
                    st.caption(toon_toelichting)

    # JSON output ingeklapt onderaan
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col2:
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(alle_output, indent=2, ensure_ascii=False),
            file_name=f"ap06_output_{alle_output[0].get('datum', 'datum') if alle_output else 'output'}.json",
            mime="application/json",
        )
    with st.expander("🔍 Debug JSON output", expanded=False):
        st.caption("Ruwe output van Stadium 1.")
        st.json(alle_output)


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))


def _kies_laatste_tv(
    tijdvensters: list,
    woonplaats: str | None,
    postcode: str | None,
    bereken_tiebreak: bool = True,
) -> tuple:
    """
    Kies het laatste tijdvenster. Bij gelijke eindtijd en bereken_tiebreak=True:
    verste locatie van de woonplaats. Retourneert (Tijdvenster | None, extra_warnings: list[str]).
    """
    if not tijdvensters:
        return None, []

    max_eind = max(tv.eindtijd for tv in tijdvensters)
    kandidaten = [tv for tv in tijdvensters if tv.eindtijd == max_eind]

    if len(kandidaten) == 1:
        return kandidaten[0], []

    # Tie — meerdere locaties met dezelfde eindtijd
    plaatsnamen = [tv.plaats for tv in kandidaten]

    if not bereken_tiebreak:
        return kandidaten[0], []

    if not woonplaats:
        return kandidaten[0], [
            f"Meerdere tijdvensters eindigen op {max_eind} ({plaatsnamen}) — "
            "geen woonplaats beschikbaar voor afstandsbepaling, eerste gekozen"
        ]

    thuis_query = f"{postcode} {woonplaats}, Nederland" if postcode else f"{woonplaats}, Nederland"
    thuis_result = _geocodeer(thuis_query)
    if not thuis_result:
        return kandidaten[0], [
            f"Meerdere tijdvensters eindigen op {max_eind} ({plaatsnamen}) — "
            "geocoding woonplaats mislukt, eerste gekozen"
        ]

    _, (thuis_lon, thuis_lat) = thuis_result
    verste_tv = None
    max_km = -1.0

    for tv in kandidaten:
        plaats_result = _geocodeer(f"{tv.plaats}, Nederland")
        if not plaats_result:
            continue
        _, (lon, lat) = plaats_result
        km = _haversine_km(lon, lat, thuis_lon, thuis_lat)
        if km > max_km:
            max_km = km
            verste_tv = tv

    if verste_tv:
        return verste_tv, [
            f"Meerdere tijdvensters eindigen op {max_eind} ({plaatsnamen}) — "
            f"verste van {woonplaats}: {verste_tv.plaats} ({max_km:.0f} km) → gekozen als laatste locatie"
        ]

    return kandidaten[0], []


def _verwerk_monsternemer(
    naam: str,
    regels: list,
    datum,
    dagnaam: str,
    bekende_namen: list[str],
    bekende_monsternemers: list,
    claude_tv_cache: dict | None = None,
) -> dict | None:
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

    # Verzamel alle tijdvensters via Claude-cache (of regex-fallback)
    tijdvensters = []
    geen_tv_regels = []
    min_eind_cap: str | None = None
    for r in regels:
        locatie_tekst = r.locatie_raw or r.klant_raw or ""
        wijziging_genorm = _DAGBLOK_RE.sub("", r.wijzigingen or "").strip() or None
        sleutel = (locatie_tekst, wijziging_genorm)
        claude_data = (claude_tv_cache or {}).get(sleutel)

        if claude_data:
            if claude_data.get("overgeslagen"):
                continue
            eindtijd_raw = claude_data.get("eindtijd")
            if not eindtijd_raw:
                warnings.append(
                    f"⚠️ Claude gaf geen eindtijd voor '{locatie_tekst}' — fallback naar 23:59"
                )
            tv = Tijdvenster(
                plaats=claude_data.get("plaats") or "",
                klant_naam="",
                begintijd=claude_data.get("begintijd") or "00:00",
                eindtijd=eindtijd_raw or "23:59",
                type=claude_data.get("type") or "LAD",
                nummer=claude_data.get("nummer"),
                origineel=locatie_tekst,
            )
            if r.wijzigingen:
                warnings.append(
                    f"'{r.wijzigingen}' verwerkt → {tv.begintijd}-{tv.eindtijd} ({tv.plaats})"
                )
                wij = verwerk_wijzigingen(r.wijzigingen)
                if wij.persoon_eind_voor and (
                    min_eind_cap is None or wij.persoon_eind_voor < min_eind_cap
                ):
                    min_eind_cap = wij.persoon_eind_voor
        else:
            # Fallback: regex
            tv = parse_tijdvenster(locatie_tekst)
            if not tv:
                geen_tv_regels.append(f"locatie={r.locatie_raw!r} klant={r.klant_raw!r}")
                continue
            if r.wijzigingen:
                wijziging = verwerk_wijzigingen(r.wijzigingen)
                if not wijziging.negeer:
                    tv_voor = f"{tv.begintijd}-{tv.eindtijd}"
                    tv = pas_wijziging_toe(tv, wijziging)
                    if (
                        tv.begintijd != tv_voor.split("-")[0]
                        or tv.eindtijd != tv_voor.split("-")[1]
                    ):
                        warnings.append(
                            f"Tijdvenster aangepast door '{r.wijzigingen}': "
                            f"{tv_voor} → {tv.begintijd}-{tv.eindtijd} ({tv.plaats})"
                        )
                    if wijziging.persoon_eind_voor and (
                        min_eind_cap is None or wijziging.persoon_eind_voor < min_eind_cap
                    ):
                        min_eind_cap = wijziging.persoon_eind_voor
                else:
                    continue

        tijdvensters.append(tv)

    if geen_tv_regels:
        warnings.append(f"Geen tijdvenster gevonden in: {'; '.join(geen_tv_regels)}")

    if tijdvensters:
        warnings.append(
            "Geparsede tijdvensters: "
            + " | ".join(f"{t.plaats} {t.begintijd}-{t.eindtijd}" for t in tijdvensters)
        )

    # Ophaaldag-logica — filter ongeldige waarden zoals "geen"
    ophaaldagen_raw = monsternemer.ophaaldagen if monsternemer else []
    ophaaldagen = [d for d in ophaaldagen_raw if d in DAGAFKORTINGEN]

    # Monsternemer zonder geldige ophaaldagen overslaan
    if monsternemer and not ophaaldagen:
        return None

    huidige_dag_is_ophaaldag = is_ophaaldag(datum, ophaaldagen) if datum and ophaaldagen else False

    # Laatste tijdvenster bepalen — tiebreak (geocoding) alleen nodig op een echte ophaaldag
    woonplaats_m = monsternemer.woonplaats if monsternemer else None
    postcode_m = monsternemer.postcode if monsternemer else None
    laatste_tv, tie_warnings = _kies_laatste_tv(
        tijdvensters,
        woonplaats_m,
        postcode_m,
        bereken_tiebreak=huidige_dag_is_ophaaldag,
    )
    warnings.extend(tie_warnings)

    # Effectieve eindtijd: cap van 'persoon_eind_voor' wint van tijdvenster-eindtijd
    effective_eindtijd: str | None = None
    if laatste_tv:
        effective_eindtijd = (
            min(min_eind_cap, laatste_tv.eindtijd) if min_eind_cap else laatste_tv.eindtijd
        )

    # Inplanning
    inplannen_op_str = ""
    inplannen_toelichting = None
    gewensttijd_begin = "10:00"
    gewensttijd_eind = monsternemer.uiterlijke_tijd if monsternemer else None
    gewensttijd_eind = gewensttijd_eind or "23:59"

    if datum and ophaaldagen:
        if huidige_dag_is_ophaaldag:
            if is_feestdag(datum):
                volgende, _ = eerstvolgende_ophaaldag(datum, ophaaldagen)
                inplannen_op_str = format_datum_nl(volgende)
                inplannen_toelichting = f"Feestdag op {datum.strftime('%d-%m-%Y')} → verschoven"
            else:
                inplannen_op_str = format_datum_nl(datum)
                if laatste_tv and monsternemer and effective_eindtijd:
                    vertrekplaats = laatste_tv.plaats
                    gewensttijd_begin, gewensttijd_eind, reistijd_debug = bereken_aankomsttijd(
                        vertrekplaats=vertrekplaats,
                        woonplaats=monsternemer.woonplaats,
                        woonplaats_postcode=monsternemer.postcode,
                        eind_tijdvenster=effective_eindtijd,
                        uiterlijke_tijd=monsternemer.uiterlijke_tijd,
                    )
                    warnings.append(f"Reistijd: {reistijd_debug}")

                    # Onmogelijk venster: aankomsttijd valt na uiterlijke_tijd
                    if (
                        monsternemer.uiterlijke_tijd
                        and gewensttijd_begin > monsternemer.uiterlijke_tijd
                    ):
                        warnings.append(
                            f"⚠️ Aankomsttijd {gewensttijd_begin} valt na uiterlijke tijd "
                            f"{monsternemer.uiterlijke_tijd} — tijdconflict"
                        )
                        gewensttijd_eind = "23:59"

                    # Planningtechnisch te laat? → verschuif naar volgende ophaaldag
                    if (
                        monsternemer.uiterlijke_plantijd
                        and gewensttijd_begin > monsternemer.uiterlijke_plantijd
                    ):
                        volgende, _ = eerstvolgende_ophaaldag(
                            datum + timedelta(days=1), ophaaldagen
                        )
                        inplannen_op_str = format_datum_nl(volgende)
                        inplannen_toelichting = (
                            f"Te laat thuis ({gewensttijd_begin} > uiterlijke plantijd "
                            f"{monsternemer.uiterlijke_plantijd}) → verschoven"
                        )
                        warnings.append(
                            f"⚠️ Aankomsttijd {gewensttijd_begin} valt na uiterlijke plantijd "
                            f"{monsternemer.uiterlijke_plantijd} → inplannen op {inplannen_op_str}"
                        )
                        gewensttijd_begin = "10:00"
                        gewensttijd_eind = monsternemer.uiterlijke_tijd or "23:59"
        else:
            volgende, _ = eerstvolgende_ophaaldag(datum, ophaaldagen)
            inplannen_op_str = format_datum_nl(volgende)
            inplannen_toelichting = "Monsters van vandaag (geen ophaaldag)"

    return {
        "dagnaam": dagnaam,
        "datum": datum.strftime("%d-%m-%Y") if datum else None,
        "naam_monsternemer": monsternemer.volledige_naam if monsternemer else naam,
        "adres": monsternemer.adres if monsternemer else None,
        "postcode": monsternemer.postcode if monsternemer else None,
        "woonplaats": monsternemer.woonplaats if monsternemer else None,
        "telefoon": monsternemer.telefoon if monsternemer else None,
        "laatste_tijdvenster_plaats": laatste_tv.plaats if laatste_tv else None,
        "laatste_tijdvenster": (
            f"{laatste_tv.begintijd} - {effective_eindtijd}"
            if laatste_tv and effective_eindtijd
            else None
        ),
        "standaard_ophaaldagen": ophaaldagen,
        "huidige_dag_is_ophaaldag": huidige_dag_is_ophaaldag,
        "inplannen_op": inplannen_op_str,
        "inplannen_toelichting": inplannen_toelichting,
        "laadinstructie": monsternemer.laadinstructie if monsternemer else None,
        "bijzonderheden_laden": monsternemer.bijzonderheden if monsternemer else None,
        "uiterlijke_plantijd": monsternemer.uiterlijke_plantijd if monsternemer else None,
        "algemene_instructie_ap06": ALGEMENE_INSTRUCTIE_AP06,
        "gewensttijd": f"{gewensttijd_begin} - {gewensttijd_eind}",
        "niet_in_database": niet_in_db,
        "warnings": warnings,
    }
