"""Auto-translate non-English listing text for display.

Uses the keyless translate.googleapis.com gtx endpoint (no account needed).
Translation is display-only — classification always runs on the original
text, which the classifier already understands. Failures degrade to showing
the original title.
"""

from __future__ import annotations

import re
import time

import requests

from .sources.http import USER_AGENT

_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


def needs_translation(text: str) -> bool:
    return bool(_CJK.search(text or ""))


def translate(text: str, dest: str = "en") -> str:
    """Return the translation, or "" on any failure."""
    try:
        time.sleep(0.15)
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": dest,
                    "dt": "t", "q": text[:400]},
            headers={"User-Agent": USER_AGENT}, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
    except Exception:
        return ""
