"""Build the daily HTML email digest (inline styles — email-client safe)."""

from __future__ import annotations

import html
from datetime import date

from .classify import (LIKELY_2LT, CHECK_MISLABELED, LIKELY_2LTE, L_FAMILY,
                       UNCERTAIN)
from .models import Listing, SourceHealth

_BADGES = {
    LIKELY_2LT: ("LIKELY 2L-T ✓", "#0a7a2f"),
    CHECK_MISLABELED: ("VERIFY — MAY BE MISLABELED", "#b06000"),
    LIKELY_2LTE: ("PROBABLY 2L-TE", "#8a1f1f"),
    L_FAMILY: ("L-SERIES RELATIVE (2L/3L/5L)", "#3d5a80"),
    UNCERTAIN: ("UNCERTAIN — CHECK AD", "#555555"),
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
    title_disp = l.title_en or l.title
    original = (f'<div style="color:#999;font-size:11px;margin-top:2px;">🌐 '
                f'auto-translated · original: {_esc(l.title[:140])}</div>'
                if l.title_en else "")
    desc_text = l.description_en or l.description
    desc = (f'<div style="color:#666;font-size:12px;margin-top:4px;">'
            f'{_esc(desc_text[:280])}</div>' if desc_text else "")
    return f"""
    <div style="border:1px solid #ddd;border-radius:6px;padding:12px 14px;margin:0 0 10px 0;">
      <div style="margin-bottom:4px;">{new_tag}
        <span style="background:{badge_color};color:#fff;padding:2px 7px;border-radius:3px;
                     font-size:11px;font-weight:bold;">{badge_text}</span></div>
      <a href="{_esc(l.url)}" style="font-size:15px;font-weight:bold;color:#0a5aa6;
         text-decoration:none;">{_esc(title_disp)}</a>
      {original}
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
    new_eng = order([l for l in new if not l.is_part and not l.is_import])
    seen_eng = order([l for l in seen if not l.is_part and not l.is_import])
    imports = order([l for l in new + seen if l.is_import and not l.is_part])
    parts = order([l for l in new if l.is_part]) + \
        order([l for l in seen if l.is_part])
    new_ids = {l.id for l in new}

    if new_eng:
        headline = (f"{len(new_eng)} new engine listing"
                    f"{'s' if len(new_eng) != 1 else ''} found today")
    elif seen_eng:
        headline = (f"No new engine listings today — {len(seen_eng)} previously "
                    f"found still tracked")
    else:
        headline = "No matching engine listings found today"

    new_section = ("".join(_card(l, True) for l in new_eng)
                   if new_eng else '<p style="color:#777;">Nothing new today.</p>')
    seen_section = ("".join(_card(l, False) for l in seen_eng[:30])
                    if seen_eng else '<p style="color:#777;">None yet.</p>')
    seen_more = (f'<p style="color:#777;font-size:12px;">…and {len(seen_eng) - 30} more '
                 f'previously-seen listings (see data/seen_listings.json).</p>'
                 if len(seen_eng) > 30 else "")
    imports_section = ""
    if imports:
        new_imp = sum(1 for l in imports if l.id in new_ids)
        imp_cards = "".join(_card(l, l.id in new_ids) for l in imports[:20])
        imp_more = (f'<p style="color:#777;font-size:12px;">…and {len(imports) - 20} '
                    f'more import listings.</p>' if len(imports) > 20 else "")
        imports_section = f"""
  <h2 style="font-size:16px;margin-top:22px;">🌍 Imports — ship to USA
    <span style="font-weight:normal;color:#777;font-size:13px;">({len(imports)}
    listings, {new_imp} new)</span></h2>
  <p style="font-size:12px;color:#777;margin:4px 0 10px 0;">Japan (Yahoo Auctions
    via Buyee, BE FORWARD, Croooober), eBay UK/Australia/Canada (filtered to
    US-deliverable items), and Canadian classifieds. Foreign-currency prices
    exclude freight — budget roughly $250–500 (parcel) to $800–1,500
    (pallet/consolidated) from Japan; less from Canada.</p>
  {imp_cards}{imp_more}"""

    parts_section = ""
    if parts:
        new_parts = sum(1 for l in parts if l.id in new_ids)
        parts_cards = "".join(_card(l, l.id in new_ids) for l in parts[:25])
        parts_more = (f'<p style="color:#777;font-size:12px;">…and {len(parts) - 25} '
                      f'more parts listings.</p>' if len(parts) > 25 else "")
        # <details> collapses in clients that support it (Apple Mail, iOS);
        # others (Gmail) render it as a normal always-open section.
        parts_section = f"""
  <details style="margin-top:22px;">
    <summary style="font-size:16px;font-weight:bold;cursor:pointer;">🔩 Parts &amp;
      components <span style="font-weight:normal;color:#777;font-size:13px;">({len(parts)}
      listings, {new_parts} new — not complete engines; tap to expand)</span></summary>
    <div style="margin-top:10px;">{parts_cards}{parts_more}</div>
  </details>"""

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
  {imports_section}
  {parts_section}

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
    engines = [l for l in new if not l.is_part and not l.is_import]
    imports = sum(1 for l in new if l.is_import and not l.is_part)
    imp_tag = f" +{imports} import{'s' if imports != 1 else ''}" if imports else ""
    if not engines:
        parts = sum(1 for l in new if l.is_part)
        tag = f" ({parts} parts)" if parts else ""
        return f"2L-T Scan {d}: no new US engine listings{imp_tag}{tag}"
    top = max(engines, key=lambda l: l.score)
    likely = sum(1 for l in engines if l.verdict == LIKELY_2LT)
    tag = f", {likely} likely 2L-T" if likely else ""
    return (f"2L-T Scan {d}: {len(engines)} new engine"
            f"{'s' if len(engines) != 1 else ''}{tag}{imp_tag} — {top.title[:60]}")
