"""Build the daily HTML email digest (inline styles — email-client safe)."""

from __future__ import annotations

import html
from datetime import date

from .classify import LIKELY_2LT, CHECK_MISLABELED, UNCERTAIN, LIKELY_2LTE
from .models import Listing, SourceHealth

_BADGES = {
    LIKELY_2LT: ("LIKELY 2L-T ✓", "#0a7a2f"),
    CHECK_MISLABELED: ("VERIFY — MAY BE MISLABELED", "#b06000"),
    UNCERTAIN: ("UNCERTAIN — CHECK AD", "#555555"),
    LIKELY_2LTE: ("PROBABLY 2L-TE", "#8a1f1f"),
}


def _esc(s: str) -> str:
    return html.escape(s or "")


def _card(l: Listing, is_new: bool) -> str:
    badge_text, badge_color = _BADGES.get(l.verdict, ("", "#555"))
    new_tag = ('<span style="background:#c8102e;color:#fff;padding:2px 7px;'
               'border-radius:3px;font-size:11px;font-weight:bold;">NEW</span> '
               if is_new else "")
    trans = (f'<div style="color:#0a5aa6;font-size:13px;margin-top:3px;">🔧 '
             f'{_esc(l.transmission_note)}</div>' if l.has_transmission else "")
    meta = " · ".join(filter(None, [_esc(l.price), _esc(l.location), _esc(l.source)]))
    desc = (f'<div style="color:#666;font-size:12px;margin-top:4px;">'
            f'{_esc(l.description[:280])}</div>' if l.description else "")
    return f"""
    <div style="border:1px solid #ddd;border-radius:6px;padding:12px 14px;margin:0 0 10px 0;">
      <div style="margin-bottom:4px;">{new_tag}
        <span style="background:{badge_color};color:#fff;padding:2px 7px;border-radius:3px;
                     font-size:11px;font-weight:bold;">{badge_text}</span></div>
      <a href="{_esc(l.url)}" style="font-size:15px;font-weight:bold;color:#0a5aa6;
         text-decoration:none;">{_esc(l.title)}</a>
      <div style="color:#333;font-size:13px;margin-top:3px;">{meta}</div>
      {trans}
      <div style="color:#444;font-size:12px;margin-top:5px;font-style:italic;">{_esc(l.verdict_note)}</div>
      {desc}
      <div style="margin-top:6px;font-size:12px;"><a href="{_esc(l.url)}">Direct link →</a></div>
    </div>"""


def _health_rows(health: list[SourceHealth]) -> str:
    rows = []
    for h in health:
        dot = "🟢" if h.ok else "🔴"
        rows.append(f"<tr><td style='padding:3px 10px 3px 0;'>{dot} {_esc(h.source)}</td>"
                    f"<td style='padding:3px 10px 3px 0;text-align:right;'>{h.found}</td>"
                    f"<td style='padding:3px 0;color:#777;'>{_esc(h.note)}</td></tr>")
    return "\n".join(rows)


def build(new: list[Listing], seen: list[Listing],
          health: list[SourceHealth]) -> str:
    today = date.today().strftime("%A, %B %d, %Y")
    order = lambda ls: sorted(ls, key=lambda l: -l.score)
    new, seen = order(new), order(seen)

    if new:
        headline = f"{len(new)} new listing{'s' if len(new) != 1 else ''} found today"
    elif seen:
        headline = f"No new listings today — {len(seen)} previously found still tracked"
    else:
        headline = "No matching listings found today"

    new_section = ("".join(_card(l, True) for l in new)
                   if new else '<p style="color:#777;">Nothing new today.</p>')
    seen_section = ("".join(_card(l, False) for l in seen[:30])
                    if seen else '<p style="color:#777;">None yet.</p>')
    seen_more = (f'<p style="color:#777;font-size:12px;">…and {len(seen) - 30} more '
                 f'previously-seen listings (see data/seen_listings.json).</p>'
                 if len(seen) > 30 else "")

    return f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:680px;margin:auto;color:#222;">
  <h1 style="font-size:20px;border-bottom:3px solid #c8102e;padding-bottom:8px;">
    🔍 Toyota 2L-T Daily Scan — {today}</h1>
  <p style="font-size:14px;"><b>{headline}.</b> Target: <b>2L-T</b> (2.4L turbo diesel,
  <b>mechanical</b> injection) — not the electronic 2L-TE, but 2L-TE-labeled ads are
  included and flagged because sellers mislabel constantly.</p>

  <h2 style="font-size:16px;margin-top:22px;">🆕 New since last scan</h2>
  {new_section}

  <h2 style="font-size:16px;margin-top:22px;">📌 Still listed (previously found)</h2>
  {seen_section}
  {seen_more}

  <h2 style="font-size:16px;margin-top:22px;">🩺 Source health</h2>
  <table style="font-size:13px;border-collapse:collapse;">{_health_rows(health)}</table>

  <h2 style="font-size:16px;margin-top:22px;">🧰 How to verify it's a real 2L-T</h2>
  <ul style="font-size:13px;color:#444;">
    <li><b>Injection pump photo is the tiebreaker:</b> the 2L-T pump is purely mechanical —
        cable-actuated throttle lever, no electrical connector on the pump body. The 2L-TE
        pump has a black electronic actuator housing and a multi-pin wiring connector on top.</li>
    <li><b>Donor vehicle helps:</b> Hilux pickups (LN65/LN106/LN107/LN111), early Hilux Surf,
        and Land Cruiser LJ70/71/73 = mechanical 2L-T. Later Hilux Surf LN130, Prado LJ78,
        and Mark II/Chaser sedans = electronic 2L-TE.</li>
    <li><b>Ask about the transmission:</b> W56/G52/G54/L52 5-speeds bolt up; "front cut" or
        "half cut" listings usually include engine + trans + harness.</li>
  </ul>
  <p style="font-size:11px;color:#999;border-top:1px solid #eee;padding-top:8px;">
    Automated daily scan · eBay, Craigslist metros, US JDM importers · repo: 2L-T</p>
</div>"""


def subject(new: list[Listing]) -> str:
    d = date.today().strftime("%b %d")
    if not new:
        return f"2L-T Scan {d}: no new listings"
    top = max(new, key=lambda l: l.score)
    likely = sum(1 for l in new if l.verdict == LIKELY_2LT)
    tag = f", {likely} likely 2L-T" if likely else ""
    return f"2L-T Scan {d}: {len(new)} new{tag} — {top.title[:60]}"
