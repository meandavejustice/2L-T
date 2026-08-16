"""Daily 2L-T scan orchestrator.

Runs every source (a failing source never kills the run), filters and
classifies candidates, diffs against the persistent seen-state, writes
digest.html, and emails the digest.
"""

from __future__ import annotations

import os
import sys

import yaml

from . import classify, digest, emailer, state, translate
from .models import Listing
from .sources import (craigslist, discovery, ebay, forums, japan, jdm_sites,
                      row52)


def run() -> int:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    listings: dict[str, Listing] = {}
    health = []

    print("Scanning eBay (US + UK/AU/CA)…")
    found, hs = ebay.scan(config.get("ebay", {}))
    health.extend(hs)
    for l in found:
        listings.setdefault(l.id, l)

    print("Scanning Craigslist metros…")
    found, h = craigslist.scan(config.get("craigslist", {}))
    health.append(h)
    for l in found:
        listings.setdefault(l.id, l)

    print("Scanning JDM importer sites…")
    found, hs = jdm_sites.scan(config.get("jdm_sites", []))
    health.extend(hs)
    for l in found:
        listings.setdefault(l.id, l)

    print("Junkyard watch (Row52)…")
    found, h = row52.scan()
    health.append(h)
    for l in found:
        listings.setdefault(l.id, l)

    print("Forum classifieds (RSS)…")
    found, hs = forums.scan(config.get("forums", []))
    health.extend(hs)
    for l in found:
        listings.setdefault(l.id, l)

    print("Japan exporters…")
    found, hs = japan.scan(config.get("japan_exporters", []))
    health.extend(hs)
    for l in found:
        listings.setdefault(l.id, l)

    print("Canadian classifieds…")
    # japan.scan is the generic import-site sweep (flags is_import).
    found, hs = japan.scan(config.get("canada_sites", []))
    health.extend(hs)
    for l in found:
        listings.setdefault(l.id, l)

    print("Web discovery…")
    found, h = discovery.scan(config.get("discovery") or config.get("google", {}))
    health.append(h)
    for l in found:
        listings.setdefault(l.id, l)

    relevant = [classify.classify(l) for l in listings.values()
                if classify.is_relevant(l)]
    print(f"{len(listings)} raw results → {len(relevant)} relevant after filtering")

    translated = 0
    for l in relevant:
        if translate.needs_translation(l.title):
            l.title_en = translate.translate(l.title)
            translated += bool(l.title_en)
        if l.description and translate.needs_translation(l.description):
            l.description_en = translate.translate(l.description[:300])
    if translated:
        print(f"{translated} listings auto-translated for display")

    st = state.load()
    new, seen = state.mark(st, relevant)
    state.save(st)
    print(f"{len(new)} new, {len(seen)} previously seen")

    board_url = config.get("board_url", "")
    html_body = digest.build(new, seen, health, board_url=board_url)
    subj = digest.subject(new)
    with open("digest.html", "w") as f:
        f.write(html_body)
    # Full uncapped board, published via GitHub Pages from docs/.
    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "index.html"), "w") as f:
        f.write(digest.build(new, seen, health, full=True))
    print(f"Digest written to digest.html — subject: {subj}")

    recipient = config.get("recipient", "")
    if emailer.configured():
        to = emailer.send(subj, html_body, recipient)
        print(f"Digest emailed to {to}")
    else:
        print("SMTP not configured (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD) — "
              "digest NOT emailed. See README for secret setup.")

    failed = [h for h in health if not h.ok]
    for h in failed:
        print(f"Source problem — {h.source}: {h.note}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
