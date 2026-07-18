#!/usr/bin/env python3
"""Download and process the geodata used to render the maps.

Raw sources land in data/raw/ (gitignored). Processed, simplified GeoJSON
files land in data/processed/ and are committed to the repo, so rendering
maps does not require network access — only re-run this script to refresh
the sources.

Sources:
- Opendatasoft "georef-spain" datasets (derived from IGN, licence: Open
  Licence / CC-BY equivalent): autonomous communities, provinces and
  municipalities with official codes and names.
  https://public.opendatasoft.com/explore/?q=georef-spain
- Natural Earth 10m admin-0 countries (public domain), used for the
  neighbouring-country context (Portugal, France, Morocco, ...).
  https://www.naturalearthdata.com/
"""

import io
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

ODS = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets"
NE_COUNTRIES = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"

# Simplification tolerance in degrees. 0.001 deg is roughly 100 m — far below
# one pixel at 4000 px for a map of Spain (~370 m/px).
TOLERANCE = 0.001


def fetch(url: str, dest: Path, desc: str) -> Path:
    if dest.exists():
        print(f"  [cached] {dest.name}")
        return dest
    print(f"  downloading {desc} ...")
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"  -> {dest.name} ({len(resp.content) / 1e6:.1f} MB)")
    return dest


def simplify(gdf: gpd.GeoDataFrame, tolerance: float = TOLERANCE) -> gpd.GeoDataFrame:
    """Simplify a polygon coverage without creating gaps between neighbours."""
    import shapely

    gdf = gdf.copy()
    if hasattr(shapely, "coverage_simplify"):
        gdf.geometry = shapely.coverage_simplify(gdf.geometry.values, tolerance)
    else:  # older shapely: per-feature simplification (may leave hairline slivers)
        gdf.geometry = gdf.geometry.simplify(tolerance)
    return gdf


def dedupe_latest(gdf: gpd.GeoDataFrame, code_field: str) -> gpd.GeoDataFrame:
    """The georef datasets can carry one row per reference year; keep the latest."""
    if "year" in gdf.columns:
        gdf = gdf.sort_values("year").drop_duplicates(code_field, keep="last")
    return gdf


def process_communities() -> None:
    raw = fetch(
        f"{ODS}/georef-spain-comunidad-autonoma/exports/geojson",
        RAW / "georef-spain-comunidad-autonoma.geojson",
        "autonomous communities (Opendatasoft/IGN)",
    )
    gdf = gpd.read_file(raw)
    gdf = dedupe_latest(gdf, "acom_code")
    gdf = gdf[gdf["acom_code"] != "20"]  # "territory not associated to any autonomy"
    gdf = gdf[["acom_code", "acom_name", "geometry"]].sort_values("acom_code")
    gdf = simplify(gdf)
    out = PROCESSED / "comunidades.geojson"
    gdf.to_file(out, driver="GeoJSON")
    print(f"  wrote {out.name}: {len(gdf)} features")


def process_provinces() -> None:
    raw = fetch(
        f"{ODS}/georef-spain-provincia/exports/geojson",
        RAW / "georef-spain-provincia.geojson",
        "provinces (Opendatasoft/IGN)",
    )
    gdf = gpd.read_file(raw)
    gdf = dedupe_latest(gdf, "prov_code")
    gdf = gdf[gdf["prov_code"] != "54"]  # "territory not associated to any province"
    gdf = gdf[["prov_code", "prov_name", "acom_code", "acom_name", "geometry"]]
    gdf = gdf.sort_values("prov_code")
    gdf = simplify(gdf)
    out = PROCESSED / "provincias.geojson"
    gdf.to_file(out, driver="GeoJSON")
    print(f"  wrote {out.name}: {len(gdf)} features")


def process_asturias() -> None:
    raw = fetch(
        f"{ODS}/georef-spain-municipio/exports/geojson?where=prov_code%3D%2733%27",
        RAW / "georef-spain-municipio-asturias.geojson",
        "Asturias municipalities/concejos (Opendatasoft/IGN)",
    )
    gdf = gpd.read_file(raw)
    gdf = dedupe_latest(gdf, "mun_code")
    gdf = gdf[["mun_code", "mun_name", "geometry"]].sort_values("mun_code")
    gdf = simplify(gdf, tolerance=0.0003)  # Asturias maps zoom in much closer
    out = PROCESSED / "asturias_concejos.geojson"
    gdf.to_file(out, driver="GeoJSON")
    print(f"  wrote {out.name}: {len(gdf)} features")


def process_context_countries() -> None:
    raw = fetch(NE_COUNTRIES, RAW / "ne_10m_admin_0_countries.zip", "Natural Earth countries")
    gdf = gpd.read_file(f"zip://{raw}")
    keep = ["Portugal", "France", "Andorra", "Morocco", "Algeria", "Gibraltar", "Monaco"]
    gdf = gdf[gdf["NAME"].isin(keep)][["NAME", "geometry"]].rename(columns={"NAME": "name"})
    # Clip to a generous box around Iberia + Canaries so the file stays small.
    gdf = gdf.clip((-20.0, 25.0, 9.0, 47.5))
    gdf = simplify(gdf, tolerance=0.002)
    out = PROCESSED / "context_countries.geojson"
    gdf.to_file(out, driver="GeoJSON")
    print(f"  wrote {out.name}: {len(gdf)} features")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    print("Communities:")
    process_communities()
    print("Provinces:")
    process_provinces()
    print("Asturias concejos:")
    process_asturias()
    print("Context countries:")
    process_context_countries()
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
