#!/usr/bin/env python3
"""Suggest a logo source + LICENCE for each brand, from Wikidata / Wikimedia.

This deliberately does NOT crawl the companies' own websites and scrape
whatever image it finds — that would just harvest copyrighted artwork with no
idea of the terms. Instead it asks Wikidata for each company's official logo
(property P154) and looks up that file's licence on Wikimedia Commons, so you
can see which logos are actually free to reuse (many simple wordmarks are
public-domain "PD-textlogo") and decide for yourself before downloading.

It writes assets/logos/sources.suggested.tsv with columns:
    slug <TAB> licence <TAB> url
Review it, copy the rows you're happy to use into assets/logos/sources.tsv,
then run:  python scripts/fetch_logos.py

Usage:
    python scripts/find_logos.py            # all brands -> suggested.tsv
    python scripts/find_logos.py "SEAT"     # just one, printed to stdout
"""

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tvmaps.maps_marcas_logos import LOGO_DIR, brand_slug
from scripts.fetch_logos import all_brands  # reuse the roster

WD_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "static-tv-maps/1.0 logo-licence-finder (personal)"}
SUGGESTED = LOGO_DIR / "sources.suggested.tsv"


def _get(url, params):
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def wikidata_qid(brand: str):
    for lang in ("es", "en"):
        data = _get(WD_API, dict(action="wbsearchentities", search=brand,
                                 language=lang, format="json", limit=1))
        hits = data.get("search", [])
        if hits:
            return hits[0]["id"], hits[0].get("label", "")
    return None, ""


def logo_filename(qid: str):
    data = _get(WD_API, dict(action="wbgetclaims", entity=qid, property="P154",
                             format="json"))
    claims = data.get("claims", {}).get("P154", [])
    if not claims:
        return None
    return claims[0]["mainsnak"]["datavalue"]["value"]


def commons_licence(filename: str) -> str:
    data = _get(COMMONS_API, dict(action="query", titles=f"File:{filename}",
                                  prop="imageinfo", iiprop="extmetadata",
                                  format="json"))
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo", [{}])
        if info:
            meta = info[0].get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value")
            if lic:
                return lic
    return "unknown"


def file_url(filename: str) -> str:
    name = filename.replace(" ", "_")
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{name}"


def lookup(brand: str):
    """Returns (licence, url) or (reason, '') if nothing usable was found."""
    qid, _label = wikidata_qid(brand)
    if not qid:
        return "no-wikidata-entity", ""
    fn = logo_filename(qid)
    if not fn:
        return "no-logo-on-wikidata", ""
    return commons_licence(fn), file_url(fn)


def main(argv) -> int:
    if argv:
        brand = argv[0]
        lic, url = lookup(brand)
        print(f"{brand_slug(brand)}\t{lic}\t{url}")
        return 0

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    rows = ["# Review the LICENCE column before using any of these. Many simple",
            "# wordmarks are 'PD-textlogo' (free); others are non-free and up to",
            "# your own fair-use judgement. Copy rows you accept into sources.tsv",
            "# (keeping only slug<TAB>url), then run scripts/fetch_logos.py.",
            "# slug\tlicence\turl"]
    print("Querying Wikidata for official logos (P154) + Commons licences...\n")
    for brand, slug in all_brands():
        try:
            lic, url = lookup(brand)
        except Exception as exc:
            lic, url = f"error: {exc}", ""
        print(f"  {brand:30} {lic}")
        rows.append(f"{slug}\t{lic}\t{url}")
        time.sleep(0.3)  # be gentle with the public APIs
    SUGGESTED.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"\nWrote {SUGGESTED}. Review licences, copy acceptable rows into "
          f"{LOGO_DIR / 'sources.tsv'} (slug<TAB>url), then run "
          "scripts/fetch_logos.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
