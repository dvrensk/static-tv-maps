"""Spain map of the 30 most populated municipalities (INE 2025).

Neutral single-tone base map; numbered red dots sized by population tier and
a two-column ranked legend over the Atlantic.
"""

from dataclasses import dataclass

from . import cities, draw, geo, style
from .maps_spain import KM, _project_lonlat, spain_scene

LAND_FILL = "#efe8d8"        # soft parchment for every community
LAND_EDGE = "#c6bfb1"        # light internal community borders
COAST_EDGE = "#8f887b"       # darker dissolved outer coastline
DOT_FACE = "#b23a2e"         # warm red
DOT_EDGE = "#ffffff"

# Population tiers: (min population, dot ms, label size).
TIERS = [
    (1_000_000, 26, 40),
    (400_000, 20, 34),
    (0, 14, 29),
]

# PORTUGAL is moved north (horizontal, near Braga) because the usual
# vertical label sits exactly where the ranking legend goes.
COUNTRY_LABELS = [
    ("PORTUGAL", -8.1, 41.6, 36, 0),
    ("FRANCIA", 1.7, 43.85, 46, 0),
    ("MARRUECOS", -4.9, 35.02, 36, 0),
]

# Legend rows that would otherwise reach into Spanish territory (the
# Extremadura border bulges west to Cedillo) continue on a second line.
LEGEND_WRAPS = {
    "Las Palmas de Gran Canaria": ("Las Palmas de", "Gran Canaria"),
    "Jerez de la Frontera": ("Jerez de la", "Frontera"),
    "Santa Cruz de Tenerife": ("Santa Cruz de", "Tenerife"),
    "Castellón de la Plana": ("Castellón de la", "Plana"),
}


@dataclass
class CityLabel:
    dx: float = 0.0          # label offset from the dot, km
    dy: float = 0.0
    ha: str = "center"
    va: str = "center"
    # If set, draw a leader line from the dot to (dot + tx/ty km).
    tx: float | None = None
    ty: float | None = None
    wrap: str | None = None  # multi-line display name override
    size: float | None = None  # font size override (else the population tier)


CITY_LABELS = {
    "Madrid": CityLabel(dy=16, va="bottom"),
    "Barcelona": CityLabel(dx=16, ha="left"),                 # sea east
    "Valencia": CityLabel(dx=13, ha="left"),                  # sea east
    "Zaragoza": CityLabel(dy=13, va="bottom"),
    "Sevilla": CityLabel(dy=13, va="bottom"),
    "Málaga": CityLabel(dy=-13, va="top"),                    # sea south
    "Murcia": CityLabel(dx=-11, ha="right"),
    "Palma": CityLabel(dy=-13, va="top"),                     # bay south
    "Las Palmas de Gran Canaria": CityLabel(         # callout up-right, clear
        tx=28, ty=74, va="bottom", ha="left", size=25,   # of the Santa Cruz
        wrap="Las Palmas de\nGran Canaria"),              # label and box edge
    "Alicante": CityLabel(dx=10, ha="left"),                  # sea east
    "Bilbao": CityLabel(dy=8, va="bottom"),                   # sea above
    "Córdoba": CityLabel(dy=10, va="bottom"),
    "Valladolid": CityLabel(dy=10, va="bottom"),
    "Vigo": CityLabel(dx=-10, ha="right"),                    # sea west
    "Gijón": CityLabel(dy=11, va="bottom"),                   # sea above
    "Vitoria-Gasteiz": CityLabel(dy=-14, va="top"),
    "A Coruña": CityLabel(dx=-10, ha="right"),                # sea west
    "Elche": CityLabel(dx=-10, ha="right"),
    "Granada": CityLabel(dy=10, va="bottom"),
    "Oviedo": CityLabel(dy=-10, va="top"),
    "Cartagena": CityLabel(dy=-12, va="top"),                 # sea south
    "Jerez de la Frontera": CityLabel(dy=12, va="bottom"),
    "Santa Cruz de Tenerife": CityLabel(              # over sea NW of Tenerife
        dx=-52, dy=26, va="bottom", ha="left", size=25,
        wrap="Santa Cruz\nde Tenerife"),
    "Pamplona": CityLabel(dx=11, ha="left"),
    "Almería": CityLabel(dy=-12, va="top"),                   # sea south
    "San Sebastián": CityLabel(tx=-2, ty=55, va="bottom"),    # callout to sea
    "Castellón de la Plana": CityLabel(dx=11, ha="left"),     # sea east
    "Burgos": CityLabel(dy=-10, va="top"),
    "Santander": CityLabel(dy=14, va="bottom"),               # sea above
    "Albacete": CityLabel(dy=10, va="bottom"),
}


def _tier(pop):
    for floor, ms, size in TIERS:
        if pop >= floor:
            return ms, size
    return TIERS[-1][1:]


def _draw_country_labels(ax, frame):
    fx0, fy0, fx1, fy1 = frame
    for text, lon, lat, size, rotation in COUNTRY_LABELS:
        x, y = _project_lonlat(lon, lat)
        if fx0 < x < fx1 and fy0 < y < fy1:
            t = draw.halo_text(ax, x, y, text, size, weight="semibold",
                               color=style.NEIGHBOR_LABEL, halo_width=6,
                               zorder=5)
            t.set_rotation(rotation)


def map_spain_ciudades():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    # Neutral Spain: one soft tone, light community borders, darker coastline.
    draw.draw_layer(ax, s["ccaa_pen"], LAND_FILL, LAND_EDGE, 1.5, zorder=2)
    outline = s["ccaa_pen"].dissolve()
    draw.draw_layer(ax, outline, "none", COAST_EDGE, 2.5, zorder=3)

    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    draw.draw_layer(ax, s["ccaa_can"], LAND_FILL, COAST_EDGE, 1.8, zorder=4)

    # City points: peninsular ones directly, Canary ones through the inset
    # transform so they land on the transposed islands.
    pts = cities.load_points()
    can_pts = cities.load_points(geo.CANARY_CRS)
    canary_cities = {"Las Palmas de Gran Canaria", "Santa Cruz de Tenerife"}

    for rank, (name, pop) in enumerate(cities.BIG_CITIES, start=1):
        if name in canary_cities:
            x, y = geo.canary_xy(can_pts[name], s["canary_tf"])
        else:
            x, y = pts[name]
        ms, size = _tier(pop)
        draw.city_dot(ax, (x, y), size=ms, face=DOT_FACE, edge=DOT_EDGE)
        spec = CITY_LABELS[name]
        size = spec.size or size
        label = spec.wrap or name
        if spec.tx is not None:
            draw.numbered_callout(ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM),
                                  rank, label, size, ha=spec.ha, va=spec.va,
                                  badge_face=DOT_FACE)
        else:
            draw.numbered_label(ax, (x + spec.dx * KM, y + spec.dy * KM), rank,
                                label, size, ha=spec.ha, va=spec.va,
                                badge_face=DOT_FACE)

    # Ranking legend: two columns of 15 entries over the Atlantic, west of
    # Portugal. Long names continue on a second line (see LEGEND_WRAPS) so
    # no row reaches Spanish land.
    rows = []
    for i, (name, pop) in enumerate(cities.BIG_CITIES, start=1):
        p = cities.format_population(pop)
        if name in LEGEND_WRAPS:
            first, second = LEGEND_WRAPS[name]
            rows.append([(str(i), first), (None, f"{second} · {p}")])
        else:
            rows.append([(str(i), f"{name} · {p}")])
    col1 = [r for entry in rows[:15] for r in entry]
    col2 = [r for entry in rows[15:] for r in entry]
    draw.legend_column(ax, s["frame"], 0.030, 0.67, col1, size=26, leading=1.4)
    draw.legend_column(ax, s["frame"], 0.155, 0.67, col2, size=26, leading=1.4)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Los 30 municipios más poblados de España (INE 2025)\n"
                     "no se incluyen los municipios de las áreas "
                     "metropolitanas de Madrid, Barcelona y Tenerife")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_ciudades():
    return draw.save(map_spain_ciudades(), "spain-ciudades")
