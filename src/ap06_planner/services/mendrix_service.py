"""
mendrix_service.py — Raadpleeg en beheer Mendrix Custom Link orders via SOAP.

Flow:
  1. haal_order_ids(datum) → lijst van order-IDs voor ClientNo 3551 op die dag
  2. haal_orders_debug(order_ids) → ruwe XML-response van de eerste orders (voor veldinspectie)
  3. maak_mendrix_order(...) → maakt een nieuw LAAD-order aan voor een monsternemer
"""

import logging
import os
import re
import ssl
from datetime import date, timedelta
from html import escape, unescape
from urllib.parse import urlparse

import requests

_log = logging.getLogger(__name__)
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


_sessie_cache: requests.Session | None = None


def _maak_sessie() -> requests.Session:
    global _sessie_cache
    if _sessie_cache is not None:
        return _sessie_cache
    s = requests.Session()
    url = os.getenv("MENDRIX_SOAP_URL", "")
    parsed = urlparse(url)
    prefix = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "https://"
    s.mount(prefix, _LegacySslAdapter())
    _sessie_cache = s
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


def _bereken_duur(begin: str, eind: str) -> tuple[float, str]:
    """Duur tussen twee HH:MM tijden. Retourneert (uren_float, DurationInDateTime-string)."""
    bh, bm = int(begin[:2]), int(begin[3:5])
    eh, em = int(eind[:2]), int(eind[3:5])
    minuten = (eh * 60 + em) - (bh * 60 + bm)
    if minuten < 0:
        minuten += 24 * 60
    uren = minuten / 60.0
    hh, mm = divmod(minuten, 60)
    return uren, f"1899-12-30T{hh:02d}:{mm:02d}:00+01:00"


def _vervang_requested_tijden(xml: str, nieuwe_begin: str, nieuwe_eind: str) -> str:
    """Vervang DateTimeBegin, DateTimeEnd en DurationIn* uitsluitend binnen <Requested> blokken."""
    duur_uren, duur_dt = _bereken_duur(nieuwe_begin, nieuwe_eind)

    def _verwerk_blok(m: re.Match) -> str:
        blok = re.sub(
            r"(<DateTimeBegin>[^T<]*T)\d{2}:\d{2}(:\d{2})?([^<]*</DateTimeBegin>)",
            lambda b: f"{b.group(1)}{nieuwe_begin}:00{b.group(3)}",
            m.group(0),
        )
        blok = re.sub(
            r"(<DateTimeEnd>[^T<]*T)\d{2}:\d{2}(:\d{2})?([^<]*</DateTimeEnd>)",
            lambda b: f"{b.group(1)}{nieuwe_eind}:00{b.group(3)}",
            blok,
        )
        blok = re.sub(
            r"<DurationInHours>[^<]*</DurationInHours>",
            f"<DurationInHours>{duur_uren}</DurationInHours>",
            blok,
        )
        blok = re.sub(
            r"<DurationInDateTime>[^<]*</DurationInDateTime>",
            f"<DurationInDateTime>{duur_dt}</DurationInDateTime>",
            blok,
        )
        return blok

    return re.sub(r"<Requested\b[^>]*>.*?</Requested>", _verwerk_blok, xml, flags=re.DOTALL)


def _splits_order_xml(batch_xml: str) -> dict[int, str]:
    """Splits batch response XML in losse per-order XML strings, klaar voor Store-aanroep."""
    wrapper_m = re.search(r"(<EoCustomLinkResponseOrdersNormal\b[^>]*>)", batch_xml)
    open_tag = wrapper_m.group(1) if wrapper_m else "<EoCustomLinkResponseOrdersNormal>"
    data_m = re.search(r"(<Data\b[^>]*>)", batch_xml)
    data_open = data_m.group(1) if data_m else "<Data>"
    result: dict[int, str] = {}
    for blok in re.findall(r"<EoOrderMx\b[^>]*>.*?</EoOrderMx>", batch_xml, re.DOTALL):
        id_m = re.search(r"<OrderId\b[^>]*>\s*<Id>(\d+)</Id>", blok, re.DOTALL)
        if id_m:
            oid = int(id_m.group(1))
            inner = f"{data_open}\n<_TEoListBase_Items>\n{blok}\n</_TEoListBase_Items>\n</Data>"
            result[oid] = f"{open_tag}\n{inner}\n</EoCustomLinkResponseOrdersNormal>"
    return result


def update_mendrix_tijdvenster(
    order_id: int,
    nieuwe_begin: str,
    nieuwe_eind: str,
    cached_xml: str | None = None,
) -> tuple[bool, str]:
    """
    Update de Requested DateTimeBegin en DateTimeEnd van een Mendrix order.
    Als cached_xml meegegeven is, wordt die gebruikt i.p.v. een nieuwe SOAP-fetch.
    Returns (succes, melding).
    """
    try:
        response_xml = cached_xml or _haal_orders_xml([order_id])
        if not response_xml:
            return False, "Geen order XML ontvangen van Mendrix"

        aangepast = _vervang_requested_tijden(response_xml, nieuwe_begin, nieuwe_eind)

        # Response-wrapper omzetten naar Store-wrapper
        store_xml = re.sub(
            r"<EoCustomLinkResponseOrdersNormal\b[^>]*>",
            '<EoCustomLinkStoreOrdersNormal Type="TEoCustomLinkStoreOrdersNormal">',
            aangepast,
        )
        store_xml = store_xml.replace(
            "</EoCustomLinkResponseOrdersNormal>",
            "</EoCustomLinkStoreOrdersNormal>",
        )

        result_xml = _soap_request(store_xml)

        if "srUpdated" in result_xml or "srInserted" in result_xml:
            return True, f"Order #{order_id} bijgewerkt naar {nieuwe_begin}–{nieuwe_eind}"
        err_m = re.search(r"<ErrorMessage>(.*?)</ErrorMessage>", result_xml, re.DOTALL)
        err = err_m.group(1).strip() if err_m else result_xml[:200]
        return False, f"Mendrix fout: {err}"

    except Exception as e:
        return False, f"Fout bij bijwerken order #{order_id}: {e}"


def _parseer_namen_en_ids(xml: str) -> dict[str, dict]:
    """Extraheer {address_name: {"order_id": int, "van": str|None, "tot": str|None}} uit Mendrix orders XML."""
    resultaat: dict[str, dict] = {}
    for blok in re.findall(r"<EoOrderMx\b[^>]*>(.*?)</EoOrderMx>", xml, re.DOTALL):
        order_id_m = re.search(r"<OrderId\b[^>]*>\s*<Id>(\d+)</Id>", blok, re.DOTALL)
        name_m = re.search(
            r"<Tasks\b[^>]*>.*?<Address\b[^>]*>\s*<Name>(.*?)</Name>", blok, re.DOTALL
        )
        if order_id_m and name_m:
            naam = name_m.group(1).strip()
            if naam:
                van: str | None = None
                tot: str | None = None
                req_m = re.search(r"<Requested\b[^>]*>(.*?)</Requested>", blok, re.DOTALL)
                if req_m:
                    begin_m = re.search(r"<DateTimeBegin>(.*?)</DateTimeBegin>", req_m.group(1))
                    eind_m = re.search(r"<DateTimeEnd>(.*?)</DateTimeEnd>", req_m.group(1))
                    # "2026-06-10T13:00:00" → "13:00"
                    if begin_m and "T" in begin_m.group(1):
                        van = begin_m.group(1).strip().split("T")[1][:5]
                    if eind_m and "T" in eind_m.group(1):
                        tot = eind_m.group(1).strip().split("T")[1][:5]
                resultaat[naam] = {"order_id": int(order_id_m.group(1)), "van": van, "tot": tot}
    return resultaat


def werkdagen_van_week(datum: date) -> list[date]:
    """Retourneert de werkdagen (ma-vr) van de ISO-week die de gegeven datum bevat."""
    iso = datum.isocalendar()
    maandag = date.fromisocalendar(iso.year, iso.week, 1)
    return [maandag + timedelta(days=i) for i in range(5)]


def haal_mendrix_namen_en_ids(datum: date) -> dict[str, dict]:
    """
    Haal alle monsternemer-namen en bijbehorende order-info op voor de gegeven datum.
    Returns: {mendrix_address_name: {"order_id": int, "van": str|None, "tot": str|None}}
    """
    order_ids = haal_order_ids(datum)
    if not order_ids:
        return {}
    xml = _haal_orders_xml(order_ids)
    return _parseer_namen_en_ids(xml)


def haal_mendrix_namen_ids_en_xml(datum: date) -> tuple[dict[str, dict], dict[int, str]]:
    """
    Zoals haal_mendrix_namen_en_ids, maar geeft ook per-order XML terug voor gebruik
    als cached_xml in update_mendrix_tijdvenster (vermijdt dubbele SOAP-fetch).
    Returns: (namen_ids, {order_id: xml_string})
    """
    order_ids = haal_order_ids(datum)
    if not order_ids:
        return {}, {}
    xml = _haal_orders_xml(order_ids)
    return _parseer_namen_en_ids(xml), _splits_order_xml(xml)


_TUSSENVOEGSELS = frozenset(
    {"van", "de", "den", "der", "het", "ten", "ter", "in", "op", "te", "uit", "bij", "des"}
)


def _achternaam(naam_lower: str) -> str | None:
    """Laatste woord dat geen Nederlands tussenvoegsel is."""
    return next((w for w in reversed(naam_lower.split()) if w not in _TUSSENVOEGSELS), None)


def _voornaam(naam_lower: str) -> str | None:
    """Eerste woord van de naam."""
    words = naam_lower.split()
    return words[0] if words else None


def _simpele_naam_match(zoek: str, kandidaten: list[str]) -> str | None:
    """
    Probeer zoek te matchen met een van de kandidaten via word-overlap.
    Strips prefixes zoals 'AP06/ONAFH -', 'AP06 -' voor vergelijking.
    Achternamen (laatste niet-tussenvoegsel woord) moeten overeenkomen om
    false positives zoals 'Johan van Zoggel' ↔ 'Johan van Gool' te voorkomen.
    Voornamen moeten ook overeenkomen als beide vol uitgeschreven zijn (len > 1),
    om false positives zoals 'Bert Coppens' ↔ 'Piet Coppens' te voorkomen.
    """
    zoek_lower = zoek.lower()
    zoek_woorden = set(zoek_lower.split())
    zoek_ach = _achternaam(zoek_lower)
    zoek_voor = _voornaam(zoek_lower)
    beste: str | None = None
    beste_score = 0.0

    for naam in kandidaten:
        kern = naam.split(" - ", 1)[-1].strip() if " - " in naam else naam
        kern_lower = kern.lower()
        naam_woorden = set(kern_lower.split())
        if not naam_woorden:
            continue
        # Achternamen moeten overeenkomen
        if zoek_ach and _achternaam(kern_lower) != zoek_ach:
            continue
        # Voornamen mogen niet conflicteren (beide vol uitgeschreven maar verschillend)
        kern_voor = _voornaam(kern_lower)
        if (
            zoek_voor and kern_voor
            and len(zoek_voor) > 1 and len(kern_voor) > 1
            and zoek_voor != kern_voor
        ):
            continue
        overlap = zoek_woorden & naam_woorden
        score = len(overlap) / max(len(zoek_woorden), len(naam_woorden))
        if score > beste_score:
            beste_score = score
            beste = naam

    return beste if beste_score >= 0.5 else None


def zoek_mendrix_order(
    naam: str,
    mendrix_namen_ids: dict[str, dict],
    gebruik_ai_fallback: bool = True,
) -> tuple[int | None, str | None]:
    """
    Zoek een bestaand Mendrix-order voor de gegeven monsternemer-naam.
    Probeert eerst simpele word-overlap, dan AI als fallback (tenzij gebruik_ai_fallback=False).
    Gebruik gebruik_ai_fallback=False voor de tweede pass (⚠️-detectie op andere datum):
    liever ❌ dan een verkeerde ⚠️ door een AI die een andere persoon koppelt.
    Returns: (order_id, gematchte_mendrix_naam) of (None, None).
    """
    if not mendrix_namen_ids:
        return None, None

    kandidaten = list(mendrix_namen_ids.keys())

    match = _simpele_naam_match(naam, kandidaten)
    if match:
        return mendrix_namen_ids[match]["order_id"], match

    if gebruik_ai_fallback:
        try:
            from ap06_planner.services.claude_service import match_naam_mendrix

            ai_match = match_naam_mendrix(naam, kandidaten)
            if ai_match and ai_match in mendrix_namen_ids:
                return mendrix_namen_ids[ai_match]["order_id"], ai_match
        except Exception:
            _log.debug("AI naam-match mislukt voor '%s'", naam, exc_info=True)

    return None, None


_PRODUCT_ID = 58  # Eurofins Agro AP06 product in Mendrix
_PACKING_NAME = "Mo Eurofins Wageningen BLGG"


def maak_mendrix_order(
    naam: str,
    adres: str,
    postcode: str,
    woonplaats: str,
    telefoon: str | None,
    bijzonderheden: str | None,
    laadinstructie: str | None,
    uiterlijke_plantijd: str | None,
    algemene_instructie_ap06: str,
    ophaaldagen: list[str],
    inplan_datum: date,
    gewensttijd_begin: str,
    gewensttijd_eind: str,
) -> tuple[bool, str]:
    """
    Maakt een nieuw LAAD-order aan in Mendrix voor een monsternemer.
    Returns (succes, melding). Bij succes bevat de melding het nieuwe order-ID.
    """
    try:
        # Splits adres in straat + huisnummer
        adres_m = re.match(r"^(.*?)\s+(\d+\S*)$", adres.strip())
        straat = adres_m.group(1) if adres_m else adres
        nummer = adres_m.group(2) if adres_m else ""

        # Assembleer instructietekst
        instructie_regels = ["AP06 monsters ophalen voor Eurofins Wageningen."]
        if uiterlijke_plantijd:
            instructie_regels.append(f"Ophalen vóór {uiterlijke_plantijd}!")
        if laadinstructie:
            instructie_regels.append(laadinstructie)
        if algemene_instructie_ap06:
            instructie_regels.append(algemene_instructie_ap06)
        instructies = "\n".join(instructie_regels)

        ophaaldagen_str = "-".join(ophaaldagen) if ophaaldagen else ""
        voornaam = naam.split()[0] if naam else naam
        notes = f"AP06 - Ophaaldagen {voornaam}: {ophaaldagen_str} (order automatisch ingeschoten)"

        datum_str = inplan_datum.strftime("%Y-%m-%d")
        begin_dt = f"{datum_str}T{gewensttijd_begin}:00"
        eind_dt = f"{datum_str}T{gewensttijd_eind}:00"
        duur_uren, duur_dt = _bereken_duur(gewensttijd_begin, gewensttijd_eind)

        inner_xml = f"""<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreOrdersNormal Type="TEoCustomLinkStoreOrdersNormal">
  <Data Type="TEoOrderMxList">
    <_TEoListBase_Items>
      <EoOrderMx Type="TEoOrderMx">
        <OrderId Type="TEoKeyIntInfraMx"><Id>-1000</Id></OrderId>
        <RelationId Type="TEoKeyIntInfraMx"><Id>{_MENDRIX_CLIENT_NO}</Id></RelationId>
        <ClientId Type="TEoKeyIntInfraMx"><Id>{_MENDRIX_CLIENT_NO}</Id></ClientId>
        <Confirmed>False</Confirmed>
        <Notes>{escape(notes)}</Notes>
        <ProductId Type="TEoKeyIntInfraMx"><Id>{_PRODUCT_ID}</Id></ProductId>
        <ProductIdAutomaticArticles>True</ProductIdAutomaticArticles>
        <Goods Type="TEoGoodMxList">
          <_TEoListBase_Items>
            <EoGoodMx Type="TEoGoodMx">
              <GoodId Type="TEoKeyIntInfraMx"><Id>-1</Id></GoodId>
              <Amount>1</Amount>
              <Parts>1.0</Parts>
              <Packing Type="TEoPackingMx">
                <Name>{escape(_PACKING_NAME)}</Name>
                <Amount>0.0</Amount>
              </Packing>
            </EoGoodMx>
          </_TEoListBase_Items>
        </Goods>
        <Tasks Type="TEoTaskMxList">
          <_TEoListBase_Items>
            <EoTaskMx Type="TEoTaskMx">
              <TaskId Type="TEoKeyIntInfraMx"><Id>-100</Id></TaskId>
              <Address Type="TEoAddress">
                <Name>{escape(f"AP06/ONAFH - {naam}")}</Name>
                <Premise>{escape(bijzonderheden or "")}</Premise>
                <Street>{escape(straat)}</Street>
                <Number>{escape(nummer)}</Number>
                <PostalCode>{escape(postcode)}</PostalCode>
                <Place>{escape(woonplaats)}</Place>
                <Country>Nederland</Country>
                <CountryCode>NL</CountryCode>
              </Address>
              <Connectivity Type="TEoConnectivity">
                <Email/>
                <Fax/>
                <Mobile>{escape(telefoon or "")}</Mobile>
                <Phone/>
                <Web/>
              </Connectivity>
              <Instructions>{escape(instructies)}</Instructions>
              <OperatorIdAutomatic>True</OperatorIdAutomatic>
              <Planned Type="TEoDateTimeWindow">
                <DateTimeEnd>{begin_dt}</DateTimeEnd>
                <DateTimeBegin>{begin_dt}</DateTimeBegin>
              </Planned>
              <Requested Type="TEoDateTimeWindow">
                <DateTimeBegin>{begin_dt}</DateTimeBegin>
                <DateTimeEnd>{eind_dt}</DateTimeEnd>
                <DurationInDateTime>{duur_dt}</DurationInDateTime>
                <DurationInHours>{duur_uren}</DurationInHours>
              </Requested>
              <TaskTypeId Type="TEoKeyIntInfraMx"><Id>1</Id></TaskTypeId>
            </EoTaskMx>
          </_TEoListBase_Items>
        </Tasks>
        <GoodsToTasks Type="TEoGoodToTaskMxList">
          <_TEoListBase_Items>
            <EoGoodToTaskMx Type="TEoGoodToTaskMx">
              <GoodId Type="TEoKeyIntInfraMx"><Id>-1</Id></GoodId>
              <TaskId Type="TEoKeyIntInfraMx"><Id>-100</Id></TaskId>
            </EoGoodToTaskMx>
          </_TEoListBase_Items>
        </GoodsToTasks>
      </EoOrderMx>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkStoreOrdersNormal>"""

        result_xml = _soap_request(inner_xml)

        if "srInserted" in result_xml:
            # Zoek het nieuwe order-ID: <Id> staat vóór <IdOld>-1000</IdOld>
            new_id_m = re.search(
                r"<Id>(-?\d+)</Id>.*?<IdOld>-1000</IdOld>", result_xml, re.DOTALL
            )
            new_id = new_id_m.group(1) if new_id_m else "?"
            return True, f"Order #{new_id} aangemaakt voor {naam}"

        err_m = re.search(r"<StoreDescription>(.*?)</StoreDescription>", result_xml, re.DOTALL)
        err = err_m.group(1).strip() if err_m else result_xml[:200]
        return False, f"Mendrix fout: {err}"

    except Exception as e:
        return False, f"Fout bij aanmaken order voor {naam}: {e}"
