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
# Sellers mislist across the whole Toyota L family (L/2L/2L-II/3L/5L and the
# turbo 2L-T/2L-TE), so every family member is collected; ranking keeps the
# 2L-T first.
LIKELY_2LT = "LIKELY_2LT"            # mechanical turbo — what we want
CHECK_MISLABELED = "CHECK_MISLABELED"  # labeled wrong for what the ad describes
LIKELY_2LTE = "LIKELY_2LTE"          # electronic turbo — verify, often mislabeled
L_FAMILY = "L_FAMILY"                # NA relative (2L/3L/5L...) — eyeball it
UNCERTAIN = "UNCERTAIN"              # Toyota diesel, can't tell which

_VERDICT_RANK = {LIKELY_2LT: 5, CHECK_MISLABELED: 4, LIKELY_2LTE: 3,
                 L_FAMILY: 2, UNCERTAIN: 1}

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
    "5mt", "ミッション", "マニュアル",
]

# Japanese equivalents used in the diesel/turbo context checks below.
_DIESEL_JP = "ディーゼル"
_TURBO_JP = "ターボ"

_TOYOTA_WORDS = ("toyota", "hilux", "surf", "land cruiser", "landcruiser",
                 "prado", "4runner", "pickup",
                 # Japanese (exporter listings keep engine codes in Latin)
                 "トヨタ", "ハイラックス", "サーフ", "ランクル", "プラド",
                 "ハイエース")

# Component listings (huge share of eBay family-code hits). A part signal
# without an engine-assembly signal demotes the listing to the parts section.
_PART_SIGNALS = [
    "glow plug", "water pump", "oil pump", "vacuum pump", "radiator",
    "gasket", "piston ring", "ring set", "piston", "bearing", "oil filter",
    "air filter", "fuel filter", "timing belt", "drive belt", "belt kit",
    "injector", "turbocharger", "cylinder head", "crankshaft", "camshaft",
    "valve cover", "oil pan", "thermostat", "alternator", "starter motor",
    "engine mount", "motor mount", "head gasket", "overhaul kit",
    "rebuild kit", "repair kit", "injection pump", "oil cooler", "oil seal",
    "seal kit", "hose", "sensor", "service manual", "repair manual",
    "workshop manual", "decal", "emblem", "sticker", "glow controller",
    "timing cover", "flywheel", "clutch kit", "clutch disc", "pressure plate",
    "manifold", "fan blade", "blade fan", "fan clutch", "fan shroud",
    "shroud", "dipstick", "pulley", "tensioner", "banjo bolt", "glow screw",
    "wiring harness", "relay", "solenoid", "cap kit", "valve stem",
    "sealing", "seal set", "o-ring", "oring kit", "shim", "washer",
    "starter", "starting motor", "snorkel", "pump head", "rotor",
    "control unit", "ecu", "ecm", "blade", "transmission plate",
    "trans plate", "engine plate", "mounting plate",
    "connecting rod", "conrod", "inlet valve", "exhaust valve",
    "valve guide", "valve set", "valve spring", "turbo charger",
    "main seal", "bolt set", "bolt kit", "stud set", "cam chain",
    "timing chain", "chain tensioner", "glow relay", "engine cover",
    "brake", "ball joint", "tie rod", "cv joint", "drum", "gear case",
    "timing gear", "valve lifter", "lifter set", "re-ring", "rering",
    "turbo kit", "down pipe", "downpipe", "dump pipe", "flange",
    "wiring loom", "loom", "stud nut", "oil line", "water line",
    "line kit", "copper core", "adrad", "intercooler", "service kit",
    "filter", "valve seal", "mount ", "mounting", "con rod", "bracket",
    "engine part", "bell housing", "bellhousing", "rocker", "rad cap",
    "cap lever", "fitting", "fittng", "brochure", "handbuch", "werkstatt",
    "fleetguard", "covers petrol", "splash guard", "mud guard", "termostat",
    "housing cap", "outlet housing", "shock absorber", "kyb",
    "pickup parts", "parts lot", "misc parts",
    # Japanese part words
    "マウント", "ガスケット", "ポンプ", "ラジエーター", "ラジエター",
    "インジェクター", "ハーネス", "オルタネーター", "セルモーター",
    "タービン", "フィルター", "ベルト", "プラグ", "センサー",
    "ターボチャージャー", "チャージャー", "カバー", "クランクシャフト",
    "カムシャフト", "テンショナー", "ボルト", "ナット", "バルブ",
    "ピストン", "リング", "コンピューター", "コンピュータ", "cpu",
    "シール", "修理書", "整備書", "サービスマニュアル", "パーツリスト",
    "カタログ", "ステッカー", "エンブレム", "コンロッド", "メタル",
    "サーモスタット", "プーリー", "アイドラー", "シリンダーヘッド",
    "ロッカー", "ダウンサス", "ダウンフォース", "レシーバ", "リザーブ",
    "エアコン", "タンク", "補修", "ショック", "カヤバ", "サスペンション",
    "ウォーター", "クラッチ", "カップ", "キット", "オイルチェンジャー",
    "チェンジャー",
]
# Only ENGINE-specific assembly wording can rescue a listing that also has a
# part signal — bare "complete"/"recon" must not ("Complete Cylinder Head"
# is a head, not an engine).
_ASSEMBLY_SIGNALS = [
    "complete engine", "engine assembly", "complete motor", "long block",
    "short block", "bare engine", "engine swap", "front cut", "front clip",
    "half cut", "halfcut", "engine and trans", "motor and trans",
    "engine with trans", "running engine", "complete swap", "drop out",
    "engine drop",
    # Japanese: engine unit / engine assy / running-when-pulled. Bare "assy"
    # must NOT count — a "turbocharger assy" is still a part.
    "エンジン本体", "エンジンassy", "engine assy", "エンジンアッセンブリー",
    "実働", "載せ替え",
]

# "…kit"/"…set" style wording marks a parts product even when assembly words
# appear ("Complete Engine Gasket Kit" is a gasket kit, not an engine).
_KIT_OVERRIDES = (" kit", " set", "pair of", " pcs", "2x ", "4x ", "x2 ",
                  "x4 ", "セット", "キット")

# Fluids: "5L" on an oil/coolant bottle is 5 liters, not the 5L engine.
_VISCOSITY_RE = re.compile(r"\b\d{1,2}w[- ]?\d{2}\b")
_FLUID_WORDS = ("engine oil", "motor oil", "coolant", "antifreeze",
                "anti-freeze", "anti-boil", "gear oil", "diff oil",
                "gearbox oil", "transmission fluid")

# Wanted/WTB ads are buyers, not sellers (including our own posted ads
# echoing back through the scrape).
_WANTED_RE = re.compile(
    r"\b(wtb|wanted|want to buy|looking for|in search of|iso)\b", re.I)
_WANTED_JP = ("求む", "買います", "探してます", "譲ってください")

# Modern Toyota diesels and non-Toyota lumps that sneak past the family
# regex via "2.0 diesel"-style titles.
_MODERN_WORDS = ("avensis", "rav4", "rav-4", "aygo", "proace", "corolla",
                 "yaris", "auris", "verso", "invincible", "hdi", "bluehdi",
                 "gun1", "kun2")

# Other Toyota diesel engine codes: a listing naming one of these (without any
# 2LT/2LTE mention) is a different engine, not a mislabeled 2L-T.
_OTHER_DIESEL_RE = re.compile(
    r"\b(1hz|1hd(?:\s?f?te?)?|1kz(?:\s?te?)?|1kd|2kd|12ht?|13bt?|2h|3b|14b|15b"
    r"|1ad|2ad|1gd|2gd|1cd|2cd|1nd|2az|dw10|d\s?4\s?d"
    r"|1dz|2dz|11z|13z|14z)\b")  # forklift diesels

# The 2L-T is 2.4L; an explicit different displacement (4.2L, 3.0L, …) without
# a 2LT mention means it's some other engine. "2.0 diesel"/"3.0 TD" style
# phrasing (no "L") counts too.
_DISPLACEMENT_RE = re.compile(
    r"\b(\d\.\d)\s*(?:l(?:iter|itre)?s?\b|td\b|turbo\b|diesel\b|d\b)")

# Engine-code matcher on separator-normalized text ("2L-T"/"2L T"/"2LT" →
# "2L T"/"2LT"). Word boundaries prevent "4.2L Turbo" ("4 2L Turbo") from
# reading as a 2LT mention: the bare-T form must end at a word boundary.
_CODE_RE = re.compile(r"\b2\s?L\s?T(E)?\b")

# "Toyota 2L turbo" without the -T suffix still means the 2L-T (the 2L is the
# base engine; turbo variant = 2L-T). Matched on RAW text so the lookbehind
# can reject displacements like "4.2L turbo". Only consulted when no explicit
# 2LT/2LTE code matched, so it cannot double-count.
_BARE_2L_RE = re.compile(r"(?<![\d.])\b2\s?L\b", re.I)

# Ads that deny the turbo ("2L non turbo") must not promote to 2L-T.
_NO_TURBO = ("non turbo", "non-turbo", "no turbo", "not turbo", "nonturbo")

# Wider L-family codes on RAW text: 2L / 2L-II / 3L / 5L / 5L-E. The
# lookbehind keeps displacements ("4.3L") out; the lookahead keeps 2L-T/2L-TE
# out (those are handled as explicit code mentions above).
_FAMILY_RE = re.compile(
    r"(?<![\d.])\b([235])\s?L(?:\s?-?\s?(II|E))?\b(?!\s?[-–—]?\s?TE?\b)", re.I)


def _family_codes(text: str) -> list[str]:
    codes = set()
    for m in _FAMILY_RE.finditer(text):
        code = f"{m.group(1)}L" + (f"-{m.group(2).upper()}" if m.group(2) else "")
        codes.add(code)
    return sorted(codes)


def _norm(text: str) -> str:
    """Collapse separators to single spaces, preserving word boundaries."""
    return re.sub(r"[\s\-–—_/.]+", " ", text.upper())


def _mentions(text: str) -> tuple[int, int]:
    """Return (count of bare 2LT mentions, count of 2LTE mentions)."""
    norm = _norm(text)
    lt = lte = 0
    for m in _CODE_RE.finditer(norm):
        if m.group(1):
            lte += 1
        else:
            lt += 1
    tl = text.lower()
    turbo = "turbo" in tl or _TURBO_JP in text
    if (not lt and not lte and turbo and _BARE_2L_RE.search(text)
            and not any(p in tl for p in _NO_TURBO)):
        lt = 1
    return lt, lte


def is_relevant(listing: Listing) -> bool:
    """Keep only plausible 2L-family turbo diesel listings."""
    text = listing.text().lower()
    # Fluids first: oil/coolant bottles are sized in liters ("5L 5W-30"),
    # which collides with the 5L engine code.
    if _VISCOSITY_RE.search(text) or any(w in text for w in _FLUID_WORDS):
        return False
    # Wanted ads are buyers, not inventory.
    if _WANTED_RE.search(text) or any(w in listing.text() for w in _WANTED_JP):
        return False
    lt, lte = _mentions(listing.text())
    if lt or lte:
        # Guard against non-Toyota "2LT" collisions: the Chevy trim level and
        # Yamaha's V-MAX model code (JYA2LT...).
        chevy = any(w in text for w in ("camaro", "silverado", "corvette",
                                        "equinox", "malibu", "traverse", "chevy",
                                        "chevrolet", "colorado zr",
                                        "yamaha", "ヤマハ", "vmax", "v-max",
                                        "v max", "kawasaki", "カワサキ"))
        toyota = any(w in text for w in _TOYOTA_WORDS)
        diesel = ("diesel" in text or "turbo" in text
                  or _DIESEL_JP in listing.text() or _TURBO_JP in listing.text())
        # エンジン ("engine") in a Japanese title with an explicit code is a
        # strong auto signal, but the non-Toyota guard still applies (Yamaha
        # V-MAX listings say エンジン too).
        return toyota or ((diesel or "エンジン" in listing.text()) and not chevy)
    # Modern Toyota diesels (D-4D era) and rebadged non-Toyota lumps are a
    # different world entirely — reject on either codeless or family path.
    modern = (any(w in text for w in _MODERN_WORDS)
              or _OTHER_DIESEL_RE.search(_norm(listing.text()).lower()))
    # Explicit L-family code (2L/2L-II/3L/5L): keep with Toyota/diesel context.
    if _family_codes(listing.text()):
        toyota = any(w in text for w in _TOYOTA_WORDS)
        return (toyota or "diesel" in text) and not modern
    # No engine code: require a Toyota word plus diesel context…
    toyota = any(w in text for w in _TOYOTA_WORDS)
    if not (toyota and "diesel" in text and ("2.4" in text or "engine" in text
                                             or "motor" in text)):
        return False
    # …and reject listings that are explicitly a *different* Toyota diesel.
    if modern:
        return False
    # L-family displacements: 2.2 (L), 2.4 (2L/2L-T), 2.8 (3L). 3.0 stays out
    # in the codeless path — it collides with the excluded 1KZ.
    displacements = set(_DISPLACEMENT_RE.findall(text))
    if displacements and not displacements & {"2.2", "2.4", "2.8"}:
        return False
    return True


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
    elif (fam := _family_codes(listing.text())):
        codes = "/".join(fam)
        if (("turbo" in text or _TURBO_JP in text)
                and not any(p in text for p in _NO_TURBO)):
            listing.verdict = CHECK_MISLABELED
            listing.verdict_note = (f"Listed as {codes} but mentions a turbo — "
                                    "the NA L-series never came factory-turbocharged, "
                                    "so this may be a mislabeled 2L-T. Ask for turbo "
                                    "and injection-pump photos.")
        else:
            listing.verdict = L_FAMILY
            listing.verdict_note = (f"Listed as {codes} — same L-series family, not "
                                    "the turbo 2L-T as described. Sellers mislabel "
                                    "these constantly, so a photo check is worth it: "
                                    "factory turbo + cable-throttle mechanical pump "
                                    "= actually a 2L-T.")
    else:
        listing.verdict = UNCERTAIN
        listing.verdict_note = ("Toyota diesel match without an explicit engine "
                                "code — could be a 2L-T; check the ad.")

    trans_hits = [s for s in _TRANSMISSION_SIGNALS if s in text]
    listing.has_transmission = bool(trans_hits)
    if listing.has_transmission:
        listing.transmission_note = ("Mentions transmission (" +
                                     ", ".join(sorted(set(t.strip() for t in trans_hits))[:4]) + ")")

    part = any(p in text for p in _PART_SIGNALS)
    assembly = any(a in text for a in _ASSEMBLY_SIGNALS)
    kit = any(k in text for k in _KIT_OVERRIDES)
    # Kit/set wording keeps a listing in parts even when assembly words
    # appear ("Complete Engine Gasket Kit").
    listing.is_part = part and (kit or not assembly)

    listing.score = _VERDICT_RANK[listing.verdict] * 10 + (5 if listing.has_transmission else 0)
    if listing.is_part:
        listing.score -= 100
    return listing
