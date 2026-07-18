"""Physical map of Spain: major rivers and mountain ranges."""

from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import LineString

from . import draw, geo
from .maps_spain import KM, _draw_country_labels, _project_lonlat, spain_scene

# Palette for the physical map.
LAND = "#efe8d8"           # parchment fill for all of Spain
LAND_EDGE = "#ddd4bf"      # very faint internal community borders
COAST = "#8a857a"          # dissolved outline of the country
RIVER = "#3f7fb5"
RIVER_FAINT = "#93b9d6"    # course outside Spain (through Portugal)
RANGE_FILL = "#c9a97e"
RANGE_ALPHA = 0.45
RANGE_LABEL = "#7a5c3d"


def _project_line(points):
    """A lon/lat polyline projected to the main map CRS."""
    return LineString([_project_lonlat(lon, lat) for lon, lat in points])


# ---------------------------------------------------------------------------
# Mountain ranges
# ---------------------------------------------------------------------------
# Natural Earth's geography_regions_polys only has polygons for the Pirineos,
# Cordillera Cantábrica, Sierra Morena and the Béticos ("Sierra Nevada", but
# the polygon actually spans the whole Penibética from Málaga to Almería).
# The remaining ranges are drawn as hand-placed capsules: a polyline along
# the range's crest, buffered a few tens of km. Coordinates are lon/lat of
# well-known summits/sierras along each axis.
HAND_RANGES = {
    # Sierra de Gata → Béjar → Gredos → Guadarrama → Somosierra/Ayllón
    "Sistema Central": ([(-6.85, 40.28), (-5.9, 40.32), (-5.2, 40.3),
                         (-4.4, 40.7), (-3.85, 40.95), (-3.35, 41.2)], 20),
    # Demanda → Urbión → Moncayo → Albarracín → Javalambre/Gúdar
    "Sistema Ibérico": ([(-3.1, 42.25), (-2.7, 42.0), (-1.85, 41.8),
                         (-1.6, 41.0), (-1.25, 40.4), (-0.7, 40.3)], 24),
    # Villuercas → Guadalupe → east toward Toledo
    "Montes de Toledo": ([(-5.4, 39.4), (-4.5, 39.42), (-3.7, 39.5)], 17),
    # Ourense/Lugo mountains: Manzaneda, O Courel, Ancares, Montes de León
    "Macizo Galaico": ([(-7.5, 42.35), (-7.1, 42.5), (-6.7, 42.45),
                        (-6.35, 42.25)], 28),
}


@dataclass
class RangeLabel:
    text: str
    lon: float
    lat: float
    rotation: float = 0.0
    size: float = 34


RANGE_LABELS = [
    RangeLabel("CORDILLERA CANTÁBRICA", -5.45, 43.08, 2, 34),
    RangeLabel("PIRINEOS", 0.55, 42.63, -4, 38),
    RangeLabel("MACIZO\nGALAICO", -6.95, 42.38, 0, 30),
    RangeLabel("SISTEMA CENTRAL", -4.85, 40.62, 17, 34),
    RangeLabel("SISTEMA IBÉRICO", -1.72, 41.38, -62, 34),
    RangeLabel("MONTES DE TOLEDO", -4.6, 39.47, -3, 30),
    RangeLabel("SIERRA MORENA", -5.0, 38.42, 3, 34),
    RangeLabel("SISTEMAS BÉTICOS", -3.6, 37.18, 12, 34),
]


# ---------------------------------------------------------------------------
# Rivers
# ---------------------------------------------------------------------------
# Where along its course each river name sits, and how the text is rotated.
# (lon, lat) is the label's centre; rotation in degrees, following the local
# direction of the stream.
@dataclass
class RiverLabel:
    lon: float
    lat: float
    rotation: float = 0.0
    size: float = 30


RIVER_LABELS = {
    "Miño": RiverLabel(-7.85, 42.93, -70),
    "Duero": RiverLabel(-4.05, 41.42, -6),
    "Ebro": RiverLabel(-2.05, 42.32, -38),
    "Tajo": RiverLabel(-5.6, 39.72, -6),
    "Guadiana": RiverLabel(-6.1, 38.98, -5),
    "Guadalquivir": RiverLabel(-5.3, 37.72, -25),
    "Genil": RiverLabel(-4.35, 37.28, 14, 28),
    "Segura": RiverLabel(-1.75, 38.2, -8, 28),
    "Júcar": RiverLabel(-1.45, 39.35, -12, 28),
    "Turia": RiverLabel(-1.02, 39.73, -50, 28),
}


def _spain_union(scene):
    """Dissolved peninsular Spain, for clipping mountains/rivers."""
    return scene["ccaa_pen"].union_all()


def map_spain_fisica():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    # Neutral parchment Spain with the faintest of community borders, plus a
    # single dissolved coastline/border outline.
    draw.draw_layer(ax, s["ccaa_pen"], LAND, LAND_EDGE, 1.0, zorder=2)
    spain = _spain_union(s)
    gpd.GeoSeries([spain.boundary], crs=geo.MAIN_CRS).plot(
        ax=ax, color=COAST, linewidth=2.2, zorder=3)

    # Canary inset: the archipelago has no major rivers; just the islands.
    draw.draw_inset_box(ax, s["canary_box"], label="Canarias")
    draw.draw_layer(ax, s["ccaa_can"], LAND, COAST, 1.6, zorder=4)

    # Mountain ranges: soft brown shading under the rivers, clipped to Spain.
    ranges = geo.load("mountains").to_crs(geo.MAIN_CRS)
    shapes = list(ranges.geometry)
    for pts, buffer_km in HAND_RANGES.values():
        shapes.append(_project_line(pts).buffer(buffer_km * KM))
    gpd.GeoSeries(shapes, crs=geo.MAIN_CRS).intersection(spain).plot(
        ax=ax, facecolor=RANGE_FILL, edgecolor="none", alpha=RANGE_ALPHA,
        zorder=5)

    # Rivers: full blue inside Spain, muted where the course continues
    # through Portugal to the Atlantic.
    rivers = geo.load("rivers").to_crs(geo.MAIN_CRS)
    inside = spain.buffer(2 * KM)
    rivers.geometry.intersection(inside).plot(
        ax=ax, color=RIVER, linewidth=3.4, zorder=6, capstyle="round")
    rivers.geometry.difference(inside).plot(
        ax=ax, color=RIVER_FAINT, linewidth=3.0, zorder=6, capstyle="round")

    # Labels.
    for name, spec in RIVER_LABELS.items():
        x, y = _project_lonlat(spec.lon, spec.lat)
        t = draw.halo_text(ax, x, y, name, spec.size, weight="semibold",
                           color=RIVER, halo=LAND, halo_width=5, zorder=8)
        t.set_rotation(spec.rotation)
    for r in RANGE_LABELS:
        x, y = _project_lonlat(r.lon, r.lat)
        t = draw.halo_text(ax, x, y, r.text, r.size, weight="extrabold",
                           color=RANGE_LABEL, halo=LAND, halo_width=5,
                           zorder=7)
        t.set_rotation(r.rotation)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "Ríos y montañas principales de España")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_fisica():
    return draw.save(map_spain_fisica(), "spain-fisica")
