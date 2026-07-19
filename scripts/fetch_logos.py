#!/usr/bin/env python3
"""Save company logos into assets/logos/ for the spain-marcas-logos map.

You choose the sources; this only downloads the URLs you give it and saves
each under the exact <slug>.png filename the map expects (converting webp/SVG
to PNG so matplotlib can read them). It never picks sources for you.

Logo artwork is copyrighted/trademarked and is NOT part of this repo:
assets/logos/ is gitignored, so whatever you put there stays local.

Usage:
    # 1. See every brand and the filename the map looks for:
    python scripts/fetch_logos.py --list

    # 2. Write a template you fill in with URLs (one row per brand):
    python scripts/fetch_logos.py --init
    #    ...edit assets/logos/sources.tsv, pasting a URL next to each brand...

    # 3. Download everything you filled in:
    python scripts/fetch_logos.py

    # Or grab a single logo directly:
    python scripts/fetch_logos.py "El Corte Inglés" https://example.com/logo.png

Then re-render:  python generate.py spain-marcas-logos
"""

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tvmaps.maps_marcas import HUBS
from tvmaps.maps_marcas_logos import LOGO_DIR, brand_slug

SOURCES = LOGO_DIR / "sources.tsv"
HEADERS = {"User-Agent": "Mozilla/5.0 (static-tv-maps logo fetcher)"}


def all_brands():
    """[(brand name, slug)] for every brand on the map, in map order."""
    seen, out = set(), []
    for hub in HUBS:
        for brand in hub.brands:
            slug = brand_slug(brand)
            if slug not in seen:
                seen.add(slug)
                out.append((brand, slug))
    return out


def resolve_slug(token: str) -> str:
    """Accept either an exact brand name or an already-slugged token."""
    token = token.strip()
    by_slug = {s: s for _b, s in all_brands()}
    if token in by_slug:
        return token
    return brand_slug(token)


def _save_as_png(content: bytes, content_type: str, url: str, slug: str) -> Path:
    """Write bytes to assets/logos/<slug>.png, converting when needed."""
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    ext = ""
    ct = (content_type or "").lower()
    low = url.lower()
    if "png" in ct or low.endswith(".png"):
        ext = "png"
    elif "jpeg" in ct or "jpg" in ct or low.endswith((".jpg", ".jpeg")):
        ext = "jpg"
    elif "webp" in ct or low.endswith(".webp"):
        ext = "webp"
    elif "svg" in ct or low.endswith(".svg"):
        ext = "svg"

    dest = LOGO_DIR / f"{slug}.png"
    if ext in ("png", "jpg"):
        # The map reads .png/.jpg/.jpeg directly; keep the real extension.
        out = LOGO_DIR / f"{slug}.{ext}"
        out.write_bytes(content)
        return out
    if ext == "webp":
        from io import BytesIO

        from PIL import Image

        Image.open(BytesIO(content)).convert("RGBA").save(dest)
        return dest
    if ext == "svg":
        try:
            import cairosvg

            cairosvg.svg2png(bytestring=content, write_to=str(dest),
                             output_height=256)
            return dest
        except Exception as exc:
            svg = LOGO_DIR / f"{slug}.svg"
            svg.write_bytes(content)
            raise RuntimeError(
                f"saved {svg.name} but could not convert SVG to PNG ({exc}); "
                "install cairosvg or supply a PNG") from exc
    # Unknown type: trust the bytes are a raster and let PIL sniff it.
    from io import BytesIO

    from PIL import Image

    Image.open(BytesIO(content)).convert("RGBA").save(dest)
    return dest


def fetch_one(brand_or_slug: str, url: str) -> Path:
    slug = resolve_slug(brand_or_slug)
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return _save_as_png(resp.content, resp.headers.get("content-type", ""),
                        url, slug)


def cmd_list() -> int:
    print(f"{'brand':30}  filename")
    print(f"{'-' * 30}  {'-' * 24}")
    for brand, slug in all_brands():
        print(f"{brand:30}  {slug}.png")
    print(f"\n{len(all_brands())} brands. Drop files in {LOGO_DIR}/")
    return 0


def cmd_init(force: bool = False) -> int:
    if SOURCES.exists() and not force:
        print(f"{SOURCES} already exists (use --force to overwrite).")
        return 1
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# One row per brand: <slug><TAB><logo URL>.  Lines starting with # are",
        "# ignored. Paste a URL next to the brands you want, then run:",
        "#     python scripts/fetch_logos.py",
        "# You choose the sources (official press kits, Wikimedia Commons — many",
        "# simple wordmark logos there are public-domain 'PD-textlogo').",
        "",
    ]
    for brand, slug in all_brands():
        lines.append(f"{slug}\t")
    SOURCES.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote template {SOURCES} with {len(all_brands())} brands. "
          "Fill in URLs, then run: python scripts/fetch_logos.py")
    return 0


def cmd_download() -> int:
    if not SOURCES.exists():
        print(f"No {SOURCES}. Run 'python scripts/fetch_logos.py --init' first.")
        return 1
    rows = []
    for raw in SOURCES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t") if "\t" in line else line.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            continue
        rows.append((parts[0].strip(), parts[1].strip()))
    if not rows:
        print(f"No URLs filled in {SOURCES} yet.")
        return 1
    ok, fail = 0, 0
    for token, url in rows:
        try:
            dest = fetch_one(token, url)
            print(f"  ✓ {token:28} -> {dest.name}")
            ok += 1
        except Exception as exc:
            print(f"  ✗ {token:28} {exc}")
            fail += 1
    have = {p.stem for p in LOGO_DIR.glob("*") if p.suffix in (".png", ".jpg", ".jpeg")}
    missing = [s for _b, s in all_brands() if s not in have]
    print(f"\nDownloaded {ok}, failed {fail}. "
          f"{len(missing)} brand(s) still show a colour chip"
          + (f": {', '.join(missing)}" if missing else "."))
    return 0 if fail == 0 else 1


def main(argv) -> int:
    if argv and argv[0] == "--list":
        return cmd_list()
    if argv and argv[0] == "--init":
        return cmd_init(force="--force" in argv)
    if len(argv) == 2:
        try:
            dest = fetch_one(argv[0], argv[1])
            print(f"Saved {dest}")
            return 0
        except Exception as exc:
            print(f"Failed: {exc}")
            return 1
    if not argv:
        return cmd_download()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
