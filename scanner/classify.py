"""Smart 2L-T vs 2L-TE classification.

The Toyota 2L-T (2.4L turbo diesel) uses a MECHANICAL injection pump; the
2L-TE uses an ECU-controlled electronic pump. Sellers constantly mix the two
up — mechanical 2L-Ts are very often listed as "2LTE" — so instead of
discarding 2L-TE listings we classify every candidate and flag the ambiguous
ones for a quick manual check (one look at the injection pump settles it:
the 2L-TE pump has a wiring connector / electronics on top, the 2L-T pump
has a plain cable-actuated throttle lever and no wiring).
"""

from __future__ import annotations

import re

from .models import Listing

# Verdicts, in descending order of how promising they are for the buyer.
LIKELY_2LT = "LIKELY_2LT"            # mechanical — what we want
CHECK_MISLABELED = "CHECK_MISLABELED"  # says 2L-TE but smells mechanical, or ambiguous
UNCERTAIN = "UNCERTAIN"              # a 2L-family turbo diesel, can't tell which
LIKELY_2LTE = "LIKELY_2LTE"          # strong electronic signals — verify anyway

_VERDICT_RANK = {LIKELY_2LT: 3, CHECK_MISLABELED: 2, UNCERTAIN: 1, LIKELY_2LTE: 0}

# Donor vehicles: the 2L-T (mechanical) came in Hilux pickups (LN65/LN106/
# LN107/LN111...), early Hilux Surf LN61/LN130 (pre-8/1990), and Land Cruiser
# II / Bundera LJ70/71/73. The 2L-TE (electronic) came in later Hilux Surf
# LN130, Land Cruiser Prado LJ71/78, and Mark II / Chaser / Cresta LX90 etc.
_MECHANICAL_SIGNALS = [
    "mechanical injection", "mechanical pump", "mechanical fuel",
    "no ecu", "non-efi", "non efi", "not electronic", "cable throttle",
    "ln65", "ln106", "ln107", "ln111", "ln61", "lj70", "lj71", "lj73",
    "bundera", "land cruiser ii",
]
_ELECTRONIC_SIGNALS = [
    "ecu", "efi", "electronic fuel injection", "electronically controlled",
    "electronic injection", "electric injection", "computer",
    "ln130 surf", "lj78", "prado", "lx90", "chaser", "cresta", "mark ii",
]
_TRANSMISSION_SIGNALS = [
    "transmission", "gearbox", "trans ", "5 speed", "5-speed", "5spd",
    "w56", "g52", "g54", "l52", "r150", "manual swap", "automatic",
    "front cut", "front clip", "half cut", "halfcut", "complete swap",
    "engine and trans", "motor and trans",
]

_TOYOTA_WORDS = ("toyota", "hilux", "surf", "land cruiser", "landcruiser",
                 "prado", "4runner", "pickup")


def _norm(text: str) -> str:
    """Collapse separators so 2L-T / 2L T / 2LT all normalize to 2LT."""
    return re.sub(r"[\s\-–—_/.]+", "", text.upper())


def _mentions(text: str) -> tuple[int, int]:
    """Return (count of bare 2LT mentions, count of 2LTE mentions)."""
    norm = _norm(text)
    lte = len(re.findall(r"2LTE", norm))
    # 2LT mentions that are NOT part of a 2LTE mention
    lt = len(re.findall(r"2LT(?!E)", norm))
    return lt, lte


def is_relevant(listing: Listing) -> bool:
    """Keep only plausible 2L-family turbo diesel listings."""
    text = listing.text().lower()
    lt, lte = _mentions(listing.text())
    if lt or lte:
        # Guard against the Camaro/Silverado "2LT" trim level and similar.
        chevy = any(w in text for w in ("camaro", "silverado", "corvette",
                                        "equinox", "malibu", "traverse", "chevy",
                                        "chevrolet", "colorado zr"))
        toyota = any(w in text for w in _TOYOTA_WORDS)
        diesel = "diesel" in text or "turbo" in text
        return toyota or (diesel and not chevy)
    # No engine code: require a Toyota word plus diesel context.
    toyota = any(w in text for w in _TOYOTA_WORDS)
    return toyota and "diesel" in text and ("2.4" in text or "engine" in text
                                            or "motor" in text)


def classify(listing: Listing) -> Listing:
    text = listing.text().lower()
    lt, lte = _mentions(listing.text())
    mech = sum(1 for s in _MECHANICAL_SIGNALS if s in text)
    elec = sum(1 for s in _ELECTRONIC_SIGNALS if s in text)

    if lte and mech > elec:
        listing.verdict = CHECK_MISLABELED
        listing.verdict_note = ("Listed as 2L-TE but the description has "
                                "mechanical-injection signals — good chance it's "
                                "actually a 2L-T. Ask the seller for a photo of "
                                "the injection pump (no wiring connector on the "
                                "pump = mechanical 2L-T).")
    elif lt and not lte and elec == 0:
        listing.verdict = LIKELY_2LT
        listing.verdict_note = ("Listed as 2L-T with no electronic-injection "
                                "signals. Confirm the pump is cable-actuated "
                                "with no ECU harness.")
    elif lt and not lte:
        listing.verdict = CHECK_MISLABELED
        listing.verdict_note = ("Listed as 2L-T but mentions electronics — "
                                "verify which pump it actually has.")
    elif lte:
        if elec > 0:
            listing.verdict = LIKELY_2LTE
            listing.verdict_note = ("Listed as 2L-TE with electronic signals. "
                                    "Still worth a look — mislabeling is rampant; "
                                    "one pump photo settles it.")
        else:
            listing.verdict = CHECK_MISLABELED
            listing.verdict_note = ("Listed as 2L-TE but nothing in the ad "
                                    "confirms electronic injection. Sellers very "
                                    "often call a mechanical 2L-T a '2LTE' — ask "
                                    "for an injection pump photo.")
    else:
        listing.verdict = UNCERTAIN
        listing.verdict_note = ("Toyota diesel match without an explicit engine "
                                "code — could be a 2L-T; check the ad.")

    trans_hits = [s for s in _TRANSMISSION_SIGNALS if s in text]
    listing.has_transmission = bool(trans_hits)
    if listing.has_transmission:
        listing.transmission_note = ("Mentions transmission (" +
                                     ", ".join(sorted(set(t.strip() for t in trans_hits))[:4]) + ")")

    listing.score = _VERDICT_RANK[listing.verdict] * 10 + (5 if listing.has_transmission else 0)
    return listing
