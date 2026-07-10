"""Craigslist source.

Craigslist has no national search, so we sweep major metros. The search pages
are JS-rendered, but Craigslist serves a static SEO fallback
(`li.cl-static-search-result`) that carries title, link, and price — enough
for the digest, and the link goes straight to the full ad.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..models import Listing, SourceHealth
from . import http

SOURCE = "Craigslist"


def _parse(html: str, city: str) -> list[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for li in soup.select("li.cl-static-search-result"):
        a = li.find("a", href=True)
        title_el = li.select_one("div.title") or a
        if not a or not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        if not title:
            continue
        price_el = li.select_one("div.price")
        loc_el = li.select_one("div.location")
        url = a["href"]
        out.append(Listing(
            id=f"craigslist:{url.rstrip('/').rsplit('/', 1)[-1]}",
            source=SOURCE, title=title, url=url,
            price=price_el.get_text(strip=True) if price_el else "",
            location=(loc_el.get_text(strip=True) if loc_el else city),
        ))
    return out


def scan(config: dict) -> tuple[list[Listing], SourceHealth]:
    cities = config.get("cities", [])
    queries = config.get("queries", [])
    out: dict[str, Listing] = {}
    errors = 0
    for city in cities:
        for q in queries:
            url = f"https://{city}.craigslist.org/search/sss?query={quote_plus(q)}"
            try:
                resp = http.get(url, delay=0.6)
                for l in _parse(resp.text, city):
                    out.setdefault(l.id, l)
            except Exception:
                errors += 1
    total = len(cities) * len(queries)
    ok = errors < total  # only report dead if literally everything failed
    note = f"{len(cities)} metros swept" + (f", {errors}/{total} requests failed" if errors else "")
    return list(out.values()), SourceHealth(SOURCE, ok, len(out), note)
