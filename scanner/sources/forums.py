"""Toyota forum classifieds, watched via RSS.

XenForo/vBulletin forums publish RSS of new threads — the best window into
private-party sales (ih8mud etc.). Feed items go through the same relevance
filter and classifier as every other source, so ordinary tech threads that
don't look like 2L-family listings are dropped.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..models import Listing, SourceHealth
from . import http

_TAG_RE = re.compile(r"<[^>]+>")


def _parse_feed(content: bytes, source: str) -> list[Listing]:
    out: dict[str, Listing] = {}
    root = ET.fromstring(content)
    # RSS 2.0 <item>; Atom uses <entry> with namespaced children.
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = _TAG_RE.sub(" ", item.findtext("description") or "").strip()[:400]
        if title and link:
            lid = f"forum:{link}"
            out.setdefault(lid, Listing(id=lid, source=source, title=title[:200],
                                        url=link, description=desc))
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.iter(f"{ns}entry"):
        title = (entry.findtext(f"{ns}title") or "").strip()
        link_el = entry.find(f"{ns}link")
        link = (link_el.get("href") if link_el is not None else "").strip()
        if title and link:
            lid = f"forum:{link}"
            out.setdefault(lid, Listing(id=lid, source=source, title=title[:200],
                                        url=link))
    return list(out.values())


def scan(feeds: list[dict]) -> tuple[list[Listing], list[SourceHealth]]:
    listings: dict[str, Listing] = {}
    health: list[SourceHealth] = []
    for feed in feeds:
        name = feed["name"]
        found: dict[str, Listing] = {}
        reached, last_err = False, ""
        for url in feed.get("urls", []):
            try:
                resp = http.get(url, delay=1.0)
                for l in _parse_feed(resp.content, name):
                    found.setdefault(l.id, l)
                reached = True
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
        listings.update(found)
        if reached:
            health.append(SourceHealth(name, True, len(found),
                                       "feed read; 2L-T filter applies downstream"))
        else:
            health.append(SourceHealth(name, False, 0, last_err or "unreachable"))
    return list(listings.values()), health
