"""
Auth system — user registration via Google Form + Google Sheet verification.

Flow:
    1. User sends any message to bot
    2. Bot checks if user's Telegram ID is in data/users.json
    3. If not registered → send Google Form link
    4. User fills the form → admin syncs with /sync command
    5. Bot reads Google Sheet to verify registration
    6. Approved users are cached in data/users.json
"""
import json
from pathlib import Path
from googleapiclient.discovery import build
from config.settings import (
    GOOGLE_CREDENTIALS_JSON, GOOGLE_TOKEN_FILE,
    GOOGLE_SHEET_ID, GOOGLE_FORM_URL
)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"


def _load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"registered_users": {}}


def _save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_registered(user_id: int) -> bool:
    """Check if a Telegram user ID is registered."""
    data = _load_data()
    return str(user_id) in data.get("registered_users", {})


def register_user_locally(user_id: int, name: str, info: dict = None):
    """Manually add a user to the local registered list."""
    data = _load_data()
    data.setdefault("registered_users", {})[str(user_id)] = {
        "name": name,
        "strikes": 0,
        **(info or {}),
    }
    _save_data(data)


def sync_from_sheet() -> int:
    """
    Read the Google Sheet linked to the registration Form.
    Expects columns: Timestamp | Name | Email | Telegram Username | Telegram ID

    Returns number of new users synced.
    """
    if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID.startswith("your_"):
        return 0

    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(
            GOOGLE_TOKEN_FILE,
            ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="A2:E1000",  # Skip header row
        ).execute()

        rows = result.get("values", [])
        data = _load_data()
        new_count = 0

        for row in rows:
            if len(row) >= 5:
                # Columns: Timestamp, Name, Email, Telegram Username, Telegram ID
                name = row[1].strip() if len(row) > 1 else "Unknown"
                telegram_id = row[4].strip() if len(row) > 4 else ""

                if telegram_id and telegram_id.isdigit():
                    uid = str(telegram_id)
                    if uid not in data["registered_users"]:
                        data["registered_users"][uid] = {
                            "name": name,
                            "email": row[2].strip() if len(row) > 2 else "",
                            "strikes": 0,
                        }
                        new_count += 1

        _save_data(data)
        return new_count

    except Exception as e:
        print(f"[Auth] Sheet sync error: {e}")
        return 0
