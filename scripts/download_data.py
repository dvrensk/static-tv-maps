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
NE_PHYSICAL = "https://naciscdn.org/naturalearth/10m/physical"

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


# --- Physical geography (rivers + mountain ranges) -------------------------
#
# Rivers come from two Natural Earth 10m datasets: the worldwide
# rivers_lake_centerlines (which carries the six biggest Iberian rivers) and
# the rivers_europe supplement (which adds the Júcar, Segura, Genil and
# Turia). The worldwide file mixes languages in `name` (Tejo, Minho, ...) but
# `name_es` is reliably the Spanish name; the europe supplement's `name_es`
# is NOT reliable (e.g. the Guadiana Menor carries name_es "Guadalquivir"),
# so there we match on `name`, which for our four targets is already the
# Spanish form.

# Matched against `name_es` in ne_10m_rivers_lake_centerlines.
RIVERS_WORLD = {"Miño", "Duero", "Tajo", "Guadiana", "Guadalquivir", "Ebro"}
# Matched against `name` in ne_10m_rivers_europe.
RIVERS_EUROPE = {"Júcar", "Segura", "Genil", "Turia"}

# Mountain-range polygons in ne_10m_geography_regions_polys that exist for
# Spain (matched against NAME_ES). The Sistema Central, Sistema Ibérico,
# Montes de Toledo and Macizo Galaico have no polygon in Natural Earth; the
# physical map hand-places those (see tvmaps/maps_fisica.py).
MOUNTAIN_RANGES = {"Pirineos", "Cordillera Cantábrica", "Sierra Morena",
                   "Sierra Nevada"}

# Generous lon/lat box around the Iberian peninsula.
IBERIA_BOX = (-9.95, 35.7, 4.6, 44.3)


def process_physical() -> None:
    import pandas as pd
    from shapely.ops import linemerge

    world = fetch(f"{NE_PHYSICAL}/ne_10m_rivers_lake_centerlines.zip",
                  RAW / "ne_10m_rivers_lake_centerlines.zip",
                  "Natural Earth rivers (world)")
    europe = fetch(f"{NE_PHYSICAL}/ne_10m_rivers_europe.zip",
                   RAW / "ne_10m_rivers_europe.zip",
                   "Natural Earth rivers (europe supplement)")
    regions = fetch(f"{NE_PHYSICAL}/ne_10m_geography_regions_polys.zip",
                    RAW / "ne_10m_geography_regions_polys.zip",
                    "Natural Earth geography regions")

    gw = gpd.read_file(f"zip://{world}")
    gw = gw[gw["name_es"].isin(RIVERS_WORLD)]
    gw = gw[["name_es", "geometry"]].rename(columns={"name_es": "name"})
    ge = gpd.read_file(f"zip://{europe}!ne_10m_rivers_europe.shp")
    ge = ge[ge["name"].isin(RIVERS_EUROPE)][["name", "geometry"]]
    riv = gpd.GeoDataFrame(pd.concat([gw, ge], ignore_index=True), crs=gw.crs)
    riv = riv.clip(IBERIA_BOX)
    # One (Multi)LineString per river, main stem and reservoir centerlines
    # merged together.
    riv = riv.dissolve("name").reset_index()
    riv.geometry = riv.geometry.apply(
        lambda g: linemerge(g) if g.geom_type == "MultiLineString" else g)
    riv.geometry = riv.geometry.simplify(TOLERANCE)
    out = PROCESSED / "rivers.geojson"
    riv.sort_values("name").to_file(out, driver="GeoJSON")
    print(f"  wrote {out.name}: {len(riv)} rivers")

    gm = gpd.read_file(f"zip://{regions}")
    gm = gm[(gm["FEATURECLA"] == "Range/mtn") & gm["NAME_ES"].isin(MOUNTAIN_RANGES)]
    gm = gm[["NAME_ES", "geometry"]].rename(columns={"NAME_ES": "name"})
    gm = gm.clip(IBERIA_BOX)
    gm.geometry = gm.geometry.simplify(0.01)  # soft shaded blobs, keep them light
    out = PROCESSED / "mountains.geojson"
    gm.sort_values("name").to_file(out, driver="GeoJSON")
    print(f"  wrote {out.name}: {len(gm)} ranges")


# Cities and towns whose exact point locations the maps need. Geocoded once
# via Nominatim (OSM) and committed in data/processed/cities.geojson; the raw
# responses are cached per city under data/raw/nominatim/.
# key -> search query
CITY_QUERIES = {
    # Province capitals (the key is the display name used on the maps)
    "Vitoria-Gasteiz": "Vitoria-Gasteiz, España",
    "Albacete": "Albacete, España",
    "Alicante": "Alicante, España",
    "Almería": "Almería, España",
    "Ávila": "Ávila, España",
    "Badajoz": "Badajoz, España",
    "Palma": "Palma de Mallorca, España",
    "Barcelona": "Barcelona, España",
    "Burgos": "Burgos, España",
    "Cáceres": "Cáceres, España",
    "Cádiz": "Cádiz, España",
    "Castellón de la Plana": "Castellón de la Plana, España",
    "Ciudad Real": "Ciudad Real, España",
    "Córdoba": "Córdoba, España",
    "A Coruña": "A Coruña, España",
    "Cuenca": "Cuenca, España",
    "Girona": "Girona, España",
    "Granada": "Granada, España",
    "Guadalajara": "Guadalajara, España",
    "San Sebastián": "Donostia-San Sebastián, España",
    "Huelva": "Huelva, España",
    "Huesca": "Huesca, España",
    "Jaén": "Jaén, España",
    "León": "León, España",
    "Lleida": "Lleida, España",
    "Logroño": "Logroño, España",
    "Lugo": "Lugo, España",
    "Madrid": "Madrid, España",
    "Málaga": "Málaga, España",
    "Murcia": "Murcia, España",
    "Pamplona": "Pamplona, España",
    "Ourense": "Ourense, España",
    "Oviedo": "Oviedo, Asturias, España",
    "Palencia": "Palencia, España",
    "Las Palmas de Gran Canaria": "Las Palmas de Gran Canaria, España",
    "Pontevedra": "Pontevedra, España",
    "Salamanca": "Salamanca, España",
    "Santa Cruz de Tenerife": "Santa Cruz de Tenerife, España",
    "Santander": "Santander, España",
    "Segovia": "Segovia, España",
    "Sevilla": "Sevilla, España",
    "Soria": "Soria, España",
    "Tarragona": "Tarragona, España",
    "Teruel": "Teruel, España",
    "Toledo": "Toledo, España",
    "Valencia": "Valencia, España",
    "Valladolid": "Valladolid, España",
    "Bilbao": "Bilbao, España",
    "Zamora": "Zamora, España",
    "Zaragoza": "Zaragoza, España",
    "Ceuta": "Ceuta, España",
    "Melilla": "Melilla, España",
    # Community capitals not already above
    "Mérida": "Mérida, Badajoz, España",
    "Santiago de Compostela": "Santiago de Compostela, España",
    # Big non-capital cities
    "Vigo": "Vigo, España",
    "Gijón": "Gijón, Asturias, España",
    "Elche": "Elche, España",
    "Jerez de la Frontera": "Jerez de la Frontera, España",
    "Cartagena": "Cartagena, España",
    # Main towns of Asturias (capitals of the concejos over 10 000 inhabitants)
    "Avilés": "Avilés, Asturias, España",
    "Pola de Siero": "Pola de Siero, Asturias, España",
    "Langreo": "La Felguera, Langreo, Asturias, España",
    "Mieres": "Mieres del Camino, Asturias, España",
    "Piedras Blancas": "Piedras Blancas, Castrillón, Asturias, España",
    "Nubledo": "Nubledo, Corvera de Asturias, España",
    "Sotrondio": "Sotrondio, Asturias, España",
    "Villaviciosa": "Villaviciosa, Asturias, España",
    "Posada": "Posada, Llanera, Asturias, España",
    "Llanes": "Llanes, Asturias, España",
    "Pola de Laviana": "Pola de Laviana, Asturias, España",
    "Cangas del Narcea": "Cangas del Narcea, Asturias, España",
    "Luarca": "Luarca, Asturias, España",
    "Luanco": "Luanco, Asturias, España",
    "Pola de Lena": "Pola de Lena, Asturias, España",
    "Candás": "Candás, Asturias, España",
    "Cabañaquinta": "Cabañaquinta, Aller, Asturias, España",
}


def process_cities() -> None:
    import json
    import time

    cache_dir = RAW / "nominatim"
    cache_dir.mkdir(parents=True, exist_ok=True)
    features = []
    for key, query in CITY_QUERIES.items():
        cache = cache_dir / (key.replace(" ", "_").replace("/", "-") + ".json")
        if not cache.exists():
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": "static-tv-maps/1.0 (personal project)"},
                timeout=30,
            )
            resp.raise_for_status()
            cache.write_text(resp.text)
            time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
        hits = json.loads(cache.read_text())
        if not hits:
            print(f"  !! no result for {key} ({query})")
            continue
        lon, lat = float(hits[0]["lon"]), float(hits[0]["lat"])
        if not (-19.0 < lon < 5.0 and 27.0 < lat < 44.5):
            print(f"  !! suspicious location for {key}: {lat:.3f}, {lon:.3f}")
        features.append({
            "type": "Feature",
            "properties": {"key": key},
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
        })
    out = PROCESSED / "cities.geojson"
    out.write_text(json.dumps(
        {"type": "FeatureCollection", "features": features},
        ensure_ascii=False, indent=None))
    print(f"  wrote {out.name}: {len(features)} cities")


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
    print("Physical (rivers + mountain ranges):")
    process_physical()
    print("Cities:")
    process_cities()
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
