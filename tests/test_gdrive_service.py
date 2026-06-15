"""Tests voor gdrive_service.py."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from ap06_planner.services.gdrive_service import (
    RETENTIE_DAGEN,
    _ruim_oude_bestanden_op,
    upload_xlsx,
    verkort_url,
)


# ---------------------------------------------------------------------------
# verkort_url — anonieme fallback (geen token)
# ---------------------------------------------------------------------------


def test_verkort_url_anoniem_succes(monkeypatch):
    monkeypatch.delenv("TINYURL_API_TOKEN", raising=False)
    mock_resp = MagicMock()
    mock_resp.text = "https://tinyurl.com/abc123"
    with patch("ap06_planner.services.gdrive_service.requests.get", return_value=mock_resp):
        result = verkort_url("https://drive.google.com/file/d/xyz/view")
    assert result == "https://tinyurl.com/abc123"


def test_verkort_url_anoniem_geen_http_respons(monkeypatch):
    monkeypatch.delenv("TINYURL_API_TOKEN", raising=False)
    mock_resp = MagicMock()
    mock_resp.text = "Error: invalid url"
    with patch("ap06_planner.services.gdrive_service.requests.get", return_value=mock_resp):
        result = verkort_url("https://drive.google.com/file/d/xyz/view")
    assert result == "https://drive.google.com/file/d/xyz/view"


def test_verkort_url_anoniem_request_fout(monkeypatch):
    import requests as req_mod
    monkeypatch.delenv("TINYURL_API_TOKEN", raising=False)
    with patch(
        "ap06_planner.services.gdrive_service.requests.get",
        side_effect=req_mod.RequestException("timeout"),
    ):
        result = verkort_url("https://drive.google.com/file/d/xyz/view")
    assert result == "https://drive.google.com/file/d/xyz/view"


# ---------------------------------------------------------------------------
# verkort_url — met API token (Bearer auth)
# ---------------------------------------------------------------------------


def test_verkort_url_met_token_succes(monkeypatch):
    monkeypatch.setenv("TINYURL_API_TOKEN", "mijn-token")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"tiny_url": "https://tinyurl.com/kort99"}}
    with patch("ap06_planner.services.gdrive_service.requests.post", return_value=mock_resp):
        result = verkort_url("https://drive.google.com/file/d/xyz/view")
    assert result == "https://tinyurl.com/kort99"


def test_verkort_url_met_token_leeg_antwoord(monkeypatch):
    monkeypatch.setenv("TINYURL_API_TOKEN", "mijn-token")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {}}
    with patch("ap06_planner.services.gdrive_service.requests.post", return_value=mock_resp):
        result = verkort_url("https://drive.google.com/file/d/xyz/view")
    assert result == "https://drive.google.com/file/d/xyz/view"


def test_verkort_url_met_token_api_fout(monkeypatch):
    import requests as req_mod
    monkeypatch.setenv("TINYURL_API_TOKEN", "mijn-token")
    with patch(
        "ap06_planner.services.gdrive_service.requests.post",
        side_effect=req_mod.RequestException("401 Unauthorized"),
    ):
        result = verkort_url("https://drive.google.com/file/d/xyz/view")
    assert result == "https://drive.google.com/file/d/xyz/view"


def test_verkort_url_bearer_header_correct(monkeypatch):
    monkeypatch.setenv("TINYURL_API_TOKEN", "test-bearer-token")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"tiny_url": "https://tinyurl.com/x"}}
    with patch("ap06_planner.services.gdrive_service.requests.post", return_value=mock_resp) as mock_post:
        verkort_url("https://example.com/lang")
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-bearer-token"


# ---------------------------------------------------------------------------
# upload_xlsx — configuratiefouten
# ---------------------------------------------------------------------------


def test_upload_xlsx_geen_folder_id_en_credentials(monkeypatch):
    monkeypatch.delenv("GDRIVE_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("GDRIVE_FOLDER_ID", raising=False)
    succes, url, fout = upload_xlsx(b"data", "test.xlsx")
    assert not succes
    assert url == ""
    assert "GDRIVE_FOLDER_ID" in fout  # folder_id wordt als eerste gecheckt


def test_upload_xlsx_geen_credentials(monkeypatch):
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "folder123")
    monkeypatch.delenv("GDRIVE_CREDENTIALS_JSON", raising=False)
    succes, url, fout = upload_xlsx(b"data", "test.xlsx")
    assert not succes
    assert url == ""
    assert "GDRIVE_CREDENTIALS_JSON" in fout


def test_upload_xlsx_geen_folder_id(monkeypatch):
    monkeypatch.setenv("GDRIVE_CREDENTIALS_JSON", "credentials/test.json")
    monkeypatch.delenv("GDRIVE_FOLDER_ID", raising=False)
    succes, url, fout = upload_xlsx(b"data", "test.xlsx")
    assert not succes
    assert "GDRIVE_FOLDER_ID" in fout


# ---------------------------------------------------------------------------
# upload_xlsx — gesimuleerde Drive API
# ---------------------------------------------------------------------------


def _mock_drive_service(file_id="abc123", short_url="https://tinyurl.com/xyz"):
    """Bouw een volledig gemockte Drive service."""
    mock_service = MagicMock()
    mock_service.files().create().execute.return_value = {"id": file_id}
    return mock_service


def test_upload_xlsx_succes(monkeypatch, tmp_path):
    creds_pad = tmp_path / "creds.json"
    creds_pad.write_text("{}")
    monkeypatch.setenv("GDRIVE_CREDENTIALS_JSON", str(creds_pad))
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "folder123")

    mock_service = _mock_drive_service(file_id="bestand456")
    mock_resp = MagicMock()
    mock_resp.text = "https://tinyurl.com/kort"

    with (
        patch("ap06_planner.services.gdrive_service._drive_service", return_value=mock_service),
        patch("ap06_planner.services.gdrive_service.requests.get", return_value=mock_resp),
    ):
        succes, url, fout = upload_xlsx(b"xlsx inhoud", "planning.xlsx")

    assert succes
    assert url == "https://tinyurl.com/kort"
    assert fout == ""


def test_upload_xlsx_drive_fout(monkeypatch, tmp_path):
    creds_pad = tmp_path / "creds.json"
    creds_pad.write_text("{}")
    monkeypatch.setenv("GDRIVE_CREDENTIALS_JSON", str(creds_pad))
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "folder123")

    with patch(
        "ap06_planner.services.gdrive_service._drive_service",
        side_effect=Exception("Drive API onbereikbaar"),
    ):
        succes, url, fout = upload_xlsx(b"data", "test.xlsx")

    assert not succes
    assert url == ""
    assert "Drive API onbereikbaar" in fout


# ---------------------------------------------------------------------------
# _ruim_oude_bestanden_op
# ---------------------------------------------------------------------------


def _oud_bestand(file_id: str, naam: str, dagen_geleden: int) -> dict:
    aangemaakt = datetime.now(tz=timezone.utc) - timedelta(days=dagen_geleden)
    return {"id": file_id, "name": naam, "createdTime": aangemaakt.strftime("%Y-%m-%dT%H:%M:%SZ")}


def test_ruim_op_verwijdert_oude_bestanden():
    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {
        "files": [_oud_bestand("id1", "oud.xlsx", RETENTIE_DAGEN + 1)]
    }

    _ruim_oude_bestanden_op(mock_service, "folder123")

    mock_service.files().delete.assert_called_once_with(fileId="id1")
    mock_service.files().delete().execute.assert_called_once()


def test_ruim_op_laat_nieuwe_bestanden():
    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {"files": []}

    _ruim_oude_bestanden_op(mock_service, "folder123")

    mock_service.files().delete.assert_not_called()


def test_ruim_op_gaat_door_bij_verwijderfout():
    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _oud_bestand("id1", "oud1.xlsx", RETENTIE_DAGEN + 5),
            _oud_bestand("id2", "oud2.xlsx", RETENTIE_DAGEN + 2),
        ]
    }
    mock_service.files().delete().execute.side_effect = [Exception("fout"), None]

    # Mag geen exception gooien
    _ruim_oude_bestanden_op(mock_service, "folder123")


def test_ruim_op_bij_list_fout():
    mock_service = MagicMock()
    mock_service.files().list().execute.side_effect = Exception("netwerk fout")

    # Mag geen exception gooien
    _ruim_oude_bestanden_op(mock_service, "folder123")
