"""
Sentiment Filter — blocks toxic/offensive messages before they reach the AI.

Strategy (cost-effective):
  1. Fast keyword blocklist — no API cost at all
  2. 3-strikes system: warn → warn → mute
"""
import re
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"

# Toxic keyword patterns (extend as needed)
BAD_KEYWORDS = [
    r"\bstupid\b", r"\bidiot\b", r"\bfool\b", r"\bdumb\b", r"\bmoron\b",
    r"\bshut up\b", r"\bscam\b", r"\bfraud\b", r"\bwaste\b", r"\bbastard\b",
    r"\bfuck\b", r"\bshit\b", r"\bass\b", r"\bdick\b", r"\bbitch\b",
    r"\bcrap\b", r"\bworthless\b", r"\buseless\b", r"\bterrible\b", r"\bawful\b",
    # Add Burmese/Myanmar bad words if needed
]

BAD_PATTERN = re.compile("|".join(BAD_KEYWORDS), re.IGNORECASE)


def _load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"registered_users": {}}


def _save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_toxic(text: str) -> bool:
    """Returns True if the message contains toxic/offensive content."""
    return bool(BAD_PATTERN.search(text))


def record_strike(user_id: int) -> int:
    """
    Increment strike count for a user.
    Returns total strikes so far.
    """
    data = _load_data()
    users = data.get("registered_users", {})
    uid = str(user_id)

    if uid not in users:
        users[uid] = {}

    users[uid]["strikes"] = users[uid].get("strikes", 0) + 1
    data["registered_users"] = users
    _save_data(data)
    return users[uid]["strikes"]


def is_muted(user_id: int) -> bool:
    """Returns True if user has 3+ strikes (muted)."""
    data = _load_data()
    uid = str(user_id)
    user = data.get("registered_users", {}).get(uid, {})
    return user.get("strikes", 0) >= 3


def reset_strikes(user_id: int):
    """Admin can reset a user's strikes."""
    data = _load_data()
    uid = str(user_id)
    if uid in data.get("registered_users", {}):
        data["registered_users"][uid]["strikes"] = 0
        _save_data(data)
