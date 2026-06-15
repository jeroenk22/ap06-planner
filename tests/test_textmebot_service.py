"""Tests voor textmebot_service.py."""

from unittest.mock import MagicMock, patch

from ap06_planner.services.textmebot_service import (
    bereken_alle_groen,
    bouw_whatsapp_bericht,
    stuur_whatsapp,
)

# ---------------------------------------------------------------------------
# stuur_whatsapp
# ---------------------------------------------------------------------------


def test_stuur_whatsapp_geen_config(monkeypatch):
    monkeypatch.delenv("TEXTMEBOT_API_KEY", raising=False)
    monkeypatch.delenv("TEXTMEBOT_ONTVANGER", raising=False)
    succes, melding = stuur_whatsapp("test")
    assert not succes
    assert "niet ingesteld" in melding


def test_stuur_whatsapp_succes(monkeypatch):
    monkeypatch.setenv("TEXTMEBOT_API_KEY", "key123")
    monkeypatch.setenv("TEXTMEBOT_ONTVANGER", "+31612345678")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Message queued"
    with patch("ap06_planner.services.textmebot_service.requests.get", return_value=mock_resp):
        succes, melding = stuur_whatsapp("Hallo!")
    assert succes
    assert melding == "Message queued"


def test_stuur_whatsapp_request_fout(monkeypatch):
    import requests as req_mod

    monkeypatch.setenv("TEXTMEBOT_API_KEY", "key123")
    monkeypatch.setenv("TEXTMEBOT_ONTVANGER", "+31612345678")
    with patch(
        "ap06_planner.services.textmebot_service.requests.get",
        side_effect=req_mod.RequestException("timeout"),
    ):
        succes, melding = stuur_whatsapp("Hallo!")
    assert not succes
    # Foutmelding mag geen URL met API-key bevatten
    assert "key123" not in melding
    assert "mislukt" in melding


# ---------------------------------------------------------------------------
# bereken_alle_groen
# ---------------------------------------------------------------------------


def _kleur_fn(pb, mv, pe="", mt=""):
    """Vereenvoudigde kleur-functie voor tests: geel als begin >= 30 min afwijkt."""
    try:
        ph, pm = int(pb[:2]), int(pb[3:5])
        mh, mm = int(mv[:2]), int(mv[3:5])
        return "geel" if abs(ph * 60 + pm - (mh * 60 + mm)) >= 30 else "groen"
    except (ValueError, IndexError):
        return "groen"


def _rec(order_id=1, gewensttijd="08:00 - 12:00", mendrix_van="08:00", mendrix_tot="12:00"):
    return {
        "naam_monsternemer": "Test",
        "inplannen_op": "Maandag 16-06-2026",
        "mendrix_order_id": order_id,
        "mendrix_van": mendrix_van,
        "mendrix_tot": mendrix_tot,
        "mendrix_tijdvenster": f"{mendrix_van}-{mendrix_tot}" if mendrix_van else "",
        "gewensttijd": gewensttijd,
    }


def test_bereken_alle_groen_leeg():
    assert bereken_alle_groen([], {}, {}, _kleur_fn)


def test_bereken_alle_groen_geen_mendrix_order_id():
    rec = {"naam_monsternemer": "Test"}  # geen 'mendrix_order_id' key
    assert not bereken_alle_groen([rec], {}, {}, _kleur_fn)


def test_bereken_alle_groen_order_id_none():
    rec = _rec(order_id=None)
    assert not bereken_alle_groen([rec], {}, {}, _kleur_fn)


def test_bereken_alle_groen_tijden_kloppen():
    rec = _rec(order_id=10, gewensttijd="08:00 - 12:00", mendrix_van="08:00", mendrix_tot="12:00")
    assert bereken_alle_groen([rec], {}, {}, _kleur_fn)


def test_bereken_alle_groen_geel_niet_bijgewerkt():
    rec = _rec(order_id=10, gewensttijd="09:00 - 13:00", mendrix_van="08:00", mendrix_tot="12:00")
    assert not bereken_alle_groen([rec], {}, {}, _kleur_fn)


def test_bereken_alle_groen_geel_wel_bijgewerkt():
    rec = _rec(order_id=10, gewensttijd="09:00 - 13:00", mendrix_van="08:00", mendrix_tot="12:00")
    update_res = {"upd_10": (True, "bijgewerkt")}
    assert bereken_alle_groen([rec], {}, update_res, _kleur_fn)


def test_bereken_alle_groen_geel_bijgew_tijden():
    # Als mendrix_bijgewerkte_tijden al de nieuwe tijd bevat, hoeft update_res niet
    rec = _rec(order_id=10, gewensttijd="09:00 - 13:00", mendrix_van="09:00", mendrix_tot="13:00")
    # Na bijwerken staat de nieuwe tijd in bijgewerkte_tijden
    bijgew = {10: ("09:00", "13:00")}
    assert bereken_alle_groen([rec], bijgew, {}, _kleur_fn)


# ---------------------------------------------------------------------------
# bouw_whatsapp_bericht
# ---------------------------------------------------------------------------


def _planning_rec(
    naam="Jan Jansen",
    order_id=42,
    gewensttijd="08:00 - 12:00",
    mendrix_van="08:00",
    mendrix_tot="12:00",
    inplan="Maandag 16-06-2026",
):
    return {
        "naam_monsternemer": naam,
        "inplannen_op": inplan,
        "mendrix_order_id": order_id,
        "mendrix_van": mendrix_van,
        "mendrix_tot": mendrix_tot,
        "mendrix_tijdvenster": f"{mendrix_van}-{mendrix_tot}",
        "gewensttijd": gewensttijd,
    }


def test_bouw_bericht_geen_wijziging():
    rec = _planning_rec()
    bericht = bouw_whatsapp_bericht([rec], {}, "planning_week24.xlsx")
    assert "*planning_week24.xlsx*" in bericht  # extensie behouden + vet
    assert "Jan Jansen" in bericht
    assert "#42" in bericht
    assert "08:00 - 12:00" in bericht
    assert "geen tijdswijziging" in bericht


def test_bouw_bericht_met_bijwerking():
    rec = _planning_rec(gewensttijd="09:00 - 13:00", mendrix_van="08:00", mendrix_tot="12:00")
    bijgew = {42: ("09:00", "13:00")}
    bericht = bouw_whatsapp_bericht([rec], bijgew, "week24.xlsx")
    assert "bijgewerkt" in bericht
    assert "08:00-12:00" in bericht  # oude tijd


def test_bouw_bericht_geen_mendrix_tijdvenster():
    rec = _planning_rec()
    rec["mendrix_tijdvenster"] = ""
    rec["mendrix_van"] = ""
    rec["mendrix_tot"] = ""
    bericht = bouw_whatsapp_bericht([rec], {}, "week24.xlsx")
    assert "08:00 - 12:00" in bericht
    assert "geen tijdswijziging" not in bericht


def test_bouw_bericht_chronologische_volgorde():
    rec_a = _planning_rec(naam="Arie", inplan="Woensdag 18-06-2026")
    rec_b = _planning_rec(naam="Bert", inplan="Maandag 16-06-2026")
    bericht = bouw_whatsapp_bericht([rec_a, rec_b], {}, "w.xlsx")
    pos_ma = bericht.index("16-06-2026")
    pos_wo = bericht.index("18-06-2026")
    assert pos_ma < pos_wo


def test_bouw_bericht_vermeldt_bestandsnaam():
    rec = _planning_rec()
    bericht = bouw_whatsapp_bericht([rec], {}, "AP06 planning week 25.xlsx")
    assert "*AP06 planning week 25.xlsx*" in bericht  # inclusief extensie en vet


def test_bouw_bericht_met_xlsx_url():
    rec = _planning_rec()
    url = "https://drive.google.com/file/d/abc123/view"
    bericht = bouw_whatsapp_bericht([rec], {}, "week24.xlsx", xlsx_url=url)
    assert url in bericht
    assert "📎" in bericht


def test_bouw_bericht_zonder_xlsx_url():
    rec = _planning_rec()
    bericht = bouw_whatsapp_bericht([rec], {}, "week24.xlsx")
    assert "drive.google.com" not in bericht


def test_bouw_bericht_dedupliceert_zelfde_naam_en_order():
    rec1 = _planning_rec(naam="Jop G", order_id=99)
    rec2 = _planning_rec(naam="Jop G", order_id=99)
    bericht = bouw_whatsapp_bericht([rec1, rec2], {}, "w.xlsx")
    assert bericht.count("Jop G") == 1


def test_bouw_bericht_bijgewerkt_toont_originele_tijd():
    rec = _planning_rec(
        order_id=10, gewensttijd="17:45 - 23:59", mendrix_van="17:45", mendrix_tot="23:59"
    )  # al ververst in Mendrix
    bijgew = {10: ("17:45", "23:59")}
    orig = {10: ("13:00", "20:14")}  # opgeslagen vóór de refresh
    bericht = bouw_whatsapp_bericht([rec], bijgew, "w.xlsx", mendrix_originele_tijden=orig)
    assert "13:00-20:14" in bericht  # originele tijd, niet de vernieuwde
    assert "17:45-23:59" not in bericht.split("was:")[1]  # "was" toont niet de nieuwe tijd


def test_bouw_bericht_bijgewerkt_fallback_zonder_originele_tijd():
    rec = _planning_rec(
        order_id=10, gewensttijd="17:45 - 23:59", mendrix_van="13:00", mendrix_tot="20:14"
    )
    bijgew = {10: ("17:45", "23:59")}
    bericht = bouw_whatsapp_bericht([rec], bijgew, "w.xlsx")  # geen orig_tijden
    assert "13:00-20:14" in bericht  # valt terug op mendrix_van/tot uit rec


def test_bouw_bericht_nieuw_aangemaakt():
    rec = _planning_rec(naam="Daniëlle van Gemert", order_id=1241873, inplan="Vrijdag 19-06-2026")
    rec["mendrix_tijdvenster"] = ""
    rec["mendrix_van"] = ""
    rec["mendrix_tot"] = ""
    update_res = {"new_Daniëlle van Gemert_Vrijdag 19-06-2026": (True, "Order aangemaakt")}
    bericht = bouw_whatsapp_bericht([rec], {}, "w.xlsx", mendrix_update_resultaten=update_res)
    assert "nieuw aangemaakt" in bericht
    assert "✨" in bericht
