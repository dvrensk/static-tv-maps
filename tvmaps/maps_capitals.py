"""Capital-city maps: the 52 province capitals and the community capitals."""

from dataclasses import dataclass

from . import cities, draw, geo, style
from .maps_spain import (
    KM,
    _draw_country_labels,
    _province_colors,
    spain_scene,
)

# Cities that live inside the Canary Islands inset and therefore need their
# coordinates loaded in the Canary CRS and passed through the inset transform.
CANARY_KEYS = {"Las Palmas de Gran Canaria", "Santa Cruz de Tenerife"}


@dataclass
class CityLabel:
    """Placement of a city-name label relative to its dot.

    (dx, dy) offset the text from the dot, in km. If (tx, ty) are set the
    label becomes a leader-line callout instead (offsets also in km)."""

    size: float = 28
    dx: float = 0.0
    dy: float = 10.0
    ha: str = "center"
    va: str = "center"
    tx: float | None = None
    ty: float | None = None
    text: str | None = None  # display override (e.g. two-line wrap)


def _capital_xy(scene):
    """key -> (x, y) in main-map coordinates for every geocoded city,
    with the Canary cities already moved into the inset."""
    pts = cities.load_points()
    pts_can = cities.load_points(geo.CANARY_CRS)
    for key in CANARY_KEYS:
        pts[key] = geo.canary_xy(pts_can[key], scene["canary_tf"])
    return pts


def _draw_city(ax, xy, name, spec, marker="dot"):
    if marker == "star":
        draw.city_star(ax, xy)
    else:
        draw.city_dot(ax, xy)
    text = spec.text or name
    if spec.tx is not None:
        draw.callout(ax, xy, (xy[0] + spec.tx * KM, xy[1] + spec.ty * KM),
                     text, spec.size, weight="extrabold", ha=spec.ha)
    else:
        draw.halo_text(ax, xy[0] + spec.dx * KM, xy[1] + spec.dy * KM, text,
                       spec.size, weight="extrabold", ha=spec.ha, va=spec.va)


# ---------------------------------------------------------------------------
# Province capitals — all 52 on one map
# ---------------------------------------------------------------------------

# key: city name from cities.PROV_CAPITALS. Offsets in km.
PROV_CAPITAL_LABELS = {
    # Galicia
    "A Coruña": CityLabel(dx=-6, dy=8, ha="right"),        # sea to the NW
    "Lugo": CityLabel(dx=8, dy=6, ha="left"),
    "Ourense": CityLabel(dy=-11),
    "Pontevedra": CityLabel(dx=-7, dy=2, ha="right"),      # sea to the W
    # Cornisa cantábrica
    "Oviedo": CityLabel(dy=-11),
    "Santander": CityLabel(dx=-2, dy=11),                  # sea above
    "Bilbao": CityLabel(dx=-4, dy=12),                     # sea above
    "San Sebastián": CityLabel(dx=8, dy=9, ha="left"),     # sea to the NE
    "Vitoria-Gasteiz": CityLabel(dy=-11),
    # Navarra / Rioja / Aragón
    "Pamplona": CityLabel(dx=9, dy=4, ha="left"),
    "Logroño": CityLabel(dx=9, dy=-3, ha="left"),
    "Huesca": CityLabel(dx=9, dy=4, ha="left"),
    "Zaragoza": CityLabel(dy=-11),
    "Teruel": CityLabel(dy=-11),
    # Cataluña
    "Girona": CityLabel(dx=9, dy=4, ha="left"),
    "Lleida": CityLabel(dy=11),
    "Barcelona": CityLabel(dx=8, dy=-6, ha="left"),        # sea to the SE
    "Tarragona": CityLabel(dx=2, dy=-12),                  # sea below
    # Castilla y León
    "León": CityLabel(dy=11),
    "Palencia": CityLabel(dx=9, dy=3, ha="left"),
    "Burgos": CityLabel(dx=3, dy=-13),
    "Zamora": CityLabel(dx=-9, dy=-2, ha="right"),
    "Valladolid": CityLabel(dy=-11),
    "Salamanca": CityLabel(dy=-11),
    "Segovia": CityLabel(dx=9, dy=4, ha="left"),
    "Soria": CityLabel(dy=11),
    "Ávila": CityLabel(dx=-9, dy=-4, ha="right"),
    # Madrid / Castilla-La Mancha
    "Madrid": CityLabel(dx=-9, dy=4, ha="right"),
    "Guadalajara": CityLabel(dx=9, dy=4, ha="left"),
    "Toledo": CityLabel(dy=-11),
    "Cuenca": CityLabel(dx=9, dy=4, ha="left"),
    "Ciudad Real": CityLabel(dy=-11),
    "Albacete": CityLabel(dy=11),
    # Levante / Murcia / Baleares
    "Castellón de la Plana": CityLabel(dx=8, dy=2, ha="left",
                                       text="Castellón de\nla Plana"),
    "Valencia": CityLabel(dx=8, dy=-4, ha="left"),         # sea to the E
    "Alicante": CityLabel(dx=8, dy=-4, ha="left"),         # sea to the SE
    "Murcia": CityLabel(dx=-9, dy=-4, ha="right"),
    "Palma": CityLabel(dx=2, dy=-12),                      # bay below
    # Extremadura
    "Cáceres": CityLabel(dy=11),
    "Badajoz": CityLabel(dy=-11),
    # Andalucía
    "Huelva": CityLabel(dx=-4, dy=-12),                    # sea below
    "Sevilla": CityLabel(dx=9, dy=4, ha="left"),
    "Cádiz": CityLabel(dx=-7, dy=-6, ha="right"),          # sea to the SW
    "Málaga": CityLabel(dx=2, dy=-12),                     # sea below
    "Córdoba": CityLabel(dy=11),
    "Jaén": CityLabel(dx=9, dy=4, ha="left"),
    "Granada": CityLabel(dy=-11),
    "Almería": CityLabel(dx=4, dy=-12),                    # sea below
    # Ciudades autónomas — leader lines out to sea
    "Ceuta": CityLabel(tx=-50, ty=22, ha="right"),
    "Melilla": CityLabel(tx=22, ty=40, ha="left"),
    # Canarias (inside the inset)
    "Las Palmas de Gran Canaria": CityLabel(dx=9, dy=-25, ha="left",
                                            text="Las Palmas de\nGran Canaria"),
    "Santa Cruz de Tenerife": CityLabel(dx=-13, dy=27,
                                        text="Santa Cruz\nde Tenerife"),
}


def map_spain_capitales_provincias():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    draw.draw_layer(ax, s["prov_pen"], _province_colors(s["prov_pen"]),
                    style.BORDER_LIGHT, 1.8, zorder=2)
    draw.draw_layer(ax, s["ccaa_pen"], "none", style.BORDER_DARK, 3.2, zorder=3)

    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    draw.draw_layer(ax, s["prov_can"], _province_colors(s["prov_can"]),
                    style.BORDER_LIGHT, 1.8, zorder=4)
    draw.draw_layer(ax, s["ccaa_can"], "none", style.BORDER_DARK, 2.2, zorder=5)

    xy = _capital_xy(s)
    for name in cities.PROV_CAPITALS.values():
        _draw_city(ax, xy[name], name, PROV_CAPITAL_LABELS[name])

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Capitales de provincia de España · "
                     "colores por comunidad autónoma")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_capitales_provincias():
    return draw.save(map_spain_capitales_provincias(),
                     "spain-capitales-provincias")


# ---------------------------------------------------------------------------
# Community capitals — 17 communities (+ Ceuta and Melilla), stars
# ---------------------------------------------------------------------------

CCAA_CAPITAL_LABELS = {
    "Sevilla": CityLabel(34, dx=11, dy=5, ha="left"),
    "Zaragoza": CityLabel(34, dy=-13),
    "Oviedo": CityLabel(34, dy=-13),
    "Palma": CityLabel(34, dx=2, dy=-14),                  # bay below
    "Santander": CityLabel(34, dx=-2, dy=13),              # sea above
    "Valladolid": CityLabel(34, dy=-13),
    "Toledo": CityLabel(34, dy=-13),
    "Barcelona": CityLabel(34, dx=10, dy=-7, ha="left"),   # sea to the SE
    "Valencia": CityLabel(34, dx=10, dy=-5, ha="left"),    # sea to the E
    "Mérida": CityLabel(34, dy=-13),
    "Santiago de Compostela": CityLabel(34, dy=-26, text="Santiago\nde Compostela"),
    "Madrid": CityLabel(34, dx=11, dy=5, ha="left"),
    "Murcia": CityLabel(34, dy=-13),
    "Pamplona": CityLabel(34, dx=11, dy=5, ha="left"),
    "Vitoria-Gasteiz": CityLabel(34, dy=-13),
    "Logroño": CityLabel(34, dx=-4, dy=-14),
    "Ceuta": CityLabel(32, tx=-50, ty=22, ha="right"),
    "Melilla": CityLabel(32, tx=22, ty=40, ha="left"),
    "Las Palmas de Gran Canaria": CityLabel(32, dx=9, dy=-27, ha="left",
                                            text="Las Palmas de\nGran Canaria"),
    "Santa Cruz de Tenerife": CityLabel(32, dx=-14, dy=29,
                                        text="Santa Cruz\nde Tenerife"),
}


def map_spain_capitales_comunidades():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    colors = [style.CCAA_COLORS[c] for c in s["ccaa_pen"].acom_code]
    draw.draw_layer(ax, s["ccaa_pen"], colors, style.BORDER_DARK, 3.0, zorder=2)

    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    draw.draw_layer(ax, s["ccaa_can"], style.CCAA_COLORS["05"],
                    style.BORDER_DARK, 2.0, zorder=4)

    xy = _capital_xy(s)
    for keys in cities.CCAA_CAPITALS.values():
        for name in keys:
            _draw_city(ax, xy[name], name, CCAA_CAPITAL_LABELS[name],
                       marker="star")

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Capitales de las comunidades autónomas · "
                     "Canarias tiene dos capitales")
    draw.draw_attribution(ax, s["frame"])
    return fig


def render_spain_capitales_comunidades():
    return draw.save(map_spain_capitales_comunidades(),
                     "spain-capitales-comunidades")
