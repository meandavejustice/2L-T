"""Generic scraper for US JDM engine importer sites.

These sites run on assorted platforms (WooCommerce, Shopify, custom carts),
so rather than one brittle parser per site, each site lists candidate search
URLs in config.yaml and we extract any anchors whose text looks like a
2L-family diesel listing. Low-tech, but resilient to redesigns — and the
digest's health table shows which sites answered.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Listing, SourceHealth
from . import http

# Anchor text worth keeping: an explicit 2L-T/2L-TE code, or Toyota diesel-ish
# (Latin or Japanese — engine codes stay Latin in Japanese titles).
_CODE_RE = re.compile(r"2\s*L\s*[-–—]?\s*TE?\b", re.I)
_DIESEL_RE = re.compile(
    r"(toyota|hilux|surf|land\s*cruiser).{0,60}diesel|diesel.{0,60}(toyota|hilux)"
    r"|(トヨタ|ハイラックス|サーフ|ランクル).{0,30}ディーゼル|ディーゼル.{0,30}(トヨタ|ハイラックス)",
    re.I)
_PRICE_RE = re.compile(r"[\$¥]\s?[\d,]+(?:\.\d{2})?|[\d,]+\s?円")

_SKIP_HREF = re.compile(r"(/cart|/account|/login|#|mailto:|tel:|/tag/|/category/|/collections/?$)", re.I)


def _extract(html: str, base_url: str, site_name: str) -> list[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, Listing] = {}
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if not text or len(text) < 8 or len(text) > 250:
            continue
        if not (_CODE_RE.search(text) or _DIESEL_RE.search(text)):
            continue
        href = a["href"]
        if _SKIP_HREF.search(href):
            continue
        url = urljoin(base_url, href)
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        price_m = _PRICE_RE.search(parent_text)
        lid = f"jdm:{url}"
        if lid not in out:
            out[lid] = Listing(
                id=lid, source=site_name, title=text[:200], url=url,
                price=price_m.group(0) if price_m else "",
                description=parent_text[:400],
            )
    return list(out.values())


def scan(sites: list[dict]) -> tuple[list[Listing], list[SourceHealth]]:
    listings: dict[str, Listing] = {}
    health: list[SourceHealth] = []
    for site in sites:
        name = site["name"]
        found: dict[str, Listing] = {}
        last_err = ""
        reached = False
        for url in site.get("urls", []):
            try:
                resp = http.get(url, delay=1.8)
                reached = True
                for l in _extract(resp.text, url, name):
                    found.setdefault(l.id, l)
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
        listings.update(found)
        if reached:
            health.append(SourceHealth(name, True, len(found),
                                       "no 2L-T matches on site today" if not found else ""))
        else:
            health.append(SourceHealth(name, False, 0, last_err or "unreachable"))
    return list(listings.values()), health
