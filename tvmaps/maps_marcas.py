"""Spain map of well-known commercial brands at their headquarter cities.

A neutral parchment base (borrowed from maps_productos) with one dot per
headquarter town and a small stacked label listing the brand(s) from there.
The whole point is the *geographic spread*: the great Spanish brands are
scattered around the periphery (Galicia, País Vasco, Cataluña, Levante,
Andalucía, Baleares...), not piled up in Madrid — so Madrid is deliberately
kept to a handful of names and every coastal hub throws its label out over
the sea with a leader line.

Each hub's HQ city was verified individually (see module notes). Where a
famous brand belongs to a group, both are shown (e.g. González Byass ·
Tío Pepe). Dense hubs (Barcelona, Bilbao, the Cádiz bay, Mallorca) fan their
labels into open water so nothing collides.
"""

from dataclasses import dataclass

from . import draw, geo, style
from .maps_productos import _base_map
from .maps_spain import KM, _draw_country_labels, _project_lonlat, spain_scene

DOT_FACE = "#33566e"     # corporate slate blue (distinct from the red cities map)
DOT_EDGE = "#ffffff"
CITY_COLOR = "#6f6a61"   # muted caption grey for the place name
BRAND_COLOR = "#24221d"  # near-black for the brand names
LEADER = "#7a746a"

CITY_SIZE = 25           # place-name caption (pt); >= 24 pt / 33 px minimum
BRAND_SIZE = 30          # brand names (pt)
LINE = 1.30              # line leading


@dataclass
class Hub:
    """A headquarter town: one dot, a place caption and its brand names."""
    city: str
    lonlat: tuple            # (lon, lat) of the dot
    brands: list             # brand display strings, drawn stacked
    tx: float = 0.0          # label-block offset from the dot, km (+E, +N)
    ty: float = 0.0
    ha: str = "left"         # text alignment of the block
    leader: bool = True
    city_size: float = CITY_SIZE
    brand_size: float = BRAND_SIZE


# Placed roughly N->S within each region. Coordinates are the HQ municipality;
# a few labels name both the municipality and the better-known nearby city.
HUBS = [
    # --- Galicia (Atlántico al oeste) --------------------------------------
    Hub("A Coruña · Arteixo", (-8.407, 43.366),
        ["Inditex · Zara", "Estrella Galicia"],
        tx=-175, ty=100, ha="right"),
    Hub("Redondela · Vigo", (-8.660, 42.283), ["Pescanova"],
        tx=-170, ty=-8, ha="right"),

    # --- Cornisa cantábrica -------------------------------------------------
    Hub("Siero", (-5.790, 43.362), ["Central Lechera Asturiana"],
        tx=-55, ty=116, ha="center"),
    Hub("Santander", (-3.807, 43.462), ["Banco Santander"],
        tx=0, ty=90, ha="center"),
    Hub("Bilbao", (-2.935, 43.263), ["BBVA", "Iberdrola"],
        tx=55, ty=104, ha="center"),
    Hub("Arrasate · Mondragón", (-2.490, 43.062),
        ["Corporación Mondragón", "Fagor"],
        tx=105, ty=66, ha="left"),

    # --- Castilla y León / Aragón ------------------------------------------
    Hub("Burgos", (-3.700, 42.343), ["Grupo Antolín", "Campofrío"],
        tx=-105, ty=-18, ha="right"),
    Hub("Zaragoza", (-0.877, 41.650), ["Pikolin"],
        tx=15, ty=92, ha="center"),

    # --- Cataluña (Mediterráneo al este; el interior a poniente) -----------
    Hub("Manresa", (1.830, 41.727), ["Tous"],
        tx=55, ty=100, ha="left"),
    Hub("Palau-solità", (2.187, 41.585), ["Mango"],
        tx=150, ty=48, ha="left"),
    Hub("Barcelona", (2.173, 41.387),
        ["Estrella Damm", "Puig", "Cola Cao", "Gallina Blanca"],
        tx=140, ty=28, ha="left"),
    Hub("Martorell", (1.930, 41.474), ["SEAT"],
        tx=-140, ty=-12, ha="right"),
    Hub("Sant Sadurní", (1.788, 41.427), ["Freixenet", "Codorníu"],
        tx=-125, ty=-88, ha="right"),
    Hub("Gavà", (1.990, 41.305), ["Roca"],
        tx=150, ty=-90, ha="left"),

    # --- Comunidad Valenciana ----------------------------------------------
    Hub("Vila-real", (-0.101, 39.938), ["Porcelanosa"],
        tx=135, ty=48, ha="left"),
    Hub("Valencia", (-0.363, 39.505), ["Mercadona", "Lladró"],
        tx=125, ty=-12, ha="left"),

    # --- Murcia -------------------------------------------------------------
    Hub("Jumilla", (-1.325, 38.479), ["García Carrión", "Don Simón"],
        tx=-100, ty=38, ha="right"),
    Hub("Alhama de Murcia", (-1.423, 37.851), ["ElPozo"],
        tx=70, ty=-58, ha="left"),

    # --- Andalucía (bahía de Cádiz, Atlántico al oeste) --------------------
    # The Gulf of Cádiz to the west is taken up by the Canary inset, so these
    # two (very close) hubs throw their labels inland over empty Andalucía.
    Hub("Jerez de la Frontera", (-6.137, 36.686),
        ["González Byass", "Tío Pepe"],
        tx=25, ty=62, ha="center"),
    Hub("El Puerto de Santa María", (-6.233, 36.594), ["Osborne"],
        tx=85, ty=-10, ha="left"),

    # --- Illes Balears ------------------------------------------------------
    Hub("Inca", (2.909, 39.720), ["Camper"],
        tx=105, ty=-2, ha="left"),
    Hub("Palma", (2.650, 39.570), ["Meliá"],
        tx=-10, ty=-64, ha="center"),

    # --- Madrid (a propósito, sólo unas pocas) ------------------------------
    Hub("Madrid", (-3.703, 40.417),
        ["El Corte Inglés", "Repsol", "Telefónica", "Iberia", "Mahou"],
        tx=40, ty=-18, ha="left"),
]


def _draw_hub(ax, frame, hub):
    x, y = _project_lonlat(*hub.lonlat)
    bx, by = x + hub.tx * KM, y + hub.ty * KM   # by = top of the text block
    dperpx = (frame[2] - frame[0]) / style.WIDTH_PX

    def lh(size):
        return size * LINE * (style.DPI / 72) * dperpx

    total = lh(hub.city_size) + len(hub.brands) * lh(hub.brand_size)

    if hub.leader and (hub.tx or hub.ty):
        ax.annotate("", xy=(x, y), xytext=(bx, by - total / 2), zorder=7,
                    arrowprops=dict(arrowstyle="-", color=LEADER,
                                    linewidth=2.2, shrinkA=7, shrinkB=7))

    cy = by
    draw.halo_text(ax, bx, cy, hub.city, hub.city_size, weight="semibold",
                   color=CITY_COLOR, ha=hub.ha, va="top", halo_width=5,
                   zorder=12)
    cy -= lh(hub.city_size)
    for name in hub.brands:
        draw.halo_text(ax, bx, cy, name, hub.brand_size, weight="extrabold",
                       color=BRAND_COLOR, ha=hub.ha, va="top", halo_width=6,
                       zorder=12)
        cy -= lh(hub.brand_size)

    draw.city_dot(ax, (x, y), size=13, face=DOT_FACE, edge=DOT_EDGE, zorder=9)


def map_spain_marcas():
    s = spain_scene()
    fig, ax, _spain = _base_map(s)

    for hub in HUBS:
        _draw_hub(ax, s["frame"], hub)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Marcas de España · grandes empresas y de dónde son")
    draw.draw_attribution(ax, s["frame"], "Datos: elaboración propia")
    return fig


def render_spain_marcas():
    return draw.save(map_spain_marcas(), "spain-marcas")
