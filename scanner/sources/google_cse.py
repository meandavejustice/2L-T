"""Optional wide-net discovery via Google Programmable Search (CSE).

Catches sources we don't scrape directly — forums (ih8mud, Marlin Crawler),
small importers, classifieds. Only runs when GOOGLE_API_KEY and GOOGLE_CSE_ID
are set; the free tier (100 queries/day) is far more than the daily run uses.
"""

from __future__ import annotations

import os

import requests

from ..models import Listing, SourceHealth

SOURCE = "Google discovery"


def scan(config: dict) -> tuple[list[Listing], SourceHealth]:
    key = os.environ.get("GOOGLE_API_KEY")
    cse = os.environ.get("GOOGLE_CSE_ID")
    if not key or not cse:
        return [], SourceHealth(SOURCE, True, 0,
                                "disabled (set GOOGLE_API_KEY + GOOGLE_CSE_ID to enable)")
    out: dict[str, Listing] = {}
    try:
        for q in config.get("queries", []):
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": key, "cx": cse, "q": q, "num": 10, "gl": "us"},
                timeout=25,
            )
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                url = item.get("link", "")
                lid = f"google:{url}"
                if url and lid not in out:
                    out[lid] = Listing(
                        id=lid, source=SOURCE,
                        title=item.get("title", "")[:200], url=url,
                        description=item.get("snippet", "")[:400],
                    )
        return list(out.values()), SourceHealth(SOURCE, True, len(out), "")
    except Exception as e:
        return list(out.values()), SourceHealth(SOURCE, False, len(out),
                                                f"{type(e).__name__}: {e}")
