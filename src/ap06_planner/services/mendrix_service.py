"""
mendrix_service.py — Raadpleeg Mendrix Custom Link via SOAP om bestaande orders op te zoeken.

Flow:
  1. haal_order_ids(datum) → lijst van order-IDs voor ClientNo 3551 op die dag
  2. haal_orders_debug(order_ids) → ruwe XML-response van de eerste orders (voor veldinspectie)
"""

import os
import re
import ssl
from datetime import date, timedelta
from html import escape, unescape
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class _LegacySslAdapter(HTTPAdapter):
    """
    Adapter voor de Mendrix SOAP-server die verouderde cipher suites gebruikt.
    SECLEVEL=1 lost de cipher-mismatch op; TLS 1.2 minimum blijft gehandhaafd.
    Wordt uitsluitend gemount op het Mendrix-endpoint, niet globaal.
    """

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


def _maak_sessie() -> requests.Session:
    s = requests.Session()
    url = os.getenv("MENDRIX_SOAP_URL", "")
    parsed = urlparse(url)
    # Mount alleen op het Mendrix-host, niet op alle https://-verbindingen
    prefix = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "https://"
    s.mount(prefix, _LegacySslAdapter())
    return s

_MENDRIX_CLIENT_NO = 3551
_SOAP_ACTION = '"urn:UCoSoapDispatcherCustomLink-ICustomLinkSoap#ExecuteRequest"'


def _bouw_soap_envelope(inner_xml: str) -> str:
    user = os.getenv("MENDRIX_SOAP_USER", "")
    password = os.getenv("MENDRIX_SOAP_PASS", "")
    return f"""<?xml version="1.0"?>
<soap-env:Envelope
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:urn="urn:UCoSoapDispatcherCustomLink-ICustomLinkSoap">
    <soap-env:Header xmlns:NS-1="urn:UCoSoapDispatcherBase">
        <NS-1:TAuthenticationHeader xsi:type="urn:TAuthenticationHeader"
            xmlns:urn="urn:UCoSoapDispatcherBase">
            <UserName xsi:type="xsd:string">{escape(user)}</UserName>
            <Password xsi:type="xsd:string">{escape(password)}</Password>
        </NS-1:TAuthenticationHeader>
    </soap-env:Header>
    <soap-env:Body>
        <urn:ExecuteRequest soap-env:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <ARequest xsi:type="xsd:string">{escape(inner_xml)}</ARequest>
        </urn:ExecuteRequest>
    </soap-env:Body>
</soap-env:Envelope>"""


def _soap_request(inner_xml: str) -> str:
    """Stuur een SOAP-request en geeft de uitgepackte Custom Link XML-response terug."""
    url = os.getenv("MENDRIX_SOAP_URL", "")
    if not url:
        raise ValueError("MENDRIX_SOAP_URL is niet ingesteld in .env")

    envelope = _bouw_soap_envelope(inner_xml)
    sessie = _maak_sessie()
    resp = sessie.post(
        url,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": _SOAP_ACTION,
        },
        timeout=20,
    )
    resp.raise_for_status()

    # Pak de inner XML uit de SOAP-wrapper (zit XML-escaped in AResult/return/ExecuteRequestResult)
    for tag in ["AResult", "ExecuteRequestResult", "return"]:
        m = re.search(rf"<[^>]*{tag}[^>]*>(.*?)</[^>]*{tag}>", resp.text, re.DOTALL)
        if m:
            return unescape(m.group(1))
    return resp.text


def haal_order_ids(datum: date) -> list[int]:
    """Haal alle order-IDs op voor ClientNo 3551 op de gegeven datum."""
    datum_str = datum.strftime("%Y-%m-%dT00:00:00")
    inner_xml = f"""<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestOrdersNormalIds Type="TEoCustomLinkRequestOrdersNormalIds"
    xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Nested>False</Nested>
  <Filter Type="TEoFilterOrdersNormal">
    <PeriodBegin>{datum_str}</PeriodBegin>
    <PeriodEnd>{datum_str}</PeriodEnd>
    <ClientNo>{_MENDRIX_CLIENT_NO}</ClientNo>
    <OperatorId>-1</OperatorId>
  </Filter>
</EoCustomLinkRequestOrdersNormalIds>"""

    response_xml = _soap_request(inner_xml)
    # Pak alle <Id> elementen uit de response
    return [int(m) for m in re.findall(r"<Id>(\d+)</Id>", response_xml)]


def _haal_orders_xml(order_ids: list[int]) -> str:
    """Haal orderdetails XML op voor de gegeven order IDs."""
    ids_csv = ",".join(str(i) for i in order_ids)
    inner_xml = f"""<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestOrdersNormal Type="TEoCustomLinkRequestOrdersNormal"
    xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Nested>False</Nested>
  <Filter Type="TEoFilterOrdersNormal">
    <KeysExplicitAsCsv>{ids_csv}</KeysExplicitAsCsv>
  </Filter>
</EoCustomLinkRequestOrdersNormal>"""
    return _soap_request(inner_xml)


def haal_orders_debug(order_ids: list[int], max_orders: int = 3) -> str:
    """Ruwe XML van de eerste max_orders orders — voor veldinspectie."""
    if not order_ids:
        return ""
    return _haal_orders_xml(order_ids[:max_orders])


def _parseer_namen_en_ids(xml: str) -> dict[str, int]:
    """Extraheer {address_name: order_id} uit Mendrix orders XML."""
    resultaat: dict[str, int] = {}
    for blok in re.findall(r"<EoOrderMx\b[^>]*>(.*?)</EoOrderMx>", xml, re.DOTALL):
        order_id_m = re.search(r"<OrderId\b[^>]*>\s*<Id>(\d+)</Id>", blok, re.DOTALL)
        name_m = re.search(
            r"<Tasks\b[^>]*>.*?<Address\b[^>]*>\s*<Name>(.*?)</Name>", blok, re.DOTALL
        )
        if order_id_m and name_m:
            naam = name_m.group(1).strip()
            if naam:
                resultaat[naam] = int(order_id_m.group(1))
    return resultaat


def werkdagen_van_week(datum: date) -> list[date]:
    """Retourneert de werkdagen (ma-vr) van de ISO-week die de gegeven datum bevat."""
    iso = datum.isocalendar()
    maandag = date.fromisocalendar(iso.year, iso.week, 1)
    return [maandag + timedelta(days=i) for i in range(5)]


def haal_mendrix_namen_en_ids(datum: date) -> dict[str, int]:
    """
    Haal alle monsternemer-namen en bijbehorende order-IDs op voor de gegeven datum.
    Returns: {mendrix_address_name: order_id}
    """
    order_ids = haal_order_ids(datum)
    if not order_ids:
        return {}
    xml = _haal_orders_xml(order_ids)
    return _parseer_namen_en_ids(xml)


def _simpele_naam_match(zoek: str, kandidaten: list[str]) -> str | None:
    """
    Probeer zoek te matchen met een van de kandidaten via word-overlap.
    Strips prefixes zoals 'AP06/ONAFH -', 'AP06 -' voor vergelijking.
    """
    zoek_woorden = set(zoek.lower().split())
    beste: str | None = None
    beste_score = 0.0

    for naam in kandidaten:
        kern = naam.split(" - ", 1)[-1].strip() if " - " in naam else naam
        naam_woorden = set(kern.lower().split())
        if not naam_woorden:
            continue
        overlap = zoek_woorden & naam_woorden
        score = len(overlap) / max(len(zoek_woorden), len(naam_woorden))
        if score > beste_score:
            beste_score = score
            beste = naam

    return beste if beste_score >= 0.5 else None


def zoek_mendrix_order(
    naam: str,
    mendrix_namen_ids: dict[str, int],
) -> tuple[int | None, str | None]:
    """
    Zoek een bestaand Mendrix-order voor de gegeven monsternemer-naam.
    Probeert eerst simpele word-overlap, dan AI als fallback.
    Returns: (order_id, gematchte_mendrix_naam) of (None, None).
    """
    if not mendrix_namen_ids:
        return None, None

    kandidaten = list(mendrix_namen_ids.keys())

    match = _simpele_naam_match(naam, kandidaten)
    if match:
        return mendrix_namen_ids[match], match

    # AI-fallback
    try:
        from ap06_planner.services.claude_service import match_naam_mendrix

        ai_match = match_naam_mendrix(naam, kandidaten)
        if ai_match and ai_match in mendrix_namen_ids:
            return mendrix_namen_ids[ai_match], ai_match
    except Exception:
        pass

    return None, None
