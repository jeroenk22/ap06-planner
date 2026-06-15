"""
textmebot_service.py — WhatsApp berichten sturen via TextMeBot API.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import requests

_log = logging.getLogger("ap06.textmebot")


def stuur_whatsapp(bericht: str) -> tuple[bool, str]:
    """
    Stuur een WhatsApp bericht via de TextMeBot API.

    Vereiste omgevingsvariabelen:
      TEXTMEBOT_API_KEY    — jouw TextMeBot API key
      TEXTMEBOT_ONTVANGER  — telefoonnummer met landcode, bijv. +31612345678

    Returns (succes, melding).
    """
    api_key = os.getenv("TEXTMEBOT_API_KEY", "")
    ontvanger = os.getenv("TEXTMEBOT_ONTVANGER", "")

    if not api_key or not ontvanger:
        return False, "TEXTMEBOT_API_KEY of TEXTMEBOT_ONTVANGER niet ingesteld"

    url = "https://api.textmebot.com/send.php"
    _log.info("Verzenden naar: %s (ontvanger: %s)", url, ontvanger)
    _log.info("Bericht inhoud:\n%s", bericht)
    try:
        resp = requests.get(
            url,
            params={"recipient": ontvanger, "apikey": api_key, "text": bericht},
            timeout=15,
        )
        resp.raise_for_status()
        tekst = resp.text.strip()
        _log.info("Respons: %s", tekst)
        return True, tekst
    except requests.RequestException as e:
        # Niet str(e) teruggeven — RequestException kan de volledige URL incl. apikey bevatten
        _log.warning("WhatsApp sturen mislukt: %s", type(e).__name__, exc_info=True)
        return False, "WhatsApp verzending mislukt (zie log voor details)"


def _plandag_sorteersleutel(datum_key: str) -> str:
    """'11-06-2026' → '2026-06-11' voor chronologische sortering."""
    try:
        d, m, y = datum_key.split("-")
        return f"{y}-{m}-{d}"
    except ValueError:
        return datum_key


def bereken_alle_groen(
    alle_output: list[dict],
    mendrix_bijgewerkte_tijden: dict,
    mendrix_update_resultaten: dict,
    tijdafwijking_kleur_fn,
) -> bool:
    """
    True als alle monsternemers een Mendrix order hebben én geen tijdverschillen meer openstaan.

    Parameters:
        alle_output: lijst van output-dicts uit de planning-verwerking
        mendrix_bijgewerkte_tijden: {order_id: (begin, eind)} van bijgewerkte orders
        mendrix_update_resultaten: {sleutel: (succes, melding)} van uitgevoerde bijwerkacties
        tijdafwijking_kleur_fn: callable(_tijdafwijking_kleur) uit planning.py
    """
    for rec in alle_output:
        if "mendrix_order_id" not in rec:
            return False
        order_id = rec.get("mendrix_order_id")
        if order_id is None:
            return False
        mendrix_tv = rec.get("mendrix_tijdvenster", "")
        if not mendrix_tv:
            continue
        bijgewerkt = mendrix_bijgewerkte_tijden.get(order_id)
        if bijgewerkt:
            mv, mt = bijgewerkt
        else:
            mv = rec.get("mendrix_van", "")
            mt = rec.get("mendrix_tot", "")
        if not mv:
            continue
        gewensttijd_str = rec.get("gewensttijd") or ""
        gb = gewensttijd_str.split(" - ")[0]
        ge = gewensttijd_str.split(" - ")[-1] if " - " in gewensttijd_str else ""
        kleur = tijdafwijking_kleur_fn(gb, mv, ge, mt)
        if kleur == "geel":
            sleutel = f"upd_{order_id}"
            if mendrix_update_resultaten.get(sleutel) is None:
                return False
    return True


def bouw_whatsapp_bericht(
    alle_output: list[dict],
    mendrix_bijgewerkte_tijden: dict,
    xlsx_naam: str,
    xlsx_url: str = "",
    mendrix_update_resultaten: dict | None = None,
    mendrix_originele_tijden: dict | None = None,
) -> str:
    """
    Bouw een WhatsApp-samenvatting per plandag.

    Per monsternemer: naam, ordernummer, gewensttijd.
    Als de tijd bijgewerkt is: toon de oude Mendrix-tijd erbij.
    Als het order nieuw aangemaakt is: toon 'nieuw aangemaakt'.
    Als de tijd al klopte: toon 'geen tijdswijziging'.
    Als xlsx_url opgegeven: link onderaan het bericht.
    Duplicaten (zelfde naam + order_id per dag) worden overgeslagen.
    """
    update_res = mendrix_update_resultaten or {}
    orig_tijden = mendrix_originele_tijden or {}

    per_datum: dict[str, list[dict]] = {}
    datum_labels: dict[str, str] = {}
    for rec in alle_output:
        inplan = (rec.get("inplannen_op") or "").strip()
        delen = inplan.split()
        datum_key = delen[-1] if delen else "—"
        per_datum.setdefault(datum_key, []).append(rec)
        if datum_key not in datum_labels:
            datum_labels[datum_key] = inplan

    regels = [
        "📋 *AP06 Planning samenvatting*",
        f"Bestand: *{Path(xlsx_naam).name}*",
        f"Verwerkt: *{datetime.now().strftime('%d-%m-%Y %H:%M')}*",
        "",
    ]

    for datum_key in sorted(per_datum, key=_plandag_sorteersleutel):
        label = datum_labels.get(datum_key, datum_key)
        label = label[0].upper() + label[1:] if label else datum_key
        regels.append(f"📅 *{label}*")

        records = sorted(per_datum[datum_key], key=lambda r: r.get("naam_monsternemer", ""))
        gezien: set[tuple] = set()
        for rec in records:
            naam = rec.get("naam_monsternemer", "?")
            order_id = rec.get("mendrix_order_id")
            dedup_sleutel = (naam, order_id)
            if dedup_sleutel in gezien:
                continue
            gezien.add(dedup_sleutel)

            gewensttijd = rec.get("gewensttijd") or "—"
            mendrix_van = rec.get("mendrix_van", "")
            mendrix_tot = rec.get("mendrix_tot", "")
            mendrix_tv = rec.get("mendrix_tijdvenster", "")
            inplannen_op = (rec.get("inplannen_op") or "").strip()

            bijgewerkt = mendrix_bijgewerkte_tijden.get(order_id) if order_id else None
            nieuw_sleutel = f"new_{naam}_{inplannen_op}"
            is_nieuw = update_res.get(nieuw_sleutel, (False,))[0]

            if bijgewerkt:
                orig = orig_tijden.get(order_id)
                oud_van, oud_tot = orig if orig else (mendrix_van, mendrix_tot)
                tijdinfo = f"{gewensttijd} ⚠️ bijgewerkt (was: {oud_van}-{oud_tot})"
            elif is_nieuw:
                tijdinfo = f"{gewensttijd} ✨ nieuw aangemaakt"
            elif mendrix_tv:
                tijdinfo = f"{gewensttijd} (geen tijdswijziging)"
            else:
                tijdinfo = gewensttijd

            order_str = f"#{order_id}" if order_id else "geen order"
            regels.append(f"• {naam} — {order_str} — {tijdinfo}")

        regels.append("")

    if xlsx_url:
        regels.append(f"📎 Planningsbestand: {xlsx_url}")

    return "\n".join(regels).rstrip()
