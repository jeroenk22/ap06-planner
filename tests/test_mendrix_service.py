"""Tests voor mendrix_service — SOAP-koppeling met Mendrix Custom Link."""

from datetime import date
from html import escape, unescape
from unittest.mock import MagicMock, patch

import pytest

from ap06_planner.services.mendrix_service import (
    _bereken_duur,
    _bouw_soap_envelope,
    _parseer_namen_en_ids,
    _simpele_naam_match,
    _splits_order_xml,
    _vervang_requested_tijden,
    haal_mendrix_namen_en_ids,
    haal_order_ids,
    haal_orders_debug,
    maak_mendrix_dummy_order,
    maak_mendrix_order,
    update_mendrix_tijdvenster,
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
        fout_resp.status_code = 500
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

    def test_maak_sessie_cache_hit(self):
        """Tweede aanroep retourneert exact hetzelfde object (cache hit, line 43)."""
        import ap06_planner.services.mendrix_service as ms
        from ap06_planner.services.mendrix_service import _maak_sessie

        ms._sessie_cache = None  # reset voor isolatie
        s1 = _maak_sessie()
        s2 = _maak_sessie()
        assert s1 is s2

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
        mock_r.status_code = 200
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

    def test_zelfde_achternaam_andere_voornaam_geen_match(self):
        """Bert Coppens mag NIET matchen op Piet Coppens (line 356: voornaam-conflict continue)."""
        kandidaten = ["AP06 - Piet Coppens"]
        assert _simpele_naam_match("Bert Coppens", kandidaten) is None


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


_RESPONSE_XML = """<?xml version="1.0"?>
<EoCustomLinkResponseOrdersNormal Type="TEoCustomLinkResponseOrdersNormal">
  <Data Type="TEoOrderMxList">
    <_TEoListBase_Items>
      <EoOrderMx Type="TEoOrderMx">
        <Tasks Type="TEoTaskMxList">
          <_TEoListBase_Items>
            <EoTaskMx Type="TEoTaskMx">
              <Planned Type="TEoDateTimeWindow">
                <DateTimeEnd>2026-06-10T18:00:00+02:00</DateTimeEnd>
                <DateTimeBegin>2026-06-10T10:00:00+02:00</DateTimeBegin>
              </Planned>
              <Requested Type="TEoDateTimeWindow">
                <DateTimeEnd>2026-06-10T18:00:00+02:00</DateTimeEnd>
                <DateTimeBegin>2026-06-10T10:00:00+02:00</DateTimeBegin>
                <DurationInDateTime>1899-12-30T08:00:00+01:00</DurationInDateTime>
                <DurationInHours>8.0</DurationInHours>
              </Requested>
            </EoTaskMx>
          </_TEoListBase_Items>
        </Tasks>
      </EoOrderMx>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkResponseOrdersNormal>"""


class TestVervangRequestedTijden:
    def test_vervangt_begintijd_en_eindtijd(self):
        result = _vervang_requested_tijden(_RESPONSE_XML, "16:00", "22:30")
        assert "<DateTimeBegin>2026-06-10T16:00:00+02:00</DateTimeBegin>" in result
        assert "<DateTimeEnd>2026-06-10T22:30:00+02:00</DateTimeEnd>" in result

    def test_raakt_planned_niet_aan(self):
        result = _vervang_requested_tijden(_RESPONSE_XML, "16:00", "22:30")
        # Planned block blijft ongewijzigd
        assert "<Planned" in result
        planned_idx = result.index("<Planned")
        requested_idx = result.index("<Requested")
        planned_blok = result[planned_idx:requested_idx]
        assert "T10:00:00" in planned_blok

    def test_behoudt_timezone_offset(self):
        result = _vervang_requested_tijden(_RESPONSE_XML, "16:00", "22:30")
        assert "+02:00</DateTimeBegin>" in result
        assert "+02:00</DateTimeEnd>" in result

    def test_geen_requested_blok_ongewijzigd(self):
        xml = "<Root><Data>geen requested</Data></Root>"
        assert _vervang_requested_tijden(xml, "16:00", "22:30") == xml

    def test_werkt_duur_bij(self):
        # 16:00-22:30 = 6h30m = 6.5 uren
        result = _vervang_requested_tijden(_RESPONSE_XML, "16:00", "22:30")
        assert "<DurationInHours>6.5</DurationInHours>" in result
        assert "<DurationInDateTime>1899-12-30T06:30:00+01:00</DurationInDateTime>" in result

    def test_duur_overmidnacht(self):
        # 22:00-02:00 = 4 uren
        result = _vervang_requested_tijden(_RESPONSE_XML, "22:00", "02:00")
        assert "<DurationInHours>4.0</DurationInHours>" in result
        assert "<DurationInDateTime>1899-12-30T04:00:00+01:00</DurationInDateTime>" in result


class TestBerekenDuur:
    def test_normale_duur(self):
        uren, dt = _bereken_duur("13:00", "23:59")
        assert abs(uren - (10 + 59 / 60)) < 0.001
        assert dt == "1899-12-30T10:59:00+01:00"

    def test_duur_zes_en_half_uur(self):
        uren, dt = _bereken_duur("16:00", "22:30")
        assert uren == 6.5
        assert dt == "1899-12-30T06:30:00+01:00"

    def test_duur_over_middernacht(self):
        uren, dt = _bereken_duur("22:00", "02:00")
        assert uren == 4.0
        assert dt == "1899-12-30T04:00:00+01:00"


class TestUpdateMendrixTijdvenster:
    def _mock_sessie_met_response(self, inner_xml: str) -> MagicMock:
        from html import escape

        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.text = f"<soap><AResult>{escape(inner_xml)}</AResult></soap>"
        sessie = MagicMock()
        sessie.post.return_value = resp
        return sessie

    def test_succes(self):
        store_result = "<EoStoreResultList><EoStoreResult><StoreResult>srUpdated</StoreResult></EoStoreResult></EoStoreResultList>"
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
                side_effect=[
                    self._mock_sessie_met_response(_RESPONSE_XML),
                    self._mock_sessie_met_response(store_result),
                ],
            ),
        ):
            succes, melding = update_mendrix_tijdvenster(1001, "16:00", "22:30")
        assert succes is True
        assert "1001" in melding
        assert "16:00" in melding

    def test_fout_response(self):
        fout_result = "<EoStoreResultList><EoStoreResult><StoreResult>srError</StoreResult><ErrorMessage>Ongeldige data</ErrorMessage></EoStoreResult></EoStoreResultList>"
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
                side_effect=[
                    self._mock_sessie_met_response(_RESPONSE_XML),
                    self._mock_sessie_met_response(fout_result),
                ],
            ),
        ):
            succes, melding = update_mendrix_tijdvenster(1001, "16:00", "22:30")
        assert succes is False
        assert "Ongeldige data" in melding

    def test_exception_wordt_afgevangen(self):
        with patch(
            "ap06_planner.services.mendrix_service._haal_orders_xml",
            side_effect=Exception("verbinding verbroken"),
        ):
            succes, melding = update_mendrix_tijdvenster(1001, "16:00", "22:30")
        assert succes is False
        assert "verbinding verbroken" in melding

    def test_lege_xml_response(self):
        with patch(
            "ap06_planner.services.mendrix_service._haal_orders_xml",
            return_value="",
        ):
            succes, melding = update_mendrix_tijdvenster(1001, "16:00", "22:30")
        assert succes is False
        assert "geen" in melding.lower()

    def test_cached_xml_slaat_fetch_over(self):
        """Met cached_xml wordt _haal_orders_xml niet aangeroepen."""
        store_result = "<EoStoreResultList><EoStoreResult><StoreResult>srUpdated</StoreResult></EoStoreResult></EoStoreResultList>"
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
                "ap06_planner.services.mendrix_service._haal_orders_xml"
            ) as mock_fetch,
            patch(
                "ap06_planner.services.mendrix_service._maak_sessie",
                return_value=self._mock_sessie_met_response(store_result),
            ),
        ):
            succes, _ = update_mendrix_tijdvenster(1001, "16:00", "22:30", cached_xml=_RESPONSE_XML)
        assert succes is True
        mock_fetch.assert_not_called()


class TestHaalMendrixNamenIdsEnXml:
    def test_lege_order_ids_geeft_lege_dicts(self):
        from ap06_planner.services.mendrix_service import haal_mendrix_namen_ids_en_xml

        with patch(
            "ap06_planner.services.mendrix_service.haal_order_ids",
            return_value=[],
        ):
            namen_ids, order_xml = haal_mendrix_namen_ids_en_xml(date(2026, 6, 10))
        assert namen_ids == {}
        assert order_xml == {}

    def test_retourneert_namen_ids_en_xml(self):
        from ap06_planner.services.mendrix_service import haal_mendrix_namen_ids_en_xml

        with (
            patch(
                "ap06_planner.services.mendrix_service.haal_order_ids",
                return_value=[42],
            ),
            patch(
                "ap06_planner.services.mendrix_service._haal_orders_xml",
                return_value="""<EoCustomLinkResponseOrdersNormal>
  <EoOrderMx><OrderId Type="x"><Id>42</Id></OrderId>
    <Tasks><_TEoListBase_Items><EoTaskMx>
      <Requested><DateTimeBegin>2026-06-10T10:00:00+02:00</DateTimeBegin>
      <DateTimeEnd>2026-06-10T18:00:00+02:00</DateTimeEnd></Requested>
      <Address><Name>Test Persoon</Name></Address>
    </EoTaskMx></_TEoListBase_Items></Tasks>
  </EoOrderMx>
</EoCustomLinkResponseOrdersNormal>""",
            ),
        ):
            namen_ids, order_xml = haal_mendrix_namen_ids_en_xml(date(2026, 6, 10))
        assert 42 in order_xml
        assert "EoCustomLinkResponseOrdersNormal" in order_xml[42]


class TestSplitsOrderXml:
    def test_splits_per_order_id(self):
        result = _splits_order_xml(_RESPONSE_XML)
        # _RESPONSE_XML heeft één order zonder OrderId in de verwachte structuur —
        # voeg een variant toe met OrderId
        xml = """<EoCustomLinkResponseOrdersNormal Type="TEoCustomLinkResponseOrdersNormal">
  <EoOrderMx><OrderId Type="x"><Id>42</Id></OrderId><Name>Test</Name></EoOrderMx>
  <EoOrderMx><OrderId Type="x"><Id>99</Id></OrderId><Name>Ander</Name></EoOrderMx>
</EoCustomLinkResponseOrdersNormal>"""
        result = _splits_order_xml(xml)
        assert 42 in result
        assert 99 in result
        assert "EoCustomLinkResponseOrdersNormal" in result[42]
        assert "<Id>42</Id>" in result[42]
        assert "<Id>99</Id>" not in result[42]

    def test_lege_xml_geeft_leeg_dict(self):
        assert _splits_order_xml("<Root/>") == {}

    def test_behoudt_wrapper_tag(self):
        xml = """<EoCustomLinkResponseOrdersNormal Type="TEoCustomLinkResponseOrdersNormal">
  <EoOrderMx><OrderId Type="x"><Id>7</Id></OrderId></EoOrderMx>
</EoCustomLinkResponseOrdersNormal>"""
        result = _splits_order_xml(xml)
        assert 'Type="TEoCustomLinkResponseOrdersNormal"' in result[7]


_INSERTED_XML = """<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>9876</Id>
 <IdOld>-1000</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreResult>srInserted</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>"""

_MAAK_KWARGS = {
    "naam": "Johan van Zoggel",
    "adres": "Sparrenlaan 5",
    "postcode": "5491 TC",
    "woonplaats": "Sint-Oedenrode",
    "telefoon": "06-12345678",
    "bijzonderheden": "Bel van tevoren",
    "laadinstructie": "Monsters liggen in de schuur",
    "uiterlijke_plantijd": "22:00",
    "algemene_instructie_ap06": "Papieren invullen",
    "ophaaldagen": ["ma", "do"],
    "inplan_datum": date(2026, 6, 11),
    "gewensttijd_begin": "10:00",
    "gewensttijd_eind": "23:59",
}


class TestMaakMendrixOrder:
    def _mock(self, inner_xml: str) -> MagicMock:
        resp = _mock_resp(inner_xml)
        return _mock_sessie(resp)

    def test_succes_retourneert_nieuw_order_id(self):
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=self._mock(_INSERTED_XML)),
        ):
            succes, melding = maak_mendrix_order(**_MAAK_KWARGS)
        assert succes is True
        assert "9876" in melding

    def test_fout_response_retourneert_false(self):
        fout_xml = "<EoStoreResultList><EoStoreResult><StoreResult>srError</StoreResult><StoreDescription>Ongeldig veld</StoreDescription></EoStoreResult></EoStoreResultList>"
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=self._mock(fout_xml)),
        ):
            succes, melding = maak_mendrix_order(**_MAAK_KWARGS)
        assert succes is False
        assert "Ongeldig veld" in melding

    def test_xml_bevat_naam_met_prefix(self):
        mock_s = self._mock(_INSERTED_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_order(**_MAAK_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "AP06/ONAFH - Johan van Zoggel" in xml

    def test_xml_bevat_tijdvenster(self):
        mock_s = self._mock(_INSERTED_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_order(**_MAAK_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "2026-06-11T10:00:00" in xml
        assert "2026-06-11T23:59:00" in xml

    def test_xml_bevat_uiterlijke_plantijd_in_instructies(self):
        mock_s = self._mock(_INSERTED_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_order(**_MAAK_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "Ophalen vóór 22:00!" in xml

    def test_exception_retourneert_false(self):
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", side_effect=Exception("timeout")),
        ):
            succes, melding = maak_mendrix_order(**_MAAK_KWARGS)
        assert succes is False
        assert "timeout" in melding


_INSERTED_DUMMY_XML = """<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>5555</Id>
 <IdOld>-1001</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreResult>srInserted</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>"""

_DUMMY_KWARGS = {
    "naam": "Johan van Zoggel",
    "adres": "Sparrenlaan 5",
    "postcode": "5491 TC",
    "woonplaats": "Sint-Oedenrode",
    "telefoon": "06-12345678",
    "bijzonderheden": "Bel van tevoren",
    "inplan_datum": date(2026, 6, 11),
    "gewensttijd_begin": "10:00",
    "gewensttijd_eind": "23:59",
    "aantal_lege_bakken": 3,
    "ophaaldagen": ["di", "do"],
}


class TestMaakMendrixDummyOrder:
    def _mock(self, inner_xml: str) -> MagicMock:
        resp = _mock_resp(inner_xml)
        return _mock_sessie(resp)

    def test_succes_retourneert_nieuw_order_id(self):
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=self._mock(_INSERTED_DUMMY_XML)),
        ):
            succes, melding = maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        assert succes is True
        assert "5555" in melding

    def test_xml_bevat_client_3699(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "<Id>3699</Id>" in xml

    def test_xml_bevat_product_60(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "<Id>60</Id>" in xml

    def test_xml_bevat_tasktype_2(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "<Id>2</Id>" in xml  # TaskTypeId

    def test_xml_bevat_packing_naam(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "Lichtgrijze mestbak met blauw deksel" in xml

    def test_notes_diversen_bevat_ophaaldagen(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "AP06 - Ophaaldagen Johan: di-do (order automatisch ingeschoten)" in xml

    def test_instructies_meervoud_bij_meer_dan_een(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**{**_DUMMY_KWARGS, "aantal_lege_bakken": 3})
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "3 Lichtgrijze mestbakken met blauw deksel en AP06 sleutel meenemen!" in xml

    def test_instructies_enkelvoud_bij_een(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**{**_DUMMY_KWARGS, "aantal_lege_bakken": 1})
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "1 Lichtgrijze mestbak met blauw deksel en AP06 sleutel meenemen!" in xml

    def test_xml_bevat_aantal_als_amount(self):
        mock_s = self._mock(_INSERTED_DUMMY_XML)
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=mock_s),
        ):
            maak_mendrix_dummy_order(**{**_DUMMY_KWARGS, "aantal_lege_bakken": 4})
        _, kwargs = mock_s.post.call_args
        xml = unescape(kwargs["data"].decode())
        assert "<Amount>4</Amount>" in xml

    def test_fout_response_retourneert_false(self):
        fout_xml = "<EoStoreResultList><EoStoreResult><StoreResult>srError</StoreResult><StoreDescription>Ongeldig veld</StoreDescription></EoStoreResult></EoStoreResultList>"
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", return_value=self._mock(fout_xml)),
        ):
            succes, melding = maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        assert succes is False
        assert "Ongeldig veld" in melding

    def test_exception_retourneert_false(self):
        with (
            patch.dict("os.environ", {"MENDRIX_SOAP_URL": "https://test.nl/soap", "MENDRIX_SOAP_USER": "u", "MENDRIX_SOAP_PASS": "p"}),
            patch("ap06_planner.services.mendrix_service._maak_sessie", side_effect=Exception("verbinding verbroken")),
        ):
            succes, melding = maak_mendrix_dummy_order(**_DUMMY_KWARGS)
        assert succes is False
        assert "verbinding verbroken" in melding
