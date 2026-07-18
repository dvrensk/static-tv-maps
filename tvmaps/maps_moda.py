"""Spain map of fashion: houses, designers, footwear and jewellery.

A neutral parchment Spain (like maps_ciudades) with a dot at each firm's home
city or founder's birthplace, deliberately spread across the country — Galicia
(Inditex, Adolfo Domínguez...), Cataluña (Mango, Desigual, Tous...), País Vasco
(Balenciaga, Paco Rabanne), Madrid (Loewe, Tendam...), the Elche/Inca footwear
tradition and Manolo Blahnik in the Canary inset.

Firms are colour-coded by kind (moda / calzado / joyería). Cities that host
several firms carry a small stacked list; coastal labels sit over the sea.
All locations were verified brand by brand (see module history).
"""

from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import Point

from . import draw, geo, style
from .maps_ciudades import COAST_EDGE, LAND_EDGE, LAND_FILL
from .maps_spain import KM, _draw_country_labels, _project_lonlat, spain_scene

LEADER = "#6b675f"
CITY_COLOR = "#6b675f"

# kind -> (dot fill, brand-name colour)
KIND = {
    "moda":    ("#b0367a", "#7c2158"),   # fashion houses & designers — plum
    "calzado": ("#a25a26", "#6f3d16"),   # footwear — leather brown
    "joyeria": ("#1f8a7a", "#116152"),   # jewellery — emerald
}

KIND_LEGEND = [
    ("moda", "Moda y diseño"),
    ("calzado", "Calzado"),
    ("joyeria", "Joyería"),
]


@dataclass
class Firm:
    lat: float
    lon: float
    city: str
    brands: list
    kind: str = "moda"
    tx: float = 0.0          # label-anchor offset from the dot, km
    ty: float = 0.0
    ha: str = "left"
    va: str = "center"
    leader: bool = True
    dot: float = 15.0
    brand_size: float = 32.0
    city_size: float = 24.0


# Peninsula + Balearic firms. Verified home city / HQ / founder birthplace.
FIRMS = [
    # --- Galicia -----------------------------------------------------------
    Firm(43.305, -8.512, "Arteixo · A Coruña", ["Zara", "Inditex"],
         tx=-60, ty=35, ha="right", va="bottom", dot=20, brand_size=34),
    Firm(42.231, -8.712, "Vigo", ["Bimba y Lola"],
         tx=-55, ty=-8, ha="right", va="center"),
    Firm(42.336, -7.864, "Ourense", ["Adolfo Domínguez"],
         tx=42, ty=30, ha="left", va="bottom"),
    Firm(41.941, -7.438, "Verín · Ourense", ["Roberto Verino"],
         tx=30, ty=-42, ha="left", va="top"),
    # --- País Vasco (Gipuzkoa coast) --------------------------------------
    Firm(43.303, -2.201, "Getaria", ["Balenciaga"],
         tx=-30, ty=60, ha="right", va="bottom"),
    Firm(43.325, -1.918, "Pasaia", ["Paco Rabanne"],
         tx=35, ty=55, ha="left", va="bottom"),
    # --- Cataluña ----------------------------------------------------------
    Firm(41.588, 2.183, "Palau-solità i Plegamans", ["Mango"],
         tx=-35, ty=48, ha="right", va="bottom"),
    Firm(41.728, 1.823, "Manresa", ["Tous"], kind="joyeria",
         tx=-55, ty=20, ha="right", va="center"),
    Firm(41.387, 2.170, "Barcelona",
         ["Desigual", "Custo Barcelona", "Pronovias", "Puig"],
         tx=60, ty=-15, ha="left", va="center", brand_size=31),
    # --- Madrid ------------------------------------------------------------
    Firm(40.416, -3.703, "Madrid",
         ["Loewe", "Agatha Ruiz de la Prada", "El Ganso", "Tendam"],
         tx=48, ty=35, ha="left", va="center", brand_size=31),
    # --- Comunidad Valenciana ---------------------------------------------
    Firm(38.265, -0.698, "Elche · capital del calzado", ["Pikolinos"],
         kind="calzado", tx=55, ty=-30, ha="left", va="top"),
    # --- Illes Balears -----------------------------------------------------
    Firm(39.721, 2.911, "Inca · Mallorca", ["Camper"], kind="calzado",
         tx=-5, ty=42, ha="center", va="bottom"),
]

# Manolo Blahnik, in the Canary inset (Santa Cruz de La Palma). The label goes
# into the open sea above Tenerife so it never covers an island.
CANARY_FIRM = Firm(28.683, -17.764, "Santa Cruz de La Palma",
                   ["Manolo Blahnik"], kind="calzado",
                   tx=55, ty=52, ha="left", va="top", city_size=24,
                   brand_size=27)


def _project_canary(lon, lat):
    return (gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
            .to_crs(geo.CANARY_CRS).iloc[0].coords[0])


def _draw_firm(ax, dot_xy, anchor_xy, firm, data_per_px):
    dot_face, brand_color = KIND[firm.kind]
    dx, dy = dot_xy
    ax_, ay = anchor_xy

    if firm.leader:
        ax.annotate("", xy=(dx, dy), xytext=(ax_, ay), zorder=9,
                    arrowprops=dict(arrowstyle="-", color=LEADER,
                                    linewidth=2.0, shrinkA=6, shrinkB=8))
    draw.city_dot(ax, (dx, dy), size=firm.dot, face=dot_face, edge="#ffffff")

    # Build the stacked lines top-to-bottom: small grey city, then brands.
    lines = [(firm.city, firm.city_size, CITY_COLOR, "semibold")]
    for b in firm.brands:
        lines.append((b, firm.brand_size, brand_color, "extrabold"))

    def line_h(text, size):
        n = text.count("\n") + 1
        return size * (style.DPI / 72) * data_per_px * 1.16 * n

    heights = [line_h(t, s) for t, s, _, _ in lines]
    total = sum(heights)
    if firm.va == "top":
        top = ay
    elif firm.va == "bottom":
        top = ay + total
    else:
        top = ay + total / 2

    cur = top
    for (text, size, color, weight), h in zip(lines, heights):
        draw.halo_text(ax, ax_, cur, text, size, weight=weight, color=color,
                       ha=firm.ha, va="top", halo_width=max(4, size / 7),
                       zorder=12, linespacing=0.95)
        cur -= h


def map_spain_moda():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    # Neutral parchment Spain.
    draw.draw_layer(ax, s["ccaa_pen"], LAND_FILL, LAND_EDGE, 1.5, zorder=2)
    outline = s["ccaa_pen"].dissolve()
    draw.draw_layer(ax, outline, "none", COAST_EDGE, 2.5, zorder=3)
    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    draw.draw_layer(ax, s["ccaa_can"], LAND_FILL, COAST_EDGE, 1.8, zorder=4)

    data_per_px = (s["frame"][2] - s["frame"][0]) / style.WIDTH_PX

    # Peninsula + Baleares firms.
    for firm in FIRMS:
        dx, dy = _project_lonlat(firm.lon, firm.lat)
        anchor = (dx + firm.tx * KM, dy + firm.ty * KM)
        _draw_firm(ax, (dx, dy), anchor, firm, data_per_px)

    # Canary firm, projected through the inset transform.
    tf = s["canary_tf"]
    dx, dy = geo.canary_xy(_project_canary(CANARY_FIRM.lon, CANARY_FIRM.lat), tf)
    anchor = (dx + CANARY_FIRM.tx * KM, dy + CANARY_FIRM.ty * KM)
    _draw_firm(ax, (dx, dy), anchor, CANARY_FIRM, data_per_px)

    # Kind legend over the Atlantic, above the Canary inset box.
    _kind_legend(ax, s["frame"], 0.03, 0.66)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "La moda española · diseñadores y firmas y dónde nacieron")
    draw.draw_attribution(ax, s["frame"], "Datos: elaboración propia")
    return fig


def _kind_legend(ax, frame, x_frac, y_top_frac, size=30, leading=1.6):
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    row = (size * style.DPI / 72 * leading) / style.HEIGHT_PX
    x_sq = fx0 + x_frac * fw
    x_text = fx0 + (x_frac + 0.013) * fw
    y = y_top_frac
    for kind, text in KIND_LEGEND:
        dot_face, label_color = KIND[kind]
        yy = fy0 + y * fh
        ax.plot(x_sq, yy, marker="o", ms=size * 0.85, mfc=dot_face,
                mec="#ffffff", mew=2.2, zorder=20)
        draw.halo_text(ax, x_text, yy, text, size, weight="semibold",
                       color="#3c3933", ha="left", va="center", zorder=20)
        y -= row
    return y


def render_spain_moda():
    return draw.save(map_spain_moda(), "spain-moda")
