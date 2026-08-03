"""eBay source.

Prefers the official Browse API when EBAY_CLIENT_ID / EBAY_CLIENT_SECRET are
set (free developer keys, immune to bot-blocking). Falls back to scraping the
public search pages with two parsing strategies, since eBay reshuffles its
result markup periodically.
"""

from __future__ import annotations

import os
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..models import Listing, SourceHealth
from . import http

SOURCE = "eBay"
_ITM_RE = re.compile(r"ebay\.com/itm/(?:[^/]+/)?(\d+)")
_PRICE_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")


def _api_token(client_id: str, client_secret: str) -> str:
    import requests
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials",
              "scope": "https://api.ebay.com/oauth/api_scope"},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# International marketplaces rich in 2L-Ts; searched with the same keys,
# restricted to items deliverable to the US, flagged as imports.
_INTL_MARKETPLACES = [
    ("EBAY_GB", "eBay UK"),
    ("EBAY_AU", "eBay Australia"),
    ("EBAY_CA", "eBay Canada"),
]

_CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "AUD": "AU$", "CAD": "CA$"}


def _search_api(queries: list[str], token: str, marketplace: str,
                item_filter: str, source: str) -> list[Listing]:
    import requests
    headers = {"Authorization": f"Bearer {token}",
               "X-EBAY-C-MARKETPLACE-ID": marketplace}
    out: dict[str, Listing] = {}
    for q in queries:
        resp = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            params={"q": q, "limit": "50", "filter": item_filter},
            headers=headers, timeout=25,
        )
        resp.raise_for_status()
        for item in resp.json().get("itemSummaries", []):
            lid = f"ebay:{item['itemId']}"
            price = item.get("price", {})
            loc = item.get("itemLocation", {})
            sym = _CURRENCY_SYMBOLS.get(price.get("currency", "USD"), "$")
            out[lid] = Listing(
                id=lid, source=source,
                title=item.get("title", ""),
                url=item.get("itemWebUrl", ""),
                price=f"{sym}{price['value']}" if price.get("value") else "",
                location=", ".join(filter(None, [loc.get("city"), loc.get("stateOrProvince"),
                                                 loc.get("country")])),
                description=item.get("shortDescription", "") or "",
                image=item.get("image", {}).get("imageUrl", ""),
            )
    return list(out.values())


def _parse_cards(soup: BeautifulSoup) -> list[Listing]:
    """Classic li.s-item result cards."""
    out = []
    for card in soup.select("li.s-item, div.s-item"):
        link = card.select_one("a.s-item__link") or card.select_one("a[href*='/itm/']")
        title_el = card.select_one(".s-item__title")
        if not link or not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        if not title or title.lower().startswith("shop on ebay"):
            continue
        m = _ITM_RE.search(link.get("href", ""))
        if not m:
            continue
        price_el = card.select_one(".s-item__price")
        loc_el = card.select_one(".s-item__location, .s-item__itemLocation")
        img = card.select_one("img")
        out.append(Listing(
            id=f"ebay:{m.group(1)}", source=SOURCE, title=title,
            url=f"https://www.ebay.com/itm/{m.group(1)}",
            price=price_el.get_text(strip=True) if price_el else "",
            location=(loc_el.get_text(strip=True).replace("from ", "") if loc_el else ""),
            image=img.get("src", "") if img else "",
        ))
    return out


def _parse_anchors(soup: BeautifulSoup) -> list[Listing]:
    """Layout-agnostic fallback: any /itm/ anchor with usable text."""
    out = {}
    for a in soup.find_all("a", href=True):
        m = _ITM_RE.search(a["href"])
        if not m:
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 15:  # icon/thumbnail links
            continue
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        price_m = _PRICE_RE.search(parent_text) or _PRICE_RE.search(title)
        lid = f"ebay:{m.group(1)}"
        if lid not in out:
            out[lid] = Listing(
                id=lid, source=SOURCE, title=title[:200],
                url=f"https://www.ebay.com/itm/{m.group(1)}",
                price=price_m.group(0) if price_m else "",
            )
    return list(out.values())


def _search_scrape(queries: list[str]) -> list[Listing]:
    out: dict[str, Listing] = {}
    for q in queries:
        # LH_PrefLoc=1 restricts to items located in the US.
        url = (f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(q)}"
               f"&_sop=10&_ipg=60&LH_PrefLoc=1")
        resp = http.get(url, delay=1.5)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = _parse_cards(soup)
        if len(cards) < 2:
            cards = _parse_anchors(soup)
        for l in cards:
            out.setdefault(l.id, l)
    return list(out.values())


def scan(config: dict) -> tuple[list[Listing], list[SourceHealth]]:
    queries = config.get("queries", [])
    listings: dict[str, Listing] = {}
    health: list[SourceHealth] = []

    if not (os.environ.get("EBAY_CLIENT_ID") and os.environ.get("EBAY_CLIENT_SECRET")):
        try:
            found = _search_scrape(queries)
            return found, [SourceHealth(SOURCE, True, len(found),
                                        "via page scrape (set EBAY_CLIENT_ID/SECRET "
                                        "for the official API + intl marketplaces)")]
        except Exception as e:
            return [], [SourceHealth(SOURCE, False, 0, f"{type(e).__name__}: {e}")]

    try:
        token = _api_token(os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"])
    except Exception as e:
        return [], [SourceHealth(SOURCE, False, 0, f"auth failed: {e}")]

    try:
        found = _search_api(queries, token, "EBAY_US",
                            "itemLocationCountry:US", "eBay US")
        for l in found:
            listings.setdefault(l.id, l)
        health.append(SourceHealth("eBay US", True, len(found),
                                   "via official Browse API"))
    except Exception as e:
        health.append(SourceHealth("eBay US", False, 0, f"{type(e).__name__}: {e}"))

    for marketplace, name in _INTL_MARKETPLACES:
        try:
            found = _search_api(queries, token, marketplace,
                                "deliveryCountry:US", name)
            for l in found:
                l.is_import = True
                listings.setdefault(l.id, l)
            health.append(SourceHealth(name, True, len(found), "ships to USA"))
        except Exception as e:
            health.append(SourceHealth(name, False, 0, f"{type(e).__name__}: {e}"))

    return list(listings.values()), health
