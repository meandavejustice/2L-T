"""Japan-side exporters that ship engines to the USA.

The deepest 2L-T supply is Japanese: Yahoo Auctions JP (via the Buyee proxy),
BE FORWARD's parts arm, and Croooober (Up Garage's export storefront). Same
generic link-extraction as the domestic shops — engine codes are Latin even
in Japanese titles — with listings flagged is_import so the digest keeps them
in their own section.
"""

from __future__ import annotations

from ..models import Listing, SourceHealth
from . import jdm_sites


def scan(sites: list[dict]) -> tuple[list[Listing], list[SourceHealth]]:
    listings, health = jdm_sites.scan(sites)
    for l in listings:
        l.is_import = True
    return listings, health
