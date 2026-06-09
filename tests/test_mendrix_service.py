"""Tests voor mendrix_service — SOAP-koppeling met Mendrix Custom Link."""

from datetime import date
from html import escape, unescape
from unittest.mock import MagicMock, patch

import pytest

from ap06_planner.services.mendrix_service import (
    _bouw_soap_envelope,
    _parseer_namen_en_ids,
    _simpele_naam_match,
    haal_mendrix_namen_en_ids,
    haal_order_ids,
    haal_orders_debug,
    werkdagen_van_week,
    zoek_mendrix_order,
)


def _soap_response(inner_xml: str) -> str:
    """Wikkel inner XML in een SOAP-response zoals Mendrix die stuurt."""
    return f"""<?xml version="1.0"?>
<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <ExecuteRequestResponse>
      <AResult>{escape(inner_xml)}</AResult>
    </ExecuteRequestResponse>
  </soap-env:Body>
</soap-env:Envelope>"""


def _mock_resp(inner_xml: str, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = _soap_response(inner_xml)
    r.raise_for_status = MagicMock()
    return r


def _mock_sessie(resp: MagicMock) -> MagicMock:
    """Geeft een nep-sessie terug waarvan .post() de gegeven resp retourneert."""
    sessie = MagicMock()
    sessie.post.return_value = resp
    return sessie


class TestBouwSoapEnvelope:
    def test_bevat_username(self):
        with patch.dict(
            "os.environ", {"MENDRIX_SOAP_USER": "testuser", "MENDRIX_SOAP_PASS": "testpass"}
        ):
            env = _bouw_soap_envelope("<Test/>")
        assert "testuser" in env

    def test_bevat_inner_xml_escaped(self):
        with patch.dict("os.environ", {"MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}):
            env = _bouw_soap_envelope("<Root><Child>val</Child></Root>")
        assert "&lt;Root&gt;" in env

    def test_bevat_soap_action_urn(self):
        with patch.dict("os.environ", {"MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}):
            env = _bouw_soap_envelope("<X/>")
        assert "ExecuteRequest" in env
        assert "UCoSoapDispatcherCustomLink" in env


class TestHaalOrderIds:
    def test_succes(self):
        ids_xml = """<?xml version="1.0"?>
<EoCustomLinkResponseOrdersNormalIds Type="TEoCustomLinkResponseOrdersNormalIds">
<Data Type="TEoKeyIntList">
  <SequenceMaximum>7086</SequenceMaximum>
  <_TEoListBase_Items>
    <EoKeyInt Type="TEoKeyInt"><Id>349</Id></EoKeyInt>
    <EoKeyInt Type="TEoKeyInt"><Id>371</Id></EoKeyInt>
  </_TEoListBase_Items>
</Data>
</EoCustomLinkResponseOrdersNormalIds>"""
        resp = _mock_resp(ids_xml)
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=_mock_sessie(resp),
            ),
        ):
            result = haal_order_ids(date(2026, 4, 13))
        assert result == [349, 371]

    def test_geen_orders(self):
        leeg_xml = """<EoCustomLinkResponseOrdersNormalIds Type="TEoCustomLinkResponseOrdersNormalIds">
<Data Type="TEoKeyIntList"><_TEoListBase_Items/></Data>
</EoCustomLinkResponseOrdersNormalIds>"""
        resp = _mock_resp(leeg_xml)
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=_mock_sessie(resp),
            ),
        ):
            result = haal_order_ids(date(2026, 4, 13))
        assert result == []

    def test_geen_url_raises(self):
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": ""}),
            pytest.raises(ValueError, match="MENDRIX_SOAP_URL"),
        ):
            haal_order_ids(date(2026, 4, 13))

    def test_http_fout(self):
        fout_resp = MagicMock()
        fout_resp.raise_for_status.side_effect = Exception("HTTP 500")
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=_mock_sessie(fout_resp),
            ),
            pytest.raises(Exception, match="HTTP 500"),
        ):
            haal_order_ids(date(2026, 4, 13))

    def test_soap_action_header_correct(self):
        ids_xml = "<EoCustomLinkResponseOrdersNormalIds><Data><_TEoListBase_Items/></Data></EoCustomLinkResponseOrdersNormalIds>"
        resp = _mock_resp(ids_xml)
        mock_s = _mock_sessie(resp)
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            haal_order_ids(date(2026, 4, 13))
        _, kwargs = mock_s.post.call_args
        assert "SOAPAction" in kwargs["headers"]
        assert "ExecuteRequest" in kwargs["headers"]["SOAPAction"]


class TestHaalOrdersDebug:
    def test_lege_ids_geeft_leeg(self):
        result = haal_orders_debug([])
        assert result == ""

    def test_succes(self):
        order_xml = (
            "<EoCustomLinkResponseOrdersNormal><Data>...</Data></EoCustomLinkResponseOrdersNormal>"
        )
        resp = _mock_resp(order_xml)
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=_mock_sessie(resp),
            ),
        ):
            result = haal_orders_debug([349, 371, 391])
        assert "EoCustomLinkResponseOrdersNormal" in result

    def test_max_orders_begrensd(self):
        order_xml = "<EoCustomLinkResponseOrdersNormal/>"
        resp = _mock_resp(order_xml)
        mock_s = _mock_sessie(resp)
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            haal_orders_debug([1, 2, 3, 4, 5, 6, 7], max_orders=3)
        _, kwargs = mock_s.post.call_args
        envelope = kwargs["data"].decode()
        assert unescape(envelope).count(",") <= 2  # 3 IDs = 2 komma's


_ORDER_XML = """<?xml version="1.0"?>
<EoCustomLinkResponseOrdersNormal Type="TEoCustomLinkResponseOrdersNormal">
<Data Type="TEoOrderMxList">
<_TEoListBase_Items>
<EoOrderMx Type="TEoOrderMx">
<OrderId Type="TEoKeyIntInfraMx">
 <Id>1001</Id>
</OrderId>
<Requested>
  <DateTimeBegin>2026-06-10T13:00:00</DateTimeBegin>
  <DateTimeEnd>2026-06-10T17:00:00</DateTimeEnd>
</Requested>
<Tasks Type="TEoTaskMxList">
<_TEoListBase_Items>
<EoTaskMx Type="TEoTaskMx">
<Address Type="TEoAddress">
 <Name>AP06/ONAFH - Kathleen Bouvier</Name>
</Address>
</EoTaskMx>
</_TEoListBase_Items>
</Tasks>
</EoOrderMx>
<EoOrderMx Type="TEoOrderMx">
<OrderId Type="TEoKeyIntInfraMx">
 <Id>1002</Id>
</OrderId>
<Tasks Type="TEoTaskMxList">
<_TEoListBase_Items>
<EoTaskMx Type="TEoTaskMx">
<Address Type="TEoAddress">
 <Name>AP06 - Susan Curma</Name>
</Address>
</EoTaskMx>
</_TEoListBase_Items>
</Tasks>
</EoOrderMx>
</_TEoListBase_Items>
</Data>
</EoCustomLinkResponseOrdersNormal>"""


class TestParseerNamenEnIds:
    def test_parseert_twee_orders(self):
        resultaat = _parseer_namen_en_ids(_ORDER_XML)
        assert resultaat["AP06/ONAFH - Kathleen Bouvier"] == {
            "order_id": 1001,
            "van": "13:00",
            "tot": "17:00",
        }
        assert resultaat["AP06 - Susan Curma"] == {"order_id": 1002, "van": None, "tot": None}

    def test_leeg_xml(self):
        assert _parseer_namen_en_ids("") == {}

    def test_geen_naam(self):
        xml = """<EoOrderMx><OrderId><Id>99</Id></OrderId>
<Tasks><_TEoListBase_Items><EoTaskMx>
<Address><Name></Name></Address>
</EoTaskMx></_TEoListBase_Items></Tasks></EoOrderMx>"""
        assert _parseer_namen_en_ids(xml) == {}


class TestHaalMendrixNamenEnIds:
    def test_succes(self):
        resp = _mock_resp(_ORDER_XML)
        ids_resp = _mock_resp("""<EoCustomLinkResponseOrdersNormalIds>
<Data><_TEoListBase_Items>
<EoKeyInt><Id>1001</Id></EoKeyInt>
<EoKeyInt><Id>1002</Id></EoKeyInt>
</_TEoListBase_Items></Data></EoCustomLinkResponseOrdersNormalIds>""")
        mock_s_ids = _mock_sessie(ids_resp)
        mock_s_orders = _mock_sessie(resp)

        call_count = 0

        def sessie_factory():
            nonlocal call_count
            call_count += 1
            return mock_s_ids if call_count == 1 else mock_s_orders

        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch("ap06_planner.services.mendrix_service._maak_sessie", side_effect=sessie_factory),
        ):
            resultaat = haal_mendrix_namen_en_ids(date(2026, 6, 5))

        assert "AP06/ONAFH - Kathleen Bouvier" in resultaat
        assert resultaat["AP06/ONAFH - Kathleen Bouvier"]["order_id"] == 1001

    def test_geen_orders(self):
        leeg = "<EoCustomLinkResponseOrdersNormalIds><Data><_TEoListBase_Items/></Data></EoCustomLinkResponseOrdersNormalIds>"
        resp = _mock_resp(leeg)
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=_mock_sessie(resp),
            ),
        ):
            assert haal_mendrix_namen_en_ids(date(2026, 6, 5)) == {}


class TestWerkdagenVanWeek:
    def test_vrijdag_geeft_ma_tm_vr(self):
        # vrijdag 06-06-2026 → week 23 → ma 01-06 t/m vr 05-06 (ISO week begint op ma)
        # Eigenlijk: vrijdag 06-06-2026 zit in week 23 → ma 02-06 t/m vr 06-06
        result = werkdagen_van_week(date(2026, 6, 6))
        assert len(result) == 5
        assert result[0].weekday() == 0  # maandag
        assert result[4].weekday() == 4  # vrijdag
        assert result[0] == date(2026, 6, 1)
        assert result[4] == date(2026, 6, 5)

    def test_maandag_geeft_zelfde_week(self):
        result = werkdagen_van_week(date(2026, 6, 8))  # maandag
        assert result[0] == date(2026, 6, 8)
        assert result[4] == date(2026, 6, 12)

    def test_altijd_5_dagen(self):
        for dag in [date(2026, 6, d) for d in range(1, 8)]:
            assert len(werkdagen_van_week(dag)) == 5


class TestSslAdapter:
    def test_maak_sessie_geeft_session(self):
        import requests as req

        from ap06_planner.services.mendrix_service import _maak_sessie

        s = _maak_sessie()
        assert isinstance(s, req.Session)

    def test_legacy_adapter_init_poolmanager(self):
        from ap06_planner.services.mendrix_service import _LegacySslAdapter

        adapter = _LegacySslAdapter()
        with patch.object(adapter.__class__.__bases__[0], "init_poolmanager"):
            # Aanroepen mag niet crashen
            adapter.init_poolmanager(10, maxsize=10)


class TestSoapRequestFallback:
    def test_geen_resultaat_tag_geeft_raw_text(self):
        """Als geen AResult/return/ExecuteRequestResult tag aanwezig → raw response terug."""
        raw = "<OnbekendElement>data</OnbekendElement>"
        mock_r = MagicMock()
        mock_r.raise_for_status = MagicMock()
        mock_r.text = raw
        with (
            patch.dict(
                "os.environ",
                {
                    "MENDRIX_SOAP_URL": "https://test.nl/soap",
                    "MENDRIX_SOAP_USER": "u",
                    "MENDRIX_SOAP_PASS": "p",
                },
            ),
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=_mock_sessie(mock_r),
            ),
        ):
            # haal_order_ids geeft lege lijst terug want <Id> staat er niet in
            result = haal_order_ids(date(2026, 6, 5))
        assert result == []


class TestSimpeleNaamMatch:
    def test_match_met_prefix(self):
        kandidaten = ["AP06/ONAFH - Kathleen Bouvier", "AP06 - Susan Curma"]
        assert (
            _simpele_naam_match("Kathleen Bouvier", kandidaten) == "AP06/ONAFH - Kathleen Bouvier"
        )

    def test_match_zonder_prefix(self):
        kandidaten = ["Kathleen Bouvier", "Susan Curma"]
        assert _simpele_naam_match("Kathleen Bouvier", kandidaten) == "Kathleen Bouvier"

    def test_geen_match(self):
        kandidaten = ["AP06 - Jan Jansen"]
        assert _simpele_naam_match("Piet Pietersen", kandidaten) is None

    def test_omgekeerde_naamvolgorde_geen_match(self):
        # "Bouvier K" heeft achternaam als eerste woord — geen match, gaat naar AI-fallback
        kandidaten = ["AP06 - Bouvier K"]
        assert _simpele_naam_match("Kathleen Bouvier", kandidaten) is None

    def test_gedeelde_voornaam_geen_false_positive(self):
        # "Johan van Zoggel" mag NIET matchen op "Johan van Gool" (andere achternaam)
        kandidaten = ["AP06/ONAFH - Johan van Gool"]
        assert _simpele_naam_match("Johan van Zoggel", kandidaten) is None

    def test_zelfde_achternaam_matcht(self):
        kandidaten = ["AP06/ONAFH - Johan van Gool"]
        assert _simpele_naam_match("Johan van Gool", kandidaten) == "AP06/ONAFH - Johan van Gool"

    def test_lege_naam_in_kandidaten_wordt_overgeslagen(self):
        # Kandidaat met lege kern na split op " - " → wordt overgeslagen
        kandidaten = ["AP06 - ", "AP06 - Susan Curma"]
        resultaat = _simpele_naam_match("Susan Curma", kandidaten)
        assert resultaat == "AP06 - Susan Curma"


_INFO_1001 = {"order_id": 1001, "van": "13:00", "tot": "17:00"}
_INFO_2002 = {"order_id": 2002, "van": None, "tot": None}
_INFO_999 = {"order_id": 999, "van": None, "tot": None}


class TestZoekMendrixOrder:
    def test_gevonden_via_simpele_match(self):
        mendrix = {"AP06/ONAFH - Kathleen Bouvier": _INFO_1001}
        order_id, naam = zoek_mendrix_order("Kathleen Bouvier", mendrix)
        assert order_id == 1001
        assert naam == "AP06/ONAFH - Kathleen Bouvier"

    def test_niet_gevonden_zonder_ai(self):
        mendrix = {"AP06 - Jan Jansen": _INFO_999}
        with patch("ap06_planner.services.claude_service.match_naam_mendrix", return_value=None):
            order_id, naam = zoek_mendrix_order("Piet Pietersen", mendrix)
        assert order_id is None
        assert naam is None

    def test_gevonden_via_ai_fallback(self):
        # "PDW" (initialen) heeft geen woord-overlap → simpele match faalt → AI-fallback
        mendrix = {"AP06/ONAFH - Petra de Wit": _INFO_2002}
        with patch(
            "ap06_planner.services.claude_service.match_naam_mendrix",
            return_value="AP06/ONAFH - Petra de Wit",
        ):
            order_id, naam = zoek_mendrix_order("PDW", mendrix)
        assert order_id == 2002
        assert naam == "AP06/ONAFH - Petra de Wit"

    def test_lege_dict(self):
        assert zoek_mendrix_order("Kathleen Bouvier", {}) == (None, None)

    def test_ai_fallback_exception_wordt_genegeerd(self):
        mendrix = {"AP06/ONAFH - Petra de Wit": _INFO_2002}
        with patch(
            "ap06_planner.services.claude_service.match_naam_mendrix",
            side_effect=Exception("API fout"),
        ):
            order_id, naam = zoek_mendrix_order("PDW", mendrix)
        assert order_id is None
        assert naam is None
