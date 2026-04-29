from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


def _credentials_from_config(config: dict[str, Any]):
    from google.oauth2 import service_account

    info_json = (config.get("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    if info_json:
        info = json.loads(info_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    credentials_path = (config.get("GOOGLE_SERVICE_ACCOUNT_FILE") or "").strip()
    if credentials_path.startswith("{"):
        info = json.loads(credentials_path)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    if credentials_path:
        return service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)

    return None


def _sheet_exists(service, spreadsheet_id: str, worksheet_name: str) -> bool:
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = metadata.get("sheets") or []
    return any((sheet.get("properties") or {}).get("title") == worksheet_name for sheet in sheets)


def _ensure_sheet(service, spreadsheet_id: str, worksheet_name: str) -> None:
    if _sheet_exists(service, spreadsheet_id, worksheet_name):
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": worksheet_name,
                        }
                    }
                }
            ]
        },
    ).execute()


def sync_csv_to_google_sheet(
    *,
    csv_path: Path,
    spreadsheet_id: str,
    worksheet_name: str,
    config: dict[str, Any],
) -> bool:
    credentials = _credentials_from_config(config)
    if credentials is None or not spreadsheet_id:
        return False

    from googleapiclient.discovery import build

    with csv_path.open(newline="", encoding="utf-8") as csvfile:
        values = list(csv.reader(csvfile))

    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    _ensure_sheet(service, spreadsheet_id, worksheet_name)
    target_range = f"{worksheet_name}!A:ZZ"

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=target_range,
        body={},
    ).execute()

    if values:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{worksheet_name}!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()

    return True
