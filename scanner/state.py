"""Persistent seen-listing state, committed back to the repo by the workflow
so "new since yesterday" survives between daily runs."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta

STATE_PATH = os.path.join("data", "seen_listings.json")
EXPIRE_DAYS = 180  # forget listings not seen for this long


def load() -> dict:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(state: dict) -> None:
    cutoff = (date.today() - timedelta(days=EXPIRE_DAYS)).isoformat()
    state = {k: v for k, v in state.items() if v.get("last_seen", "") >= cutoff}
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)


def mark(state: dict, listings: list) -> tuple[list, list]:
    """Update state with today's listings; return (new, previously_seen)."""
    today = date.today().isoformat()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    new, seen = [], []
    for l in listings:
        entry = state.get(l.id)
        if entry is None:
            state[l.id] = {"first_seen": today, "last_seen": today,
                           "title": l.title, "url": l.url, "recorded_at": now}
            new.append(l)
        else:
            entry["last_seen"] = today
            seen.append(l)
    return new, seen
