"""Classifier regression tests: `python tests/test_classify.py`."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scanner import classify  # noqa: E402
from scanner.models import Listing  # noqa: E402


def mk(title, desc=""):
    return Listing(id="t", source="test", title=title, url="u", description=desc)


def check(title, desc, relevant, verdict=None, trans=None):
    l = mk(title, desc)
    got_rel = classify.is_relevant(l)
    assert got_rel == relevant, f"{title!r}: relevance {got_rel} != {relevant}"
    if not relevant:
        return
    classify.classify(l)
    if verdict is not None:
        assert l.verdict == verdict, f"{title!r}: verdict {l.verdict} != {verdict}"
    if trans is not None:
        assert l.has_transmission == trans, f"{title!r}: trans {l.has_transmission}"


# The real-world false positive from the first production run: a 1HD-T whose
# "4.2L Turbo" read as a 2LT mention under the old normalizer.
check("1990-1994 Toyota Land Cruiser 80 Series 4.2L Turbo Diesel Engine JDM 1HD-T",
      "", False)
check("Toyota Land Cruiser 4.2L Turbo Diesel Engine", "", False)
check("JDM Toyota 1KZ-TE 3.0L Turbo Diesel Engine Hilux Surf", "", False)
check("Toyota 1HZ diesel engine", "", False)

# Chevy trim-level noise.
check("2016 Camaro 2LT V6 engine", "", False)

# The engines we want.
check("Toyota Hilux 2L-T turbo diesel engine with W56 5 speed transmission",
      "", True, classify.LIKELY_2LT, True)
check("JDM Toyota 2LT Turbo Diesel Engine LN106", "", True, classify.LIKELY_2LT)
check("Toyota 2 L T diesel motor", "", True, classify.LIKELY_2LT)

# Mislabel handling: bare "2LTE" claims stay in, flagged for verification.
check("Toyota 2LTE engine", "", True, classify.CHECK_MISLABELED)
check("Toyota 2L-TE engine 2.4 turbo diesel Hilux LN106",
      "mechanical pump, no ECU needed", True, classify.CHECK_MISLABELED)
check("JDM Toyota 2LTE Turbo Diesel Engine Hilux Surf",
      "complete with ECU and wiring harness", True, classify.LIKELY_2LTE)

# Codeless but plausible: 2.4 turbo diesel Toyota.
check("Toyota pickup 2.4 turbo diesel engine complete", "", True,
      classify.UNCERTAIN)
check("Toyota Hilux 2.4L turbo diesel engine and transmission front cut",
      "", True, classify.UNCERTAIN, True)

print("all classifier tests passed")
