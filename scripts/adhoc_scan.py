"""Ad-hoc one-off engine scan — results go to stdout only.

Usage: python -m scripts.adhoc_scan
No email, no state writes, no board — purely a console report for a code
other than the 2L-T (currently: 1HZ).
"""

from __future__ import annotations

import re

from scanner.sources import craigslist, discovery, ebay, jdm_sites

CODE_RE = re.compile(r"\b1\s?hz\b", re.I)

EBAY_QUERIES = ["toyota 1hz engine", "1hz diesel engine",
                "land cruiser 1hz engine", "toyota 4.2 diesel engine"]
CL_QUERIES = ["toyota 1hz", "1hz engine", "land cruiser diesel engine"]
CL_CITIES = ["losangeles", "sfbay", "sandiego", "sacramento", "seattle",
             "portland", "spokane", "boise", "phoenix", "tucson", "denver",
             "saltlakecity", "albuquerque", "lasvegas", "dallas", "houston",
             "austin", "atlanta", "miami", "chicago", "minneapolis",
             "newyork", "newjersey", "philadelphia", "boston",
             "washingtondc", "charlotte", "nashville"]
SHOPS = [
    {"name": n, "urls": [f"{base}1HZ"]}
    for n, base in [
        ("JDM Engine Depot (NJ)", "https://jdmenginedepot.com/?s="),
        ("JDM Engine Zone", "https://jdmenginezone.com/search?q="),
        ("JDM Racing Motors", "https://www.jdmracingmotors.com/search?q="),
        ("JDM of San Diego", "https://jdmofsandiego.com/?s="),
        ("JDM Engine World (Queens NY)", "https://jdmengineworld.com/?s="),
        ("JDM New York", "https://www.jdmnewyork.com/?s="),
        ("JDM Orlando", "https://www.jdmorlandoinc.com/?s="),
        ("Foreign Engines (WA)", "https://www.foreignengines.com/search?q="),
        ("Engine World (TX)", "https://www.engineworldinc.com/?s="),
    ]
]
DISCOVERY_QUERIES = ["toyota 1hz engine for sale", "1hz engine for sale usa",
                     "land cruiser 1hz diesel engine for sale"]


def main() -> None:
    found = []

    listings, healths = ebay.scan({"queries": EBAY_QUERIES})
    found.extend(listings)
    for h in healths:
        print(f"[health] {h.source}: {'OK' if h.ok else 'FAIL'} {h.found} — {h.note}")

    listings, h = craigslist.scan({"queries": CL_QUERIES, "cities": CL_CITIES})
    found.extend(listings)
    print(f"[health] {h.source}: {'OK' if h.ok else 'FAIL'} {h.found} — {h.note}")

    listings, healths = jdm_sites.scan(SHOPS)
    found.extend(listings)
    for h in healths:
        print(f"[health] {h.source}: {'OK' if h.ok else 'FAIL'} {h.found} — {h.note}")

    listings, h = discovery.scan({"queries": DISCOVERY_QUERIES})
    found.extend(listings)
    print(f"[health] {h.source}: {'OK' if h.ok else 'FAIL'} {h.found} — {h.note}")

    hits, seen = [], set()
    for l in found:
        if l.url in seen:
            continue
        seen.add(l.url)
        if CODE_RE.search(l.text()):
            hits.append(l)

    print(f"\n===== 1HZ HITS: {len(hits)} =====")
    for l in hits:
        imp = " [SHIPS-TO-US]" if l.is_import else ""
        print(f"\n- {l.title[:120]}{imp}")
        print(f"  {l.price or 'no price'} | {l.location or 'no location'} | {l.source}")
        print(f"  {l.url}")
        if l.description:
            print(f"  {l.description[:160]}")


if __name__ == "__main__":
    main()
