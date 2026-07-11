# 2L-T Hunter 🔍

Daily automated scan of US listings for the **Toyota 2L-T** — the 2.4L turbo
diesel with a **mechanical** injection pump (not the electronic 2L-TE).
Results arrive as a daily HTML email digest with direct links, prices,
locations, a 2L-T-vs-2L-TE verdict for every listing, and a note when a
transmission appears to be included.

## What it scans

| Source | How | Notes |
|---|---|---|
| **eBay** (US-located items) | Official Browse API if keys are set, page scrape otherwise | 7 query variants (2LT, 2L-T, 2LTE, 2.4 turbo diesel, …) |
| **Craigslist** | Static SEO search results across ~38 major metros | Craigslist has no national search, so we sweep city by city |
| **US JDM importers** | Site-search scrape of 10 importers (JDM Engine Depot, JDM Engine Zone, JDM Racing Motors, JDM of San Diego, JDM Engine Corp, JDM Alliance, JDM New York, JDM Orlando, Foreign Engines, Engine World) | Add more in `config.yaml` |
| **Google discovery** (optional) | Programmable Search API | Catches forums (ih8mud, Marlin Crawler), small importers, and marketplaces we don't scrape — enable with free API keys |

Every digest ends with a **source health table** so a blocked or broken
source is visible immediately instead of silently disappearing.

### Not scannable (check manually)
- **Facebook Marketplace** — aggressively blocks automation; no public API.
- **ih8mud / Marlin Crawler forum classifieds** — login-walled; the optional
  Google discovery source surfaces public threads from them.

## The 2L-T vs 2L-TE problem

Sellers mislabel constantly — mechanical 2L-Ts are very often advertised as
"2LTE". So the scanner **keeps** 2L-TE-labeled listings and classifies each
one:

- 🟩 **LIKELY 2L-T** — listed as 2L-T, no electronic-injection signals.
- 🟧 **VERIFY — MAY BE MISLABELED** — e.g. listed as 2L-TE but the ad has
  mechanical signals, or a bare "2LTE" claim with nothing confirming
  electronics. These are the hidden gems.
- ⬜ **UNCERTAIN** — Toyota diesel match without an explicit engine code.
- 🟥 **PROBABLY 2L-TE** — electronic signals present; ranked last but still
  shown.

**The one-photo tiebreaker to send every seller:** ask for a picture of the
injection pump. The 2L-T pump is fully mechanical — cable-actuated throttle
lever, no electrical connector. The 2L-TE pump has an electronic actuator
housing and a multi-pin plug on top. Donor vehicle is a strong hint too:
Hilux pickups (LN65/LN106/LN107/LN111) and Land Cruiser LJ70/71/73 =
mechanical; later Hilux Surf LN130, Prado LJ78, Mark II/Chaser sedans =
electronic.

Listings that mention a transmission (W56/G52/5-speed, front cut/half cut,
"engine and trans") get a 🔧 flag and rank higher within their group.

## Setup (one-time, ~10 minutes)

The scan runs via GitHub Actions on a daily cron — **schedules only fire on
the default branch**, so merge this branch to `main` to activate it.

### 1. Required: SMTP secrets (for the email)

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` (or `465` for implicit TLS) |
| `SMTP_USERNAME` | the sending account, e.g. `you@gmail.com` |
| `SMTP_PASSWORD` | for Gmail: an [App Password](https://myaccount.google.com/apppasswords) (requires 2FA), **not** your normal password |
| `DIGEST_TO` | optional — defaults to `david@justice.engineering` (set in `config.yaml`) |
| `DIGEST_FROM` | optional — defaults to `SMTP_USERNAME` |

Any SMTP provider works (Gmail, Fastmail, Resend `smtp.resend.com`,
SendGrid `smtp.sendgrid.net`, …).

### 2. Recommended: eBay API keys (free, makes eBay bulletproof)

eBay sometimes bot-blocks GitHub's IP ranges. With official keys the scanner
uses the Browse API instead of scraping:

1. Register at [developer.ebay.com](https://developer.ebay.com) (free).
2. Create a **Production** keyset; copy the App ID and Cert ID.
3. Add secrets `EBAY_CLIENT_ID` (App ID) and `EBAY_CLIENT_SECRET` (Cert ID).

### 3. Optional: Google discovery

1. Create an API key at
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   with the *Custom Search API* enabled (free tier: 100 queries/day; the
   daily run uses 4).
2. Create a search engine at
   [programmablesearchengine.google.com](https://programmablesearchengine.google.com).
   Google has discontinued "search the entire web" for new engines (and is
   sunsetting it everywhere on 2027-01-01), so configure a curated site list
   instead — the places 2L-Ts actually surface: `forum.ih8mud.com/*`,
   `www.yotatech.com/*`, `www.pirate4x4.com/*`, `expeditionportal.com/*`,
   `www.marlincrawler.com/*`, `www.racingjunk.com/*`, `www.car-part.com/*`,
   `offerup.com/*`, `www.mercari.com/*`, `*.craigslist.org` (up to 50
   domains). Copy the engine's ID from Overview → Basic.
3. Add secrets `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`.

### 4. Test it

Actions tab → **Daily 2L-T Scan** → **Run workflow**. Check your inbox and
the run log's source-health output; the digest is also attached to the run
as an artifact.

## Running locally

```bash
pip install -r requirements.txt
export SMTP_HOST=... SMTP_USERNAME=... SMTP_PASSWORD=...   # optional
python -m scanner.main        # writes digest.html; emails if SMTP is set
```

## Tuning

Everything lives in `config.yaml`: eBay/Craigslist queries, the metro list,
JDM importer sites (name + candidate search URLs — the parser is generic),
and Google queries. Classification keywords are in `scanner/classify.py`.
State (already-seen listings, for the NEW badges) is committed to
`data/seen_listings.json` by the workflow after each run.
