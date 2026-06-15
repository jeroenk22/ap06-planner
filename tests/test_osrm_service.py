"""Tests voor osrm_service — geocoding en reistijdberekening."""

from unittest.mock import MagicMock, patch

import pytest

import ap06_planner.services.osrm_service as osrm
from ap06_planner.services.osrm_service import (
    _geocodeer,
    _geocodeer_google,
    _geocodeer_nominatim,
    _osrm_route,
    bereken_aankomsttijd,
    bereken_reistijd_minuten,
)


@pytest.fixture(autouse=True)
def leeg_caches():
    """Verwijder geocode-caches voor elke test."""
    osrm._google_cache.clear()
    osrm._nominatim_cache.clear()
    yield
    osrm._google_cache.clear()
    osrm._nominatim_cache.clear()


def _nominatim_resp(lon: str = "5.0", lat: str = "51.0"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"lon": lon, "lat": lat, "display_name": "Testplaats"}]
    resp.raise_for_status.return_value = None
    return resp


def _nominatim_leeg_resp():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = []
    resp.raise_for_status.return_value = None
    return resp


def _google_ok_resp(lng: float = 5.0, lat: float = 51.0):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "status": "OK",
        "results": [
            {
                "geometry": {"location": {"lng": lng, "lat": lat}},
                "formatted_address": "Testplaats, Nederland",
            }
        ],
    }
    return resp


def _google_geen_resp():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    return resp


def _osrm_ok_resp(duration_sec: float = 1800):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"code": "Ok", "routes": [{"duration": duration_sec}]}
    resp.raise_for_status.return_value = None
    return resp


def _osrm_fout_resp():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"code": "NoRoute", "routes": []}
    resp.raise_for_status.return_value = None
    return resp


class TestGeocodeerNominatim:
    def test_succes(self):
        with patch("requests.get", return_value=_nominatim_resp("5.1", "51.2")):
            result = _geocodeer_nominatim("Bladel, Nederland")
        assert result == (5.1, 51.2)

    def test_geen_resultaat(self):
        with patch("requests.get", return_value=_nominatim_leeg_resp()):
            result = _geocodeer_nominatim("XxOnbestaandXx")
        assert result is None

    def test_exception_geeft_none(self):
        with patch("requests.get", side_effect=Exception("timeout")):
            result = _geocodeer_nominatim("Bladel")
        assert result is None

    def test_caching(self):
        with patch("requests.get", return_value=_nominatim_resp()) as mock_get:
            _geocodeer_nominatim("Bladel")
            _geocodeer_nominatim("Bladel")
            assert mock_get.call_count == 1

    def test_cache_sla_geen_none_op(self):
        with patch("requests.get", return_value=_nominatim_leeg_resp()):
            r1 = _geocodeer_nominatim("OnbestaandeStad")
        with patch("requests.get", return_value=_nominatim_resp()) as mock_get2:
            r2 = _geocodeer_nominatim("OnbestaandeStad")
            # Geen cache omdat r1 None was — opnieuw request
            assert mock_get2.call_count == 1
        assert r1 is None
        assert r2 is not None

    def test_rate_limit_429_logt_warning(self, caplog):
        resp = MagicMock()
        resp.status_code = 429
        with patch("requests.get", return_value=resp):
            with caplog.at_level("WARNING", logger="ap06.osrm"):
                result = _geocodeer_nominatim("Bladel")
        assert result is None
        assert any("429" in r.message for r in caplog.records)


class TestGeocodeerGoogle:
    def test_succes(self):
        with (
            patch("os.getenv", return_value="FAKE_KEY"),
            patch("requests.get", return_value=_google_ok_resp(5.0, 51.0)),
        ):
            result = _geocodeer_google("Bladel")
        assert result == (5.0, 51.0)

    def test_geen_api_key(self):
        with patch("os.getenv", return_value=""):
            result = _geocodeer_google("Bladel")
        assert result is None

    def test_zero_results(self):
        with (
            patch("os.getenv", return_value="FAKE_KEY"),
            patch("requests.get", return_value=_google_geen_resp()),
        ):
            result = _geocodeer_google("OnbestaandeStad")
        assert result is None

    def test_exception_geeft_none(self):
        with (
            patch("os.getenv", return_value="FAKE_KEY"),
            patch("requests.get", side_effect=Exception("network error")),
        ):
            result = _geocodeer_google("Bladel")
        assert result is None

    def test_quota_exceeded_logt_warning(self, caplog):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"status": "OVER_QUERY_LIMIT", "results": []}
        with (
            patch("os.getenv", return_value="FAKE_KEY"),
            patch("requests.get", return_value=resp),
        ):
            with caplog.at_level("WARNING", logger="ap06.osrm"):
                result = _geocodeer_google("Bladel")
        assert result is None
        assert any("OVER_QUERY_LIMIT" in r.message for r in caplog.records)

    def test_request_denied_logt_warning(self, caplog):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"status": "REQUEST_DENIED", "results": []}
        with (
            patch("os.getenv", return_value="FAKE_KEY"),
            patch("requests.get", return_value=resp),
        ):
            with caplog.at_level("WARNING", logger="ap06.osrm"):
                result = _geocodeer_google("Bladel")
        assert result is None
        assert any("REQUEST_DENIED" in r.message for r in caplog.records)

    def test_caching(self):
        with (
            patch("os.getenv", return_value="FAKE_KEY"),
            patch("requests.get", return_value=_google_ok_resp()) as mock_get,
        ):
            _geocodeer_google("Bladel")
            _geocodeer_google("Bladel")
            assert mock_get.call_count == 1


class TestGeocodeer:
    def test_google_primair(self):
        with (
            patch.object(osrm, "_geocodeer_google", return_value=(5.0, 51.0)),
            patch.object(osrm, "_geocodeer_nominatim") as mock_nom,
        ):
            result = _geocodeer("Bladel")
        assert result is not None
        bron, coords = result
        assert bron == "Google Maps"
        assert coords == (5.0, 51.0)
        mock_nom.assert_not_called()

    def test_nominatim_als_google_mislukt(self):
        with (
            patch.object(osrm, "_geocodeer_google", return_value=None),
            patch.object(osrm, "_geocodeer_nominatim", return_value=(5.1, 51.1)),
        ):
            result = _geocodeer("Bladel")
        assert result is not None
        bron, coords = result
        assert bron == "Nominatim"

    def test_koppelteken_fallback_via_google(self):
        """Koppelteken-fallback: altadres gevonden via Google."""
        calls = []

        def fake_google(adres):
            calls.append(adres)
            if "-" not in adres:
                return (5.0, 51.0)
            return None

        with (
            patch.object(osrm, "_geocodeer_google", side_effect=fake_google),
            patch.object(osrm, "_geocodeer_nominatim", return_value=None),
        ):
            result = _geocodeer("Heeswijk-Dinther")
        assert result is not None
        assert "Heeswijk Dinther" in calls

    def test_koppelteken_fallback_via_nominatim(self):
        """Koppelteken-fallback: Google faalt → Nominatim slaagt voor alt adres."""
        calls_nom = []

        def fake_nominatim(adres):
            calls_nom.append(adres)
            if "-" not in adres:
                return (5.1, 51.1)
            return None

        with (
            patch.object(osrm, "_geocodeer_google", return_value=None),
            patch.object(osrm, "_geocodeer_nominatim", side_effect=fake_nominatim),
        ):
            result = _geocodeer("Heeswijk-Dinther")
        assert result is not None
        assert result[0] == "Nominatim"
        assert "Heeswijk Dinther" in calls_nom

    def test_alles_mislukt_geeft_none(self):
        with (
            patch.object(osrm, "_geocodeer_google", return_value=None),
            patch.object(osrm, "_geocodeer_nominatim", return_value=None),
        ):
            result = _geocodeer("OnbestaandeStad")
        assert result is None


class TestOsrmRoute:
    def test_succes(self):
        with patch("requests.get", return_value=_osrm_ok_resp(1800)):
            result = _osrm_route(5.0, 51.0, 5.5, 51.5)
        assert result == 30  # 1800/60 = 30 min

    def test_lokaal_mislukt_gebruikt_fallback(self):
        calls = []

        def fake_get(url, **kw):
            calls.append(url)
            if "192.168" in url:
                raise Exception("lokaal niet bereikbaar")
            return _osrm_ok_resp(900)

        with patch("requests.get", side_effect=fake_get):
            result = _osrm_route(5.0, 51.0, 5.5, 51.5)
        assert result == 15
        assert any("192.168" in c for c in calls)
        assert any("project-osrm" in c for c in calls)

    def test_beide_servers_mislukken(self):
        with patch("requests.get", side_effect=Exception("network")):
            result = _osrm_route(5.0, 51.0, 5.5, 51.5)
        assert result is None

    def test_noroute_code(self):
        with patch("requests.get", return_value=_osrm_fout_resp()):
            result = _osrm_route(5.0, 51.0, 5.5, 51.5)
        # Geen "Ok" code → geen resultaat van lokaal server, probeert fallback ook
        assert result is None

    def test_rate_limit_429_logt_warning(self, caplog):
        resp = MagicMock()
        resp.status_code = 429
        with patch("requests.get", return_value=resp):
            with caplog.at_level("WARNING", logger="ap06.osrm"):
                result = _osrm_route(5.0, 51.0, 5.5, 51.5)
        assert result is None
        assert any("429" in r.message for r in caplog.records)

    def test_server_error_500_logt_warning(self, caplog):
        resp = MagicMock()
        resp.status_code = 503
        with patch("requests.get", return_value=resp):
            with caplog.at_level("WARNING", logger="ap06.osrm"):
                result = _osrm_route(5.0, 51.0, 5.5, 51.5)
        assert result is None
        assert any("503" in r.message for r in caplog.records)


class TestBerekenReistijdMinuten:
    def test_succes(self):
        with (
            patch.object(osrm, "_geocodeer", return_value=("Nominatim", (5.0, 51.0))),
            patch.object(osrm, "_osrm_route", return_value=45),
        ):
            result = bereken_reistijd_minuten("1234AB", "Amsterdam", "5678XY", "Eindhoven")
        assert result == 45

    def test_geocoding_mislukt(self):
        with patch.object(osrm, "_geocodeer", return_value=None):
            result = bereken_reistijd_minuten("1234AB", "Amsterdam", "5678XY", "Eindhoven")
        assert result is None

    def test_zonder_postcode(self):
        with (
            patch.object(osrm, "_geocodeer", return_value=("Nominatim", (5.0, 51.0))),
            patch.object(osrm, "_osrm_route", return_value=20),
        ):
            result = bereken_reistijd_minuten("", "Amsterdam", "", "Eindhoven")
        assert result == 20


class TestBerekenAankomsttijd:
    def test_succes_buffer_15(self):
        """Reistijd < 60 min → +15 min buffer."""
        with (
            patch.object(osrm, "_geocodeer", return_value=("Nominatim", (5.0, 51.0))),
            patch.object(osrm, "_osrm_route", return_value=30),
        ):
            begin, eind, debug = bereken_aankomsttijd(
                vertrekplaats="Bladel",
                woonplaats="Amsterdam",
                woonplaats_postcode="1234AB",
                eind_tijdvenster="18:00",
                uiterlijke_tijd="21:30",
            )
        # 18:00 + 30 min + 15 buffer = 18:45 → afgerond kwartier = 18:45
        assert begin == "18:45"
        assert eind == "21:30"
        assert "30 min" in debug

    def test_succes_buffer_30(self):
        """Reistijd ≥ 60 min → +30 min buffer."""
        with (
            patch.object(osrm, "_geocodeer", return_value=("Nominatim", (5.0, 51.0))),
            patch.object(osrm, "_osrm_route", return_value=90),
        ):
            begin, eind, debug = bereken_aankomsttijd(
                vertrekplaats="Tilburg",
                woonplaats="Groningen",
                woonplaats_postcode="9712AB",
                eind_tijdvenster="12:00",
                uiterlijke_tijd=None,
            )
        # 12:00 + 90 + 30 = 13:60 → 14:00 afgerond op kwartier
        assert begin == "14:00"
        assert eind == "23:59"

    def test_geocoding_thuis_mislukt(self):
        with patch.object(osrm, "_geocodeer", return_value=None):
            begin, eind, debug = bereken_aankomsttijd(
                vertrekplaats="Bladel",
                woonplaats="OnbestaandeStad",
                woonplaats_postcode="",
                eind_tijdvenster="18:00",
                uiterlijke_tijd=None,
            )
        assert begin == "18:00"
        assert "mislukt" in debug

    def test_geocoding_vertrek_mislukt(self):
        calls = {"count": 0}

        def fake_geocodeer(adres):
            calls["count"] += 1
            if calls["count"] == 1:
                return ("Nominatim", (5.0, 51.0))  # thuis OK
            return None  # vertrek mislukt

        with patch.object(osrm, "_geocodeer", side_effect=fake_geocodeer):
            begin, eind, debug = bereken_aankomsttijd(
                vertrekplaats="OnbestaandeStad",
                woonplaats="Amsterdam",
                woonplaats_postcode="1234AB",
                eind_tijdvenster="18:00",
                uiterlijke_tijd=None,
            )
        assert begin == "18:00"
        assert "mislukt" in debug

    def test_osrm_mislukt(self):
        with (
            patch.object(osrm, "_geocodeer", return_value=("Nominatim", (5.0, 51.0))),
            patch.object(osrm, "_osrm_route", return_value=None),
        ):
            begin, eind, debug = bereken_aankomsttijd(
                vertrekplaats="Bladel",
                woonplaats="Amsterdam",
                woonplaats_postcode="1234AB",
                eind_tijdvenster="18:00",
                uiterlijke_tijd=None,
            )
        assert begin == "18:00"
        assert "onbekend" in debug

    def test_kwartier_afronding(self):
        """Resultaat moet altijd op kwartier afgerond zijn."""
        with (
            patch.object(osrm, "_geocodeer", return_value=("Nominatim", (5.0, 51.0))),
            patch.object(osrm, "_osrm_route", return_value=31),
        ):
            begin, _, _ = bereken_aankomsttijd(
                vertrekplaats="Bladel",
                woonplaats="Amsterdam",
                woonplaats_postcode="1234AB",
                eind_tijdvenster="18:00",
                uiterlijke_tijd=None,
            )
        # 18:00 + 31 + 15 = 18:46 → afgerond naar 19:00 (volgende kwartier)
        minuten = int(begin.split(":")[1])
        assert minuten % 15 == 0
