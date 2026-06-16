"""
gdrive_service.py — Google Drive integratie voor AP06 Planner.

Upload xlsx-bestanden naar een gedeelde Drive-map en verwijder bestanden
ouder dan RETENTIE_DAGEN automatisch bij elke upload.
"""

import logging
import os
from datetime import UTC, datetime, timedelta

import requests

_log = logging.getLogger("ap06.gdrive")

RETENTIE_DAGEN = 30
_SCOPES = ["https://www.googleapis.com/auth/drive"]


def verkort_url(url: str) -> str:
    """
    Verkort een URL via de TinyURL API.

    Gebruikt TINYURL_API_TOKEN (Bearer auth) als die ingesteld is,
    anders anonieme fallback via api-create.php.
    Bij elke fout wordt de originele URL teruggegeven.
    """
    api_token = os.getenv("TINYURL_API_TOKEN", "")
    try:
        if api_token:
            resp = requests.post(
                "https://api.tinyurl.com/create",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "domain": "tinyurl.com"},
                timeout=10,
            )
            resp.raise_for_status()
            kort = resp.json().get("data", {}).get("tiny_url", "")
        else:
            resp = requests.get(
                "https://tinyurl.com/api-create.php",
                params={"url": url},
                timeout=5,
            )
            resp.raise_for_status()
            kort = resp.text.strip()
        if kort.startswith("http"):
            _log.debug("URL verkort: %s → %s", url, kort)
            return kort
    except Exception as e:
        _log.warning("URL verkorten mislukt: %s", e, exc_info=True)
    return url


def _drive_service():
    """Maak een geauthenticeerde Drive API client via OAuth token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_pad = os.getenv("GDRIVE_TOKEN_JSON", "credentials/gdrive_token.json")
    if not os.path.exists(token_pad):
        raise ValueError(f"GDRIVE_TOKEN_JSON niet gevonden: {token_pad}")

    creds = Credentials.from_authorized_user_file(token_pad, _SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_pad, "w") as f:
            f.write(creds.to_json())
        _log.debug("OAuth token vernieuwd en opgeslagen in %s", token_pad)

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_xlsx(bestand_bytes: bytes, bestandsnaam: str) -> tuple[bool, str, str]:
    """
    Upload een xlsx-bestand naar de geconfigureerde Drive-map.

    Maakt het bestand publiek toegankelijk en verwijdert automatisch
    bestanden ouder dan RETENTIE_DAGEN uit dezelfde map.

    Returns (succes, publieke_url, foutmelding).
    Publieke_url is leeg bij mislukking.
    """
    folder_id = os.getenv("GDRIVE_FOLDER_ID", "")
    token_pad = os.getenv("GDRIVE_TOKEN_JSON", "credentials/gdrive_token.json")

    if not folder_id:
        return False, "", "GDRIVE_FOLDER_ID niet ingesteld"
    if not os.path.exists(token_pad):
        return False, "", f"GDRIVE_TOKEN_JSON niet gevonden: {token_pad}"

    try:
        from io import BytesIO

        from googleapiclient.http import MediaIoBaseUpload

        service = _drive_service()

        _ruim_oude_bestanden_op(service, folder_id)

        bestand_meta = {
            "name": bestandsnaam,
            "parents": [folder_id],
        }
        media = MediaIoBaseUpload(
            BytesIO(bestand_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=False,
        )
        bestand = (
            service.files()
            .create(
                body=bestand_meta,
                media_body=media,
                fields="id",
            )
            .execute()
        )

        file_id = bestand.get("id")

        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
        ).execute()
        _log.debug("Bestand publiek gemaakt: %s", file_id)

        url = verkort_url(f"https://drive.google.com/file/d/{file_id}/view")
        _log.info("xlsx geüpload naar Drive: %s (%s)", bestandsnaam, url)
        return True, url, ""

    except Exception as e:
        _log.warning("Drive upload mislukt voor '%s': %s", bestandsnaam, e, exc_info=True)
        return False, "", str(e)


def _ruim_oude_bestanden_op(service, folder_id: str) -> None:
    """Verwijder bestanden ouder dan RETENTIE_DAGEN uit de Drive-map."""
    grens = datetime.now(tz=UTC) - timedelta(days=RETENTIE_DAGEN)
    grens_str = grens.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        resultaat = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and createdTime < '{grens_str}' and trashed = false",
                fields="files(id, name, createdTime)",
            )
            .execute()
        )

        for bestand in resultaat.get("files", []):
            try:
                service.files().delete(fileId=bestand["id"]).execute()
                _log.info(
                    "Oud Drive-bestand verwijderd: %s (aangemaakt: %s)",
                    bestand["name"],
                    bestand["createdTime"],
                )
            except Exception as e:
                _log.warning("Verwijderen mislukt voor %s: %s", bestand["name"], e)

    except Exception as e:
        _log.warning("Opruimen oude Drive-bestanden mislukt: %s", e, exc_info=True)
