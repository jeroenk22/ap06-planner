"""Tests voor nager_service — feestdagen en ophaaldag-logica."""

from datetime import date
from unittest.mock import patch

import pytest

import ap06_planner.services.nager_service as nager
from ap06_planner.services.nager_service import (
    eerstvolgende_ophaaldag,
    haal_feestdagen,
    is_feestdag,
)


@pytest.fixture(autouse=True)
def leeg_cache():
    """Verwijder cache voor elke test."""
    nager._feestdagen_cache.clear()
    yield
    nager._feestdagen_cache.clear()


def _mock_feestdag_response(data: list[dict]):
    """Helper: mock requests.get die feestdagdata retourneert."""
    import requests

    mock_resp = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: data,
    })()
    return mock_resp


class TestHaalFeestdagen:
    def test_haalt_feestdagen_op(self):
        feestdag_data = [{"date": "2026-04-05"}, {"date": "2026-12-25"}]
        with patch("requests.get") as mock_get:
            mock_get.return_value = _mock_feestdag_response(feestdag_data)
            result = haal_feestdagen(2026)
        assert date(2026, 4, 5) in result
        assert date(2026, 12, 25) in result

    def test_caching(self):
        feestdag_data = [{"date": "2026-04-05"}]
        with patch("requests.get") as mock_get:
            mock_get.return_value = _mock_feestdag_response(feestdag_data)
            haal_feestdagen(2026)
            haal_feestdagen(2026)  # Tweede aanroep
            assert mock_get.call_count == 1  # Alleen één HTTP-call

    def test_api_fout_geeft_lege_set(self):
        with patch("requests.get", side_effect=Exception("timeout")):
            result = haal_feestdagen(2026)
        assert result == set()

    def test_http_fout_geeft_lege_set(self):
        import requests

        def raise_http(*a, **kw):
            raise requests.HTTPError("500")

        with patch("requests.get", side_effect=raise_http):
            result = haal_feestdagen(2026)
        assert result == set()

    def test_verschillende_jaren_apart_gecached(self):
        data_2026 = [{"date": "2026-04-05"}]
        data_2027 = [{"date": "2027-04-25"}]
        with patch("requests.get") as mock_get:
            mock_get.return_value = _mock_feestdag_response(data_2026)
            r2026 = haal_feestdagen(2026)
            mock_get.return_value = _mock_feestdag_response(data_2027)
            r2027 = haal_feestdagen(2027)
        assert date(2026, 4, 5) in r2026
        assert date(2027, 4, 25) in r2027


class TestIsFeestdag:
    def test_feestdag_herkend(self):
        with patch.object(nager, "haal_feestdagen", return_value={date(2026, 4, 5)}):
            assert is_feestdag(date(2026, 4, 5)) is True

    def test_gewone_dag(self):
        with patch.object(nager, "haal_feestdagen", return_value={date(2026, 4, 5)}):
            assert is_feestdag(date(2026, 4, 6)) is False

    def test_geen_feestdagen_bekend(self):
        with patch.object(nager, "haal_feestdagen", return_value=set()):
            assert is_feestdag(date(2026, 6, 1)) is False


class TestEerstvolgendeOphaaldag:
    def test_vandaag_is_ophaaldag(self):
        maandag = date(2026, 6, 1)  # weekday() == 0 (ma)
        with patch.object(nager, "is_feestdag", return_value=False):
            dag, _ = eerstvolgende_ophaaldag(maandag, ["ma"])
        assert dag == maandag

    def test_volgende_woensdag(self):
        maandag = date(2026, 6, 1)  # ma
        with patch.object(nager, "is_feestdag", return_value=False):
            dag, _ = eerstvolgende_ophaaldag(maandag, ["wo"])
        assert dag == date(2026, 6, 3)

    def test_feestdag_overgeslagen(self):
        # Maandag is feestdag → geeft woensdag
        maandag = date(2026, 6, 1)

        def fake_feestdag(d):
            return d == maandag

        with patch.object(nager, "is_feestdag", side_effect=fake_feestdag):
            dag, _ = eerstvolgende_ophaaldag(maandag, ["ma", "wo"])
        assert dag == date(2026, 6, 3)  # woensdag

    def test_lege_ophaaldagen_geeft_vandaag(self):
        vandaag = date(2026, 6, 1)
        dag, omzeild = eerstvolgende_ophaaldag(vandaag, [])
        assert dag == vandaag
        assert omzeild is False

    def test_onbekende_afkorting_overgeslagen(self):
        maandag = date(2026, 6, 1)
        with patch.object(nager, "is_feestdag", return_value=False):
            dag, _ = eerstvolgende_ophaaldag(maandag, ["xx", "ma"])
        assert dag == maandag

    def test_geen_feestdagen_controleren(self):
        maandag = date(2026, 6, 1)
        dag, _ = eerstvolgende_ophaaldag(maandag, ["ma"], sla_feestdagen_over=False)
        assert dag == maandag

    def test_max_iteraties_fallback(self):
        """Als alle kandidaatdagen feestdag zijn → fallback na 30 iteraties."""
        maandag = date(2026, 6, 1)
        with patch.object(nager, "is_feestdag", return_value=True):
            dag, _ = eerstvolgende_ophaaldag(
                maandag,
                ["ma", "di", "wo", "do", "vr", "za", "zo"],
            )
        assert dag == maandag  # Fallback: originele datum
