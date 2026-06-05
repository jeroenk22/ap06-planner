"""Tests voor claude_service — API-integratie met mocked Anthropic client."""

import json
from unittest.mock import MagicMock, patch

import pytest

import ap06_planner.services.claude_service as cs
from ap06_planner.services.claude_service import (
    _get_client,
    _parse_json,
    analyseer_tijdvenster_met_claude,
    interpreteer_wijzigingen,
    interpreteer_wijzigingen_batch,
    match_monsternemer_naam,
    verwerk_planningsregels_batch,
)


def _maak_message(tekst: str):
    """Helper: maak een nep-Anthropic message object."""
    blok = MagicMock()
    blok.type = "text"
    blok.text = tekst
    msg = MagicMock()
    msg.content = [blok]
    return msg


def _maak_client(response_tekst: str):
    """Helper: maak een nep-Anthropic client die response_tekst retourneert."""
    client = MagicMock()
    client.messages.create.return_value = _maak_message(response_tekst)
    return client


class TestParseJson:
    def test_schone_json_array(self):
        result = _parse_json('[{"a": 1}]')
        assert result == [{"a": 1}]

    def test_schone_json_object(self):
        result = _parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_code_block(self):
        tekst = '```json\n[{"a": 1}]\n```'
        result = _parse_json(tekst)
        assert result == [{"a": 1}]

    def test_markdown_zonder_taal(self):
        tekst = '```\n[{"a": 2}]\n```'
        result = _parse_json(tekst)
        assert result == [{"a": 2}]

    def test_preamble_tekst_voor_json(self):
        tekst = 'Hier is de output:\n[{"x": 5}]'
        result = _parse_json(tekst)
        assert result == [{"x": 5}]

    def test_lege_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("")

    def test_ongeldige_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("dit is geen json")

    def test_preamble_voor_object(self):
        tekst = 'Antwoord: {"sleutel": "waarde"}'
        result = _parse_json(tekst)
        assert result == {"sleutel": "waarde"}


class TestGetClient:
    def test_zonder_api_key_raises(self):
        cs._client = None
        with (
            patch("os.getenv", return_value=None),
            pytest.raises(ValueError, match="ANTHROPIC_API_KEY"),
        ):
            _get_client()

    def test_met_api_key(self):
        cs._client = None
        with patch("os.getenv", return_value="test-key"), patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = _get_client()
        assert client is not None

    def test_caching_client(self):
        fake_client = MagicMock()
        cs._client = fake_client
        result = _get_client()
        assert result is fake_client
        cs._client = None  # Opschonen


class TestVerwerkPlanningsregelsBatch:
    def test_lege_invoer(self):
        resultaten, fout = verwerk_planningsregels_batch([])
        assert resultaten == []
        assert fout is None

    def test_succes(self):
        invoer = [{"locatie": "Bladel TonTrans 7-18 LAD17", "wijziging": None}]
        response = json.dumps(
            [
                {
                    "plaats": "Bladel",
                    "begintijd": "07:00",
                    "eindtijd": "18:00",
                    "type": "LAD",
                    "nummer": "17",
                    "overgeslagen": False,
                }
            ]
        )
        fake_client = _maak_client(response)
        with patch.object(cs, "_get_client", return_value=fake_client):
            resultaten, fout = verwerk_planningsregels_batch(invoer)
        assert fout is None
        assert resultaten is not None
        assert len(resultaten) == 1
        assert resultaten[0]["plaats"] == "Bladel"

    def test_deduplicatie(self):
        """Dezelfde locatie wordt slechts één keer naar Claude gestuurd."""
        invoer = [
            {"locatie": "Bladel TonTrans 7-18 LAD1", "wijziging": None},
            {"locatie": "Bladel TonTrans 7-18 LAD2", "wijziging": None},
        ]
        response = json.dumps(
            [
                {
                    "plaats": "Bladel",
                    "begintijd": "07:00",
                    "eindtijd": "18:00",
                    "type": "LAD",
                    "nummer": None,
                    "overgeslagen": False,
                }
            ]
        )
        fake_client = _maak_client(response)
        with patch.object(cs, "_get_client", return_value=fake_client):
            resultaten, fout = verwerk_planningsregels_batch(invoer)
        assert fout is None
        assert resultaten is not None
        assert len(resultaten) == 2
        assert fake_client.messages.create.call_count == 1  # Eén API-call

    def test_verkeerd_aantal_resultaten(self):
        invoer = [{"locatie": "A", "wijziging": None}, {"locatie": "B", "wijziging": None}]
        response = json.dumps([{"plaats": "X"}])  # Slechts 1 resultaat voor 2 unieke items
        fake_client = _maak_client(response)
        with patch.object(cs, "_get_client", return_value=fake_client):
            resultaten, fout = verwerk_planningsregels_batch(invoer)
        assert resultaten is None
        assert fout is not None
        assert "resultaten" in fout

    def test_json_fout(self):
        fake_client = _maak_client("dit is geen json")
        with patch.object(cs, "_get_client", return_value=fake_client):
            resultaten, fout = verwerk_planningsregels_batch(
                [{"locatie": "Bladel 7-18 LAD", "wijziging": None}]
            )
        assert resultaten is None
        assert fout is not None
        assert "JSON-fout" in fout

    def test_api_fout(self):
        with patch.object(cs, "_get_client", side_effect=ValueError("geen key")):
            resultaten, fout = verwerk_planningsregels_batch(
                [{"locatie": "Bladel 7-18 LAD", "wijziging": None}]
            )
        assert resultaten is None
        assert fout is not None

    def test_chunking_meer_dan_10(self):
        """Batches >10 items worden in chunks van 10 verwerkt."""
        invoer = [{"locatie": f"Stad{i} 7-18 LAD{i}", "wijziging": None} for i in range(15)]
        item = {
            "plaats": "Stad",
            "begintijd": "07:00",
            "eindtijd": "18:00",
            "type": "LAD",
            "nummer": None,
            "overgeslagen": False,
        }

        call_count = {"n": 0}

        def fake_create(**kwargs):
            n = len(json.loads(kwargs["messages"][0]["content"]))
            call_count["n"] += 1
            return _maak_message(json.dumps([item] * n))

        fake_client = MagicMock()
        fake_client.messages.create.side_effect = fake_create
        with patch.object(cs, "_get_client", return_value=fake_client):
            resultaten, fout = verwerk_planningsregels_batch(invoer)
        assert fout is None
        assert resultaten is not None
        assert len(resultaten) == 15
        assert call_count["n"] == 2  # 15 unieke items → 2 chunks (10+5)


class TestAnalyseerTijdvensterMetClaude:
    def test_succes(self):
        response = json.dumps(
            [
                {
                    "plaats": "Bladel",
                    "begintijd": "07:00",
                    "eindtijd": "18:00",
                    "type": "LAD",
                    "nummer": "17",
                    "overgeslagen": False,
                }
            ]
        )
        fake_client = _maak_client(response)
        with patch.object(cs, "_get_client", return_value=fake_client):
            result = analyseer_tijdvenster_met_claude("Bladel TonTrans 7-18 LAD17")
        assert result is not None
        assert result["plaats"] == "Bladel"

    def test_lege_resultaten_geeft_none(self):
        with patch.object(cs, "verwerk_planningsregels_batch", return_value=([], None)):
            result = analyseer_tijdvenster_met_claude("test")
        assert result is None


class TestInterpreteerWijzigingenBatch:
    def test_lege_lijst(self):
        result = interpreteer_wijzigingen_batch([])
        assert result == {}

    def test_alleen_lege_strings(self):
        result = interpreteer_wijzigingen_batch(["", None])
        assert result == {}

    def test_succes(self):
        response = json.dumps(
            [
                {
                    "tijdvervang": ["12:00", "18:00"],
                    "start_na": None,
                    "eind_voor": None,
                    "hele_dag": False,
                    "negeer": False,
                }
            ]
        )
        fake_client = _maak_client(response)
        with patch.object(cs, "_get_client", return_value=fake_client):
            result = interpreteer_wijzigingen_batch(["Naar 12-18"])
        assert result is not None
        assert "Naar 12-18" in result

    def test_api_fout_geeft_none(self):
        with patch.object(cs, "_get_client", side_effect=Exception("network error")):
            result = interpreteer_wijzigingen_batch(["Naar 12-18"])
        assert result is None

    def test_deduplicatie(self):
        """Duplicaten worden slechts eenmaal naar API gestuurd."""
        response = json.dumps(
            [
                {
                    "tijdvervang": None,
                    "start_na": "12:00",
                    "eind_voor": None,
                    "hele_dag": False,
                    "negeer": False,
                }
            ]
        )
        fake_client = _maak_client(response)
        with patch.object(cs, "_get_client", return_value=fake_client):
            result = interpreteer_wijzigingen_batch(["Anouk na 12", "Anouk na 12"])
        assert result is not None
        assert fake_client.messages.create.call_count == 1


class TestInterpreteerWijzigingen:
    def test_succes(self):
        batch_result = {"Naar 12-18": {"tijdvervang": ["12:00", "18:00"]}}
        with patch.object(cs, "interpreteer_wijzigingen_batch", return_value=batch_result):
            result = interpreteer_wijzigingen("Naar 12-18")
        assert result is not None

    def test_api_fout_geeft_none(self):
        with patch.object(cs, "interpreteer_wijzigingen_batch", return_value=None):
            result = interpreteer_wijzigingen("Naar 12-18")
        assert result is None


class TestMatchMonsternemeNaam:
    def test_lege_lijst(self):
        result = match_monsternemer_naam("Jan de Vries", [])
        assert result is None

    def test_succes_exacte_match(self):
        bekenden = ["Jan de Vries", "Piet Smit"]
        fake_client = _maak_client("Jan de Vries")
        with patch.object(cs, "_get_client", return_value=fake_client):
            result = match_monsternemer_naam("Jan vd Vries", bekenden)
        assert result == "Jan de Vries"

    def test_geen_match(self):
        bekenden = ["Piet Smit", "An Janssen"]
        fake_client = _maak_client("GEEN")
        with patch.object(cs, "_get_client", return_value=fake_client):
            result = match_monsternemer_naam("Totaal Anders", bekenden)
        assert result is None

    def test_niet_in_lijst(self):
        bekenden = ["Piet Smit"]
        fake_client = _maak_client("Onbekende Naam")  # Niet in bekenden
        with patch.object(cs, "_get_client", return_value=fake_client):
            result = match_monsternemer_naam("Jan Klaasen", bekenden)
        assert result is None

    def test_api_fout_geeft_none(self):
        with patch.object(cs, "_get_client", side_effect=Exception("network")):
            result = match_monsternemer_naam("Jan", ["Jan de Vries"])
        assert result is None


class TestMatchNaamMendrix:
    def _mock_claude(self, tekst: str):
        blok = MagicMock()
        blok.type = "text"
        blok.text = tekst
        msg = MagicMock()
        msg.content = [blok]
        client = MagicMock()
        client.messages.create.return_value = msg
        return client

    def test_lege_kandidaten(self):
        from ap06_planner.services.claude_service import match_naam_mendrix
        assert match_naam_mendrix("Jan", []) is None

    def test_exacte_match(self):
        from ap06_planner.services.claude_service import match_naam_mendrix
        kandidaten = ["AP06/ONAFH - Kathleen Bouvier", "AP06 - Susan Curma"]
        with patch.object(cs, "_get_client", return_value=self._mock_claude("AP06/ONAFH - Kathleen Bouvier")):
            result = match_naam_mendrix("Kathleen Bouvier", kandidaten)
        assert result == "AP06/ONAFH - Kathleen Bouvier"

    def test_geen_match(self):
        from ap06_planner.services.claude_service import match_naam_mendrix
        with patch.object(cs, "_get_client", return_value=self._mock_claude("GEEN")):
            result = match_naam_mendrix("Onbekend Iemand", ["AP06 - Jan Jansen"])
        assert result is None

    def test_tolerante_match(self):
        from ap06_planner.services.claude_service import match_naam_mendrix
        kandidaten = ["AP06/ONAFH - Kathleen Bouvier"]
        # Claude geeft iets terug dat niet exact matcht maar wel substring is
        with patch.object(cs, "_get_client", return_value=self._mock_claude("Kathleen Bouvier")):
            result = match_naam_mendrix("Kathleen Bouvier", kandidaten)
        assert result == "AP06/ONAFH - Kathleen Bouvier"

    def test_geen_tolerante_match(self):
        from ap06_planner.services.claude_service import match_naam_mendrix
        kandidaten = ["AP06/ONAFH - Kathleen Bouvier"]
        # Claude geeft iets terug dat niet in de lijst zit en ook geen substring is
        with patch.object(cs, "_get_client", return_value=self._mock_claude("Totaal Anders XYZ")):
            result = match_naam_mendrix("Jan", kandidaten)
        assert result is None

    def test_api_fout_geeft_none(self):
        from ap06_planner.services.claude_service import match_naam_mendrix
        with patch.object(cs, "_get_client", side_effect=Exception("netwerk")):
            result = match_naam_mendrix("Jan", ["AP06 - Jan Jansen"])
        assert result is None
