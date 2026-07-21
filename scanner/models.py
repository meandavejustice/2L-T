"""Shared data types for the 2L-T scanner."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Listing:
    id: str                      # stable dedupe key, e.g. "ebay:126012345678"
    source: str                  # human-readable source name
    title: str
    url: str
    price: str = ""
    location: str = ""
    description: str = ""        # any extra text we captured (used by classifier)
    image: str = ""

    # Filled in by the classifier:
    verdict: str = ""            # see classify.py verdict constants
    verdict_note: str = ""
    has_transmission: bool = False
    transmission_note: str = ""
    is_part: bool = False        # a component (pump, gasket...), not an engine
    score: int = 0               # sort key: higher = more promising

    def text(self) -> str:
        return f"{self.title} {self.description}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SourceHealth:
    source: str
    ok: bool
    found: int = 0
    note: str = ""
