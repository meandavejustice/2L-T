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

# Bare "2L turbo" phrasing means the 2L-T; displacements must not trigger it.
check("Toyota Hilux 2L Turbo Diesel Engine complete", "", True,
      classify.LIKELY_2LT)
check("Toyota 2 L turbo diesel motor pickup", "", True, classify.LIKELY_2LT)
check("Toyota Supra 3.0 twin turbo 2JZ engine", "", False)

# Wider L-family: collected and ranked below the turbo candidates.
check("Toyota 2L diesel engine non turbo Hilux", "", True, classify.L_FAMILY)
check("Toyota 3L 2.8 diesel engine pickup", "", True, classify.L_FAMILY)
check("Toyota 5L-E diesel engine", "", True, classify.L_FAMILY)
# An NA code plus a turbo mention smells like a mislabeled 2L-T.
check("Toyota 3L turbo diesel engine Hilux", "", True,
      classify.CHECK_MISLABELED)
# Displacement strings still must not read as family codes.
check("Chevy Silverado 4.3L V6 engine", "", False)

# Codeless but plausible: 2.4 turbo diesel Toyota.
check("Toyota pickup 2.4 turbo diesel engine complete", "", True,
      classify.UNCERTAIN)
check("Toyota Hilux 2.4L turbo diesel engine and transmission front cut",
      "", True, classify.UNCERTAIN, True)

# Japanese exporter listings (engine codes stay Latin in Japanese titles).
check("トヨタ ハイラックス 2L-T エンジン 5MT ミッション付き 実働", "", True,
      classify.LIKELY_2LT, True)
check("トヨタ 2LTE ディーゼルターボ エンジンASSY", "", True,
      classify.CHECK_MISLABELED)
check("2LT エンジン 中古", "", True, classify.LIKELY_2LT)


def check_part(title, desc, is_part):
    l = mk(title, desc)
    assert classify.is_relevant(l), f"{title!r}: expected relevant"
    classify.classify(l)
    assert l.is_part == is_part, f"{title!r}: is_part {l.is_part} != {is_part}"


# Parts vs complete engines: components demote to the parts section.
check_part("Hastings Diesel STD Piston Ring Set Eng Code:2LT Turbo Toyota Pickup",
           "", True)
check_part("4X 12V Glow Plug for Toyota Hilux 3L 5L 2L-TE Engine", "", True)
check_part("Injection Pump Fits Toyota Hilux 4-Runner Engine: 2L-T 2.4L", "", True)
check_part("Toyota Hilux 2L-T turbo diesel complete engine with W56 transmission",
           "", False)
check_part("JDM Toyota 2LT Turbo Diesel Engine Long Block LN106", "", False)
check_part("Toyota 2LTE turbo diesel front cut engine trans wiring", "", False)
check_part("2L-T エンジンマウント トヨタ ハイラックス", "", True)
check_part("GEARBOX ENGINE SEALING Toyota LAND CRUISER 2.4 TD 2L-T", "", True)
check_part("トヨタ 2LT エンジン本体 実働", "", False)

# Translation detection (display-only; no network in tests).
from scanner import translate  # noqa: E402
assert translate.needs_translation("トヨタ ハイラックス 2L-T エンジン")
assert translate.needs_translation("2LT エンジン 中古")
assert not translate.needs_translation("Toyota Hilux 2L-T turbo diesel engine")
assert not translate.needs_translation("")

print("all classifier tests passed")
