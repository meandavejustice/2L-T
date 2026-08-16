"""Row52 — inventory of Pick-n-Pull self-serve junkyards.

A 1980s diesel Toyota Pickup landing in a self-serve yard is a complete
engine for scrap-plus-labor money. Yard rows don't say "diesel", but the
VIN does: L-series diesel Pickups/4Runners carry LN chassis codes
(JT4LN5../LN6../LN10.. VIN prefixes), so rows are kept only when an LN
marker appears near the vehicle link.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..models import Listing, SourceHealth
from . import http

SOURCE = "Row52 (Pick-n-Pull yards)"

_URLS = [
    "https://www.row52.com/Search/?YMMorVin=YMM&Make=Toyota&Model=Pickup",
    "https://www.row52.com/Search/?YMMorVin=YMM&Make=Toyota&Model=Pick-Up",
]

_VEHICLE_RE = re.compile(r"\b(19[78]\d|199[0-7])\s+Toyota\s+(Pick[- ]?up|4Runner|Hilux)", re.I)
_LN_RE = re.compile(r"\bJT\d?LN|\bLN\d{2,3}\b", re.I)


def scan() -> tuple[list[Listing], SourceHealth]:
    out: dict[str, Listing] = {}
    reached, last_err = False, ""
    for url in _URLS:
        try:
            resp = http.get(url, delay=1.5)
            reached = True
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text(" ", strip=True)
                if not _VEHICLE_RE.search(text):
                    continue
                block = a.find_parent(["tr", "li", "div"])
                context = block.get_text(" ", strip=True)[:500] if block else text
                if not _LN_RE.search(context):
                    continue  # gas truck (RN/VZN chassis) — not an L-series
                href = a["href"]
                full = href if href.startswith("http") else f"https://www.row52.com{href}"
                lid = f"row52:{full}"
                out.setdefault(lid, Listing(
                    id=lid, source=SOURCE, title=f"JUNKYARD: {text}"[:200],
                    url=full, description=("LN-chassis (L-series diesel) at a "
                                           "self-serve yard — complete engine at "
                                           "scrap prices if you pull it. " + context[:250]),
                ))
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
    if reached:
        return list(out.values()), SourceHealth(
            SOURCE, True, len(out),
            "LN-VIN (diesel chassis) rows only" if out else
            "reachable; no LN-chassis Toyotas in yards today")
    return [], SourceHealth(SOURCE, False, 0, last_err or "unreachable")
