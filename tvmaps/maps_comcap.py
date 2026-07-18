"""Combined map: autonomous communities filled in colour, showing together
both each community's NAME and its CAPITAL (gold star + city name).

Communities are coloured exactly like ``maps_spain.map_spain_comunidades``.
On top of that we add a gold star at every community capital and the capital
name in a smaller, dark-bronze style so a viewer can tell "region" (big dark
extrabold names) from "capital" (star + smaller bronze name) at a glance.
Canarias carries its two co-capitals inside the inset; Ceuta and Melilla are
city-states, so their single name doubles as region and capital (a star marks
the city).
"""

from . import cities, draw, geo, style
from .maps_spain import (
    Label,
    _draw_country_labels,
    _label_regions,
    spain_scene,
    KM,
)
from .maps_capitals import CityLabel, _capital_xy

# Capital names are drawn in a warm dark bronze so they read as "belonging to
# the gold star", clearly distinct from the near-black community names.
CAP_COLOR = "#7a4e10"

# Capitals drawn as a star only (no separate name): Ceuta/Melilla are
# city-states and Madrid/Murcia share their name with the community, which is
# already labelled once as the region.
STAR_ONLY = {"Ceuta", "Melilla", "Madrid", "Murcia"}


# --- Community NAME placements (big, dark, extrabold) -----------------------
# Shifted away from the capital star of the same community so the two never
# collide. Offsets in km; (tx, ty) means a leader-line callout into open sea.
COMM_LABELS = {
    "01": Label(54, dx=95, dy=12),        # Andalucía — E of Sevilla
    "02": Label(52, dy=-78),              # Aragón — S toward Teruel (star N)
    "03": Label(42, tx=-82, ty=58),       # Asturias — callout NW into sea (Oviedo central)
    "04": Label(40, dx=-8, dy=-88),       # Islas Baleares — sea S of Mallorca
    "06": Label(38, tx=-72, ty=70),       # Cantabria — callout NW into sea
    "07": Label(52, dx=20, dy=-72),       # Castilla y León — S-centre, clear of NE cluster
    "08": Label(54, dx=-25, dy=-45),      # Castilla-La Mancha — S-centre
    "09": Label(54, dx=-28),              # Cataluña — inland (Barcelona coast)
    "10": Label(38, dx=8, dy=36),         # Comunidad Valenciana — N (Castellón)
    "11": Label(52, dy=66),               # Extremadura — N (Mérida central)
    "12": Label(48, dx=58),               # Galicia — E (Santiago W coast)
    "13": Label(40, dy=26),               # Madrid — N of the star
    "14": Label(40, dx=-34, dy=30),       # Murcia — NW of the star
    "15": Label(40, dy=-50),              # Navarra — S (Pamplona N)
    "16": Label(40, tx=80, ty=104),       # País Vasco — callout NE into sea
    "17": Label(28, dx=-14, dy=-16),      # La Rioja — region body
    "18": Label(34, tx=-55, ty=25, ha="right"),   # Ceuta — callout
    "19": Label(34, tx=25, ty=45, ha="left"),     # Melilla — callout
}


# --- Capital placements (gold star + smaller bronze name) -------------------
CAP_LABELS = {
    # Andalucía / Extremadura / south
    "Sevilla": CityLabel(30, dx=-8, dy=-9, ha="right"),   # name is to the E
    "Mérida": CityLabel(30, dy=-14),                      # name is to the N
    # Ebro / Aragón / Cataluña / Levante
    "Zaragoza": CityLabel(30, dy=-14),                    # name is to the S
    "Barcelona": CityLabel(30, dx=10, dy=-7, ha="left"),  # sea to the SE
    "Valencia": CityLabel(30, dx=10, dy=-5, ha="left"),   # sea to the E
    # Cornisa cantábrica
    "Oviedo": CityLabel(30, dy=-14),                      # name is to the W
    "Santander": CityLabel(30, dy=-15),                   # name callout above
    "Vitoria-Gasteiz": CityLabel(28, dx=-9, dy=-2, ha="right"),   # W of star
    "Pamplona": CityLabel(28, dy=14),                    # name is to the S
    "Logroño": CityLabel(26, dx=9, dy=6, ha="left"),
    # Castilla y León / La Mancha
    "Valladolid": CityLabel(30, dy=14),                  # name is to the S
    "Toledo": CityLabel(30, dy=-14),                     # name is centre-S
    # Galicia
    "Santiago de Compostela": CityLabel(28, dx=-6, dy=-26, ha="right",
                                        text="Santiago\nde Compostela"),
    # Baleares
    "Palma": CityLabel(30, dx=2, dy=-16),                # bay below
    # Canarias (inside the inset)
    "Las Palmas de Gran Canaria": CityLabel(28, dx=9, dy=-27, ha="left",
                                            text="Las Palmas de\nGran Canaria"),
    "Santa Cruz de Tenerife": CityLabel(28, dx=-14, dy=29,
                                        text="Santa Cruz\nde Tenerife"),
}


def _draw_capital(ax, xy, name):
    """Gold star at the capital, plus its name (unless it is a star-only
    city-state / same-name-as-region capital)."""
    draw.city_star(ax, xy)
    if name in STAR_ONLY:
        return
    spec = CAP_LABELS[name]
    text = spec.text or name
    if spec.tx is not None:
        draw.callout(ax, xy, (xy[0] + spec.tx * KM, xy[1] + spec.ty * KM),
                     text, spec.size, weight="semibold", color=CAP_COLOR,
                     ha=spec.ha)
    else:
        draw.halo_text(ax, xy[0] + spec.dx * KM, xy[1] + spec.dy * KM, text,
                       spec.size, weight="semibold", color=CAP_COLOR,
                       ha=spec.ha, va=spec.va)


def _draw_key(ax, frame):
    """Small key over the Atlantic: gold star = capital."""
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    x = fx0 + 0.022 * fw
    y = fy0 + 0.50 * fh
    draw.city_star(ax, (x, y))
    draw.halo_text(ax, x + 0.012 * fw, y, "capital", 30, weight="semibold",
                   color=CAP_COLOR, ha="left", va="center", zorder=20)


def map_spain_comunidades_capitales():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    # Coloured communities, exactly like map_spain_comunidades.
    colors = [style.CCAA_COLORS[c] for c in s["ccaa_pen"].acom_code]
    draw.draw_layer(ax, s["ccaa_pen"], colors, style.BORDER_DARK, 3.0, zorder=2)

    draw.draw_inset_box(ax, s["canary_box"], label="Canarias")
    draw.draw_layer(ax, s["ccaa_can"], style.CCAA_COLORS["05"],
                    style.BORDER_DARK, 2.0, zorder=4)

    # Community names (big, dark, extrabold).
    _label_regions(ax, s["ccaa_pen"], "acom_code",
                   lambda c, r: style.CCAA_DISPLAY[c], COMM_LABELS)

    # Capitals (gold star + smaller bronze name).
    xy = _capital_xy(s)
    for keys in cities.CCAA_CAPITALS.values():
        for name in keys:
            _draw_capital(ax, xy[name], name)

    _draw_key(ax, s["frame"])
    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "Comunidades autónomas y sus capitales")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_comunidades_capitales():
    return draw.save(map_spain_comunidades_capitales(),
                     "spain-comunidades-capitales")
