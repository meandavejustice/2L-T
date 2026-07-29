"""Japan-side exporters that ship engines to the USA.

The deepest 2L-T supply is Japanese: Yahoo Auctions JP (via the Buyee proxy),
BE FORWARD's parts arm, and Croooober (Up Garage's export storefront). Same
generic link-extraction as the domestic shops — engine codes are Latin even
in Japanese titles — with listings flagged is_import so the digest keeps them
in their own section.
"""

from __future__ import annotations

import re

from ..models import Listing, SourceHealth
from . import jdm_sites

# Buyee's own search bot-blocks CI, but its item pages share Yahoo's auction
# IDs — so we scrape Yahoo Auctions JP directly (server-rendered, reachable
# from abroad) and rewrite result links into one-click Buyee purchase links.
_YAHOO_AUCTION_RE = re.compile(
    r"(?:page|auctions)\.auctions\.yahoo\.co\.jp/jp/auction/(\w+)", re.I)


def scan(sites: list[dict]) -> tuple[list[Listing], list[SourceHealth]]:
    listings, health = jdm_sites.scan(sites)
    for l in listings:
        l.is_import = True
        m = _YAHOO_AUCTION_RE.search(l.url)
        if m:
            l.url = f"https://buyee.jp/item/yahoo/auction/{m.group(1)}"
            l.id = f"jdm:{l.url}"
    return listings, health
