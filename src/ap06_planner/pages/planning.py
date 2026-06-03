"""
planning.py — Upload en verwerk xlsx-planningsbestanden.
Stadium 1: Upload → JSON debug output per monsternemer.
"""

import json
import math
import re
from datetime import timedelta
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
from ap06_planner.services.nager_service import eerstvolgende_ophaaldag, is_feestdag
from ap06_planner.services.osrm_service import _geocodeer, bereken_aankomsttijd
from ap06_planner.utils.date_utils import DAGAFKORTINGEN, format_datum_nl, is_ophaaldag, parse_datum

_DAGBLOK_RE = re.compile(r"\b(?:dagblok|ochtendblok)\b", re.IGNORECASE)


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

    # Actuele planning overzicht — gegroepeerd op plandag
    st.divider()
    st.subheader("📋 Actuele planning")

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

            col_naam, col_tijd, col_reden = st.columns([4, 2, 4])
            with col_naam:
                st.write(naam_label)
            with col_tijd:
                st.write(gewensttijd)
            with col_reden:
                if toon_toelichting:
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
        "algemene_instructie_ap06": ALGEMENE_INSTRUCTIE_AP06,
        "gewensttijd": f"{gewensttijd_begin} - {gewensttijd_eind}",
        "niet_in_database": niet_in_db,
        "warnings": warnings,
    }
