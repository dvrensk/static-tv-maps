"""Geometry helpers: loading, projections, framing, Canary Islands inset."""

from pathlib import Path

import geopandas as gpd
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import polylabel

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# ETRS89 / UTM 30N: the standard projected CRS for peninsular Spain.
MAIN_CRS = "EPSG:25830"
# ETRS89 / UTM 28N for the Canary Islands, so the archipelago keeps its own
# undistorted shape before being translated into the main map frame.
CANARY_CRS = "EPSG:25828"

RATIO = 16 / 9


def load(name: str) -> gpd.GeoDataFrame:
    return gpd.read_file(PROCESSED / f"{name}.geojson")


def compute_frame(bounds, pad=0.04, ratio: float = RATIO):
    """Expand a (minx, miny, maxx, maxy) bounds tuple to a 16:9 frame.

    `pad` is either one fraction for all sides or per-side fractions
    (left, bottom, right, top) of the raw width/height."""
    minx, miny, maxx, maxy = bounds
    w, h = maxx - minx, maxy - miny
    if isinstance(pad, (int, float)):
        pad = (pad, pad, pad, pad)
    left, bottom, right, top = pad
    minx, maxx = minx - left * w, maxx + right * w
    miny, maxy = miny - bottom * h, maxy + top * h
    w, h = maxx - minx, maxy - miny
    if w / h < ratio:  # too tall: widen
        extra = h * ratio - w
        minx, maxx = minx - extra / 2, maxx + extra / 2
    else:  # too wide: heighten
        extra = w / ratio - h
        miny, maxy = miny - extra / 2, maxy + extra / 2
    return (minx, miny, maxx, maxy)


def frame_polygon(frame) -> Polygon:
    minx, miny, maxx, maxy = frame
    return Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)])


def place_canary(canary: gpd.GeoDataFrame, frame, margin_x=0.025, margin_y=0.045):
    """Project the Canary Islands in their own CRS and translate them to the
    lower-left corner of the frame (their true direction from the peninsula).

    Returns the translated GeoDataFrame (in main-map coordinates) and the
    inset rectangle (minx, miny, maxx, maxy) to draw around them.
    Both CRSs are metric UTM zones, so true relative scale is preserved.
    """
    can = canary.to_crs(CANARY_CRS).copy()
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    cx0, cy0, cx1, cy1 = can.total_bounds
    pad = 42_000  # metres of breathing room inside the inset box
    target_x = fx0 + margin_x * fw + pad
    target_y = fy0 + margin_y * fh + pad
    dx, dy = target_x - cx0, target_y - cy0
    can.geometry = can.geometry.apply(lambda g: affinity.translate(g, xoff=dx, yoff=dy))
    box = (cx0 + dx - pad, cy0 + dy - pad, cx1 + dx + pad, cy1 + dy + pad)
    return can, box


def label_point(geom, tol: float = 1500.0):
    """A good interior anchor for a label: pole of inaccessibility of the
    largest polygon of the geometry."""
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    try:
        p = polylabel(geom, tolerance=tol)
    except Exception:
        p = geom.representative_point()
    return p.x, p.y
