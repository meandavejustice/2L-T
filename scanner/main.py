"""Daily 2L-T scan orchestrator.

Runs every source (a failing source never kills the run), filters and
classifies candidates, diffs against the persistent seen-state, writes
digest.html, and emails the digest.
"""

from __future__ import annotations

import sys

import yaml

from . import classify, digest, emailer, state
from .models import Listing
from .sources import craigslist, ebay, google_cse, jdm_sites


def run() -> int:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    listings: dict[str, Listing] = {}
    health = []

    print("Scanning eBay…")
    found, h = ebay.scan(config.get("ebay", {}))
    health.append(h)
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

    print("Google discovery…")
    found, h = google_cse.scan(config.get("google", {}))
    health.append(h)
    for l in found:
        listings.setdefault(l.id, l)

    relevant = [classify.classify(l) for l in listings.values()
                if classify.is_relevant(l)]
    print(f"{len(listings)} raw results → {len(relevant)} relevant after filtering")

    st = state.load()
    new, seen = state.mark(st, relevant)
    state.save(st)
    print(f"{len(new)} new, {len(seen)} previously seen")

    html_body = digest.build(new, seen, health)
    subj = digest.subject(new)
    with open("digest.html", "w") as f:
        f.write(html_body)
    print(f"Digest written to digest.html — subject: {subj}")

    recipient = config.get("recipient", "")
    if emailer.configured():
        to = emailer.send(subj, html_body, recipient)
        print(f"Digest emailed to {to}")
    else:
        print("SMTP not configured (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD) — "
              "digest NOT emailed. See README for secret setup.")

    failed = [h for h in health if not h.ok]
    if failed:
        print("Sources with problems: " + ", ".join(h.source for h in failed))
    return 0


if __name__ == "__main__":
    sys.exit(run())
