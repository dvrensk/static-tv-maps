"""River maps of Spain: the twenty rivers a schoolchild learns, and the
rivers together with the cities they flow through ("Sevilla está en el
Guadalquivir").

Both maps reuse the parchment style of the physical map (maps_fisica) and
read data/processed/rivers20.geojson (see process_rivers20 in
scripts/download_data.py for how the courses were extracted and which
Natural Earth mislabelings were corrected).
"""

from dataclasses import dataclass

import geopandas as gpd

from . import cities, draw, geo
from .maps_fisica import (COAST, HAND_RANGES, LAND, LAND_EDGE, RANGE_ALPHA,
                          RANGE_FILL, RIVER, RIVER_FAINT, _project_line,
                          _spain_union)
from .maps_spain import KM, _draw_country_labels, _project_lonlat, spain_scene

# Tributaries in a lighter blue than the main stems, but clearly stronger
# than RIVER_FAINT (reserved for courses through Portugal).
RIVER_TRIB = "#6b9cc7"

MAIN_LW = 3.6
TRIB_LW = 2.7


# ---------------------------------------------------------------------------
# The twenty rivers
# ---------------------------------------------------------------------------
# Where along its course each river's name sits; rotation follows the local
# direction of the stream. `main` selects color/width: sea-reaching stems in
# full blue, tributaries slightly thinner and lighter.
@dataclass
class RiverSpec:
    lon: float
    lat: float
    rotation: float = 0.0
    size: float = 32
    main: bool = True


RIOS_LABELS = {
    # Vertiente cantábrica
    "Nalón": RiverSpec(-5.72, 43.42, 8, 27),
    # Vertiente atlántica
    "Miño": RiverSpec(-7.87, 42.93, -70),
    "Sil": RiverSpec(-6.72, 42.62, 38, 27, main=False),
    "Duero": RiverSpec(-4.05, 41.42, -6),
    "Esla": RiverSpec(-5.95, 42.35, -75, 27, main=False),
    "Pisuerga": RiverSpec(-4.48, 42.45, -80, 27, main=False),
    "Tormes": RiverSpec(-5.95, 40.92, -35, 27, main=False),
    "Tajo": RiverSpec(-5.6, 39.72, -6),
    "Guadiana": RiverSpec(-6.1, 38.98, -5),
    "Guadalquivir": RiverSpec(-5.3, 37.72, -25),
    "Genil": RiverSpec(-4.35, 37.28, 14, 27, main=False),
    # Vertiente mediterránea
    "Ebro": RiverSpec(-2.05, 42.32, -38),
    "Aragón": RiverSpec(-1.15, 42.62, 22, 27, main=False),
    "Jalón": RiverSpec(-1.33, 41.56, 35, 27, main=False),
    "Cinca": RiverSpec(0.04, 42.25, -72, 27, main=False),
    "Segre": RiverSpec(1.18, 42.0, 40, 27, main=False),
    "Mijares": RiverSpec(-0.33, 40.10, -32, 27),
    "Turia": RiverSpec(-1.13, 39.70, -50, 27),
    "Júcar": RiverSpec(-1.45, 39.35, -12),
    "Segura": RiverSpec(-1.75, 38.2, -8),
}


# Range names, hand-tuned again for this map: with twice as many rivers the
# fisica positions collide (Macizo Galaico with the Sil, the Cordillera
# Cantábrica with the Nalón), so this module owns its own copies.
@dataclass
class RangeSpec:
    text: str
    lon: float
    lat: float
    rotation: float = 0.0
    size: float = 30


RANGE_LABELS_RIOS = [
    RangeSpec("CORDILLERA CANTÁBRICA", -5.35, 43.03, 2, 30),
    RangeSpec("PIRINEOS", 0.55, 42.63, -4, 32),
    RangeSpec("MACIZO\nGALAICO", -7.05, 42.16, 0, 27),
    RangeSpec("SISTEMA CENTRAL", -4.5, 40.75, 17, 30),
    RangeSpec("SISTEMA IBÉRICO", -2.3, 40.62, -60, 30),
    RangeSpec("MONTES DE TOLEDO", -4.6, 39.47, -3, 27),
    RangeSpec("SIERRA MORENA", -5.0, 38.42, 3, 30),
    RangeSpec("SISTEMAS BÉTICOS", -3.4, 37.05, 12, 30),
]


def _parchment_base(s, ax):
    """Parchment Spain, dissolved coastline and the Canary inset; returns
    the dissolved Spain polygon used for clipping."""
    draw.draw_context(ax, s["countries"])
    draw.draw_layer(ax, s["ccaa_pen"], LAND, LAND_EDGE, 1.0, zorder=2)
    spain = _spain_union(s)
    gpd.GeoSeries([spain.boundary], crs=geo.MAIN_CRS).plot(
        ax=ax, color=COAST, linewidth=2.2, zorder=3)
    draw.draw_inset_box(ax, s["canary_box"], label="Canarias")
    draw.draw_layer(ax, s["ccaa_can"], LAND, COAST, 1.6, zorder=4)
    return spain


def _draw_rivers(ax, riv, spain, specs):
    """Rivers colored by class, muted where the course leaves Spain."""
    inside = spain.buffer(2 * KM)
    for _, row in riv.iterrows():
        spec = specs.get(row["name"])
        if spec is None:
            continue
        color = RIVER if spec.main else RIVER_TRIB
        lw = MAIN_LW if spec.main else TRIB_LW
        gpd.GeoSeries([row.geometry.intersection(inside)]).plot(
            ax=ax, color=color, linewidth=lw, zorder=6, capstyle="round")
        out = row.geometry.difference(inside)
        if not out.is_empty:
            gpd.GeoSeries([out]).plot(
                ax=ax, color=RIVER_FAINT, linewidth=lw - 0.4, zorder=6,
                capstyle="round")


def _label_rivers(ax, specs):
    for name, spec in specs.items():
        x, y = _project_lonlat(spec.lon, spec.lat)
        color = RIVER if spec.main else RIVER_TRIB
        t = draw.halo_text(ax, x, y, name, spec.size, weight="semibold",
                           color=color, halo=LAND, halo_width=5, zorder=8)
        t.set_rotation(spec.rotation)


def map_spain_rios():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    spain = _parchment_base(s, ax)

    # Mountain shading under the rivers, as in the physical map.
    ranges = geo.load("mountains").to_crs(geo.MAIN_CRS)
    shapes = list(ranges.geometry)
    for pts, buffer_km in HAND_RANGES.values():
        shapes.append(_project_line(pts).buffer(buffer_km * KM))
    gpd.GeoSeries(shapes, crs=geo.MAIN_CRS).intersection(spain).plot(
        ax=ax, facecolor=RANGE_FILL, edgecolor="none", alpha=RANGE_ALPHA,
        zorder=5)

    riv = geo.load("rivers20").to_crs(geo.MAIN_CRS)
    _draw_rivers(ax, riv, spain, RIOS_LABELS)
    gpd.GeoSeries([_project_line(GUADALQUIVIR_MOUTH)], crs=geo.MAIN_CRS).plot(
        ax=ax, color=RIVER, linewidth=MAIN_LW, zorder=6, capstyle="round")
    _label_rivers(ax, RIOS_LABELS)

    from .maps_fisica import RANGE_LABEL
    for r in RANGE_LABELS_RIOS:
        x, y = _project_lonlat(r.lon, r.lat)
        t = draw.halo_text(ax, x, y, r.text, r.size, weight="extrabold",
                           color=RANGE_LABEL, halo=LAND, halo_width=5,
                           zorder=7)
        t.set_rotation(r.rotation)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "Los ríos de España y sus montañas")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_rios():
    return draw.save(map_spain_rios(), "spain-rios")


# ---------------------------------------------------------------------------
# Rivers and the cities they flow through
# ---------------------------------------------------------------------------

# Rivers drawn on the cities map: only those with a famous city pairing.
# (No Miño: NE's simplified course runs ~30 km west of Ourense, so that
# pairing would look wrong and is left out.)
# Label positions retuned so the names keep clear of the city dots.
CIUDADES_RIVER_LABELS = {
    "Duero": RiverSpec(-4.05, 41.42, -6),
    "Pisuerga": RiverSpec(-4.48, 42.45, -80, 27, main=False),
    "Tormes": RiverSpec(-5.45, 40.55, -35, 27, main=False),
    "Tajo": RiverSpec(-5.35, 39.72, -6),
    "Guadiana": RiverSpec(-4.6, 39.28, 0),
    "Guadalquivir": RiverSpec(-5.35, 37.75, -25),
    "Genil": RiverSpec(-4.45, 37.3, 14, 27, main=False),
    "Ebro": RiverSpec(-3.2, 42.72, -10),
    "Turia": RiverSpec(-1.13, 39.70, -50, 27),
    "Segura": RiverSpec(-1.75, 38.2, -8),
}

# Natural Earth's Tajo centerline stops near Golegã (-8.77, 39.10); continue
# it by hand down the real course past Vila Franca de Xira to the Lisboa
# estuary so the Lisboa dot sits on its river. Drawn muted like every other
# Portuguese reach.
TAJO_ESTUARIO = [(-8.77, 39.10), (-8.88, 39.05), (-8.99, 38.95),
                 (-9.04, 38.86), (-9.09, 38.78), (-9.13, 38.72)]

# Natural Earth's Guadalquivir centerline stops in the marshes near La Puebla
# (-6.20, 36.93), ~15 km short of the real Atlantic mouth at Sanlúcar de
# Barrameda; extend it by hand down the estuary so it reaches the sea.
GUADALQUIVIR_MOUTH = [(-6.195, 36.93), (-6.26, 36.90), (-6.32, 36.85),
                      (-6.36, 36.80), (-6.38, 36.77)]

# The Nervión (Bilbao) and Llobregat (Barcelona) are famous city rivers but
# too small for Natural Earth's 10 m dataset, so their courses are traced by
# hand from source through the named towns to the mouth. Both lie entirely in
# Spain, so they draw in full blue like the other main stems.
HAND_RIVERS = {
    # source Delika → Orduña → Bilbao → mouth between Portugalete and Getxo
    "Nervión": ([(-2.98, 42.95), (-2.995, 43.05), (-3.0, 43.13),
                 (-2.97, 43.19), (-2.935, 43.26), (-2.99, 43.32),
                 (-3.02, 43.36)],
                RiverSpec(-3.27, 43.05, -60, 26)),
    # source Castellar de n'Hug → Berga → Manresa → Martorell → El Prat delta
    "Llobregat": ([(2.0, 42.26), (1.87, 42.1), (1.83, 41.85), (1.83, 41.72),
                   (1.9, 41.55), (1.93, 41.47), (2.03, 41.38), (2.11, 41.32),
                   (2.138, 41.298)],
                  RiverSpec(1.66, 41.68, -70, 27)),
    # Congost headwater → Granollers → Montcada → mouth NE of Barcelona, so
    # the city sits between its two rivers.
    "Besòs": ([(2.38, 41.77), (2.32, 41.68), (2.29, 41.61), (2.23, 41.52),
               (2.19, 41.47), (2.22, 41.44), (2.235, 41.418)],
              RiverSpec(2.45, 41.62, -58, 25)),
}

# Cities missing from data/processed/cities.geojson (the two Portuguese
# river mouths the user wants on the map), hardcoded lon/lat.
EXTRA_CITIES = {
    "Lisboa": (-9.1393, 38.7223),
    "Oporto": (-8.6291, 41.1579),
}


@dataclass
class CitySpec:
    dx: float = 0.0       # label offset from the dot, km
    dy: float = 12.0
    ha: str = "center"
    size: float = 30


# City -> label placement. Every pairing here was checked: the city really
# sits on (or at the mouth of) the river drawn on this map.
CIUDADES = {
    # Ebro
    "Zaragoza": CitySpec(0, 14),
    "Logroño": CitySpec(0, 14),
    # Nervión / Llobregat (hand-traced courses)
    "Bilbao": CitySpec(0, 15),
    "Barcelona": CitySpec(15, -2, ha="left"),
    # Turia / Segura
    "Valencia": CitySpec(14, -4, ha="left"),
    "Murcia": CitySpec(0, -17),
    # Guadalquivir / Genil
    "Sevilla": CitySpec(-14, -4, ha="right"),
    "Córdoba": CitySpec(0, 15),
    "Granada": CitySpec(12, -12, ha="left"),
    # Guadiana
    "Mérida": CitySpec(12, 12, ha="left"),
    "Badajoz": CitySpec(-12, 12, ha="right"),
    # Tajo
    "Toledo": CitySpec(0, -17),
    # Duero basin
    "Valladolid": CitySpec(14, 0, ha="left"),
    "Salamanca": CitySpec(0, 14),
    "Zamora": CitySpec(0, 14),
    # Miño
    "Ourense": CitySpec(0, 14),
    # Portuguese mouths (explicitly wanted despite the grey context)
    "Lisboa": CitySpec(12, -10, ha="left"),
    "Oporto": CitySpec(0, 14),
}


def map_spain_rios_ciudades():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    spain = _parchment_base(s, ax)

    riv = geo.load("rivers20").to_crs(geo.MAIN_CRS)
    riv = riv[riv["name"].isin(CIUDADES_RIVER_LABELS)]
    _draw_rivers(ax, riv, spain, CIUDADES_RIVER_LABELS)
    _label_rivers(ax, CIUDADES_RIVER_LABELS)

    # Hand-traced Nervión and Llobregat, plus the muted Tajo estuary to Lisboa.
    for name, (course, spec) in HAND_RIVERS.items():
        gpd.GeoSeries([_project_line(course)], crs=geo.MAIN_CRS).plot(
            ax=ax, color=RIVER, linewidth=MAIN_LW, zorder=6, capstyle="round")
        _label_rivers(ax, {name: spec})
    gpd.GeoSeries([_project_line(TAJO_ESTUARIO)], crs=geo.MAIN_CRS).plot(
        ax=ax, color=RIVER_FAINT, linewidth=MAIN_LW - 0.4, zorder=6,
        capstyle="round")
    gpd.GeoSeries([_project_line(GUADALQUIVIR_MOUTH)], crs=geo.MAIN_CRS).plot(
        ax=ax, color=RIVER, linewidth=MAIN_LW, zorder=6, capstyle="round")

    pts = cities.load_points()
    for key, (lon, lat) in EXTRA_CITIES.items():
        pts[key] = _project_lonlat(lon, lat)
    for key, spec in CIUDADES.items():
        x, y = pts[key]
        draw.city_dot(ax, (x, y), size=14, zorder=9)
        draw.halo_text(ax, x + spec.dx * KM, y + spec.dy * KM, key,
                       spec.size, weight="extrabold", va="center",
                       ha=spec.ha, zorder=10)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "Ríos y las ciudades que bañan")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_rios_ciudades():
    return draw.save(map_spain_rios_ciudades(), "spain-rios-ciudades")
