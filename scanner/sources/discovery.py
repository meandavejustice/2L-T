"""Wide-net web discovery.

Replaces Google Programmable Search: Google closed the Custom Search JSON
API to new customers (full shutdown 2027-01-01), so new projects get a
permanent 403. Instead:

- Brave Search API when BRAVE_API_KEY is set (free tier: 2,000 queries/mo,
  we use ~4/day) — most robust.
- DuckDuckGo's static HTML endpoint otherwise — keyless, zero setup.
"""

from __future__ import annotations

import os
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from bs4 import BeautifulSoup

from ..models import Listing, SourceHealth
from . import http

SOURCE = "Web discovery"


def _brave(queries: list[str], key: str) -> list[Listing]:
    import requests
    out: dict[str, Listing] = {}
    for q in queries:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": q, "count": 20, "country": "us"},
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
            timeout=25,
        )
        resp.raise_for_status()
        for item in resp.json().get("web", {}).get("results", []):
            url = item.get("url", "")
            lid = f"web:{url}"
            if url and lid not in out:
                out[lid] = Listing(
                    id=lid, source=SOURCE,
                    title=(item.get("title") or "")[:200], url=url,
                    description=(item.get("description") or "")[:400],
                )
    return list(out.values())


def _ddg_url(href: str) -> str:
    """DDG result hrefs are often redirect links carrying uddg=<real url>."""
    if "uddg=" in href:
        qs = parse_qs(urlparse(href).query)
        if qs.get("uddg"):
            return unquote(qs["uddg"][0])
    return href


def _duckduckgo(queries: list[str]) -> list[Listing]:
    out: dict[str, Listing] = {}
    for q in queries:
        resp = http.get(f"https://html.duckduckgo.com/html/?q={quote_plus(q)}",
                        delay=2.0)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a.result__a"):
            url = _ddg_url(a.get("href", ""))
            title = a.get_text(" ", strip=True)
            if not url.startswith("http") or not title:
                continue
            snippet_el = a.find_parent(class_="result__body")
            snippet = ""
            if snippet_el:
                sn = snippet_el.select_one(".result__snippet")
                snippet = sn.get_text(" ", strip=True)[:400] if sn else ""
            lid = f"web:{url}"
            if lid not in out:
                out[lid] = Listing(id=lid, source=SOURCE, title=title[:200],
                                   url=url, description=snippet)
    return list(out.values())


def scan(config: dict) -> tuple[list[Listing], SourceHealth]:
    queries = config.get("queries", [])
    try:
        key = os.environ.get("BRAVE_API_KEY")
        if key:
            listings = _brave(queries, key)
            note = "via Brave Search API"
        else:
            listings = _duckduckgo(queries)
            note = "via DuckDuckGo (keyless; set BRAVE_API_KEY for the Brave API)"
        return listings, SourceHealth(SOURCE, True, len(listings), note)
    except Exception as e:
        return [], SourceHealth(SOURCE, False, 0, f"{type(e).__name__}: {e}")
