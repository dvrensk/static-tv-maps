"""Spain map where every province carries its name plus an icon of what it is
most famous for — "lo más típico de cada provincia".

Icons are monochrome pictographs from the bundled Noto Emoji font (the colour
emoji fonts render as tofu boxes in matplotlib/Agg; the monochrome family draws
as clean line art). Each glyph is drawn dark with a white halo, like the text
labels, so it pops off the pale parchment base.

Neighbouring provinces are deliberately given different icons: where two
adjacent provinces share a claim to fame (wine, beaches, cathedrals...) one
keeps the obvious icon and the other gets its next-most-distinctive thing.
"""

from dataclasses import dataclass

import matplotlib.patheffects as pe
from matplotlib import font_manager as fm

from . import draw, geo, style
from .maps_spain import KM, _draw_country_labels, _prov_name, spain_scene

LAND_EDGE = "#c6bfb1"        # light internal province borders
COAST_EDGE = "#8f887b"       # darker community / outer coastline
ICON_COLOR = "#2b2824"
NAME_COLOR = style.LABEL_COLOR

_EMOJI_LOADED = False


def _emoji_font(size):
    """FontProperties for the bundled monochrome Noto Emoji font."""
    global _EMOJI_LOADED
    if not _EMOJI_LOADED:
        fm.fontManager.addfont(str(style.ROOT / "assets" / "fonts" /
                                   "NotoEmoji-Bold.ttf"))
        _EMOJI_LOADED = True
    return fm.FontProperties(family="Noto Emoji", weight=700, size=size)


@dataclass
class IconSpec:
    icon: str
    reason: str = ""            # documentation only
    name_size: float = 30
    icon_size: float = 56
    dx: float = 0.0            # anchor nudge, km
    dy: float = 0.0
    # If set, draw the icon+name away from the province with a leader line
    # ending at (anchor + tx/ty km).
    tx: float | None = None
    ty: float | None = None


# prov_code -> icon. See module docstring for the neighbour-differentiation
# logic. Reasons are Spanish so the table doubles as documentation.
ICONS = {
    # --- Galicia -----------------------------------------------------------
    "15": IconSpec("\U0001F5FC", "Torre de Hércules (faro)",         # A Coruña
                   dx=-8, dy=28),
    "27": IconSpec("\U0001F9F1", "muralla romana"),                  # Lugo
    "32": IconSpec("♨", "termas"),                              # Ourense
    "36": IconSpec("\U0001F990", "marisco de las rías / albariño",  # Pontevedra
                   dx=-10, dy=-30),
    # --- Cornisa cantábrica -----------------------------------------------
    "33": IconSpec("\U0001F37E", "sidra"),                           # Asturias
    "39": IconSpec("\U0001F41F", "anchoas"),                         # Cantabria
    # --- País Vasco -------------------------------------------------------
    "48": IconSpec("\U0001F3A8", "Museo Guggenheim",                 # Bizkaia
                   name_size=26, icon_size=46, tx=-48, ty=80),
    "20": IconSpec("\U0001F3C4", "surf",                             # Gipuzkoa
                   name_size=26, icon_size=46, tx=46, ty=98),
    "01": IconSpec("\U0001F9C2", "salinas de Añana",                 # Álava
                   name_size=26, icon_size=48, dy=-6),
    # --- Navarra / La Rioja / Aragón --------------------------------------
    "31": IconSpec("\U0001F402", "San Fermín (toro)"),               # Navarra
    "26": IconSpec("\U0001F377", "vino",                             # La Rioja
                   name_size=26, icon_size=48, dx=18, dy=-6),
    "22": IconSpec("\U0001F3D4", "Pirineos"),                        # Huesca
    "50": IconSpec("⛪", "basílica del Pilar"),                  # Zaragoza
    "44": IconSpec("\U0001F995", "dinosaurios (Dinópolis)"),         # Teruel
    # --- Cataluña ---------------------------------------------------------
    "25": IconSpec("\U0001F34E", "fruta (manzana, pera)"),           # Lleida
    "43": IconSpec("\U0001F3DB", "ruinas romanas (Tarraco)"),        # Tarragona
    "08": IconSpec("⛪", "Sagrada Família"),                     # Barcelona
    "17": IconSpec("\U0001F3D6", "Costa Brava"),                     # Girona
    # --- Comunidad Valenciana / Murcia ------------------------------------
    "12": IconSpec("\U0001F34A", "naranjas"),                        # Castellón
    "46": IconSpec("\U0001F958", "paella"),                          # Valencia
    "03": IconSpec("\U0001F36C", "turrón"),                          # Alicante
    "30": IconSpec("\U0001F96C", "huerta"),                          # Murcia
    # --- Andalucía --------------------------------------------------------
    "04": IconSpec("\U0001F3DC", "desierto de Tabernas"),            # Almería
    "18": IconSpec("\U0001F3F0", "Alhambra"),                        # Granada
    "29": IconSpec("\U0001F3A8", "Picasso"),                         # Málaga
    "23": IconSpec("\U0001FAD2", "aceite de oliva"),                 # Jaén
    "14": IconSpec("\U0001F54C", "Mezquita"),                        # Córdoba
    "41": IconSpec("\U0001F483", "flamenco"),                        # Sevilla
    "11": IconSpec("\U0001F3AD", "carnaval"),                        # Cádiz
    "21": IconSpec("\U0001F353", "fresas"),                          # Huelva
    # --- Extremadura ------------------------------------------------------
    "06": IconSpec("\U0001F356", "jamón / dehesa"),                  # Badajoz
    "10": IconSpec("\U0001F426", "cigüeñas"),                        # Cáceres
    # --- Castilla-La Mancha / Madrid --------------------------------------
    "45": IconSpec("⚔", "espadas", dx=22, dy=-30),              # Toledo
    "13": IconSpec("\U0001F9C0", "queso manchego"),                  # Ciudad Real
    "16": IconSpec("\U0001F3E0", "casas colgadas"),                  # Cuenca
    "19": IconSpec("\U0001F36F", "miel de la Alcarria",              # Guadalajara
                   dx=30, dy=6),
    "02": IconSpec("\U0001F52A", "navajas / cuchillos"),             # Albacete
    "28": IconSpec("\U0001F43B", "el oso y el madroño",              # Madrid
                   icon_size=52, dx=-12, dy=-16),
    # --- Castilla y León --------------------------------------------------
    "05": IconSpec("\U0001F9F1", "murallas"),                        # Ávila
    "40": IconSpec("\U0001F309", "acueducto", dx=8, dy=-30),         # Segovia
    "37": IconSpec("\U0001F393", "universidad"),                     # Salamanca
    "49": IconSpec("⛪", "románico"),                            # Zamora
    "47": IconSpec("\U0001F347", "Ribera del Duero (vino)", dy=8),   # Valladolid
    "34": IconSpec("\U0001F33E", "Tierra de Campos (cereal)"),       # Palencia
    "09": IconSpec("\U0001F32D", "morcilla"),                        # Burgos
    "42": IconSpec("\U0001F332", "pinares"),                         # Soria
    "24": IconSpec("\U0001F981", "el león (heráldica)"),             # León
    # --- Islas ------------------------------------------------------------
    "07": IconSpec("\U0001F3DD", "playas y calas"),                  # Illes Balears
    "35": IconSpec("\U0001F3D6", "dunas y playa"),                   # Las Palmas
    "38": IconSpec("\U0001F30B", "el Teide"),                        # S.C. Tenerife
    # --- Ciudades autónomas -----------------------------------------------
    "51": IconSpec("⚓", "puerto / estrecho"),                   # Ceuta
    "52": IconSpec("⛵", "puerto"),                              # Melilla
}


def _draw_icon_name(ax, x, y, icon, name, icon_size, name_size,
                    gap=1.5 * KM):
    """Stack an icon above a name, both centred on (x, y)."""
    ax.text(x, y + gap, icon, fontproperties=_emoji_font(icon_size),
            color=ICON_COLOR, ha="center", va="bottom", zorder=11,
            path_effects=[pe.withStroke(linewidth=max(4, icon_size / 9),
                                        foreground="#ffffff")])
    draw.halo_text(ax, x, y - gap, name, name_size, weight="extrabold",
                   color=NAME_COLOR, ha="center", va="top", zorder=11)


def map_spain_iconos():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    # Pale community tints so provinces are distinguishable but the dark icons
    # and names dominate.
    tints = [style.shade(style.CCAA_COLORS[c], 0.62)
             for c in s["prov_pen"].acom_code]
    draw.draw_layer(ax, s["prov_pen"], tints, LAND_EDGE, 1.6, zorder=2)
    draw.draw_layer(ax, s["ccaa_pen"], "none", COAST_EDGE, 3.0, zorder=3)

    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    can_tints = [style.shade(style.CCAA_COLORS[c], 0.62)
                 for c in s["prov_can"].acom_code]
    draw.draw_layer(ax, s["prov_can"], can_tints, LAND_EDGE, 1.6, zorder=4)
    draw.draw_layer(ax, s["ccaa_can"], "none", COAST_EDGE, 2.0, zorder=5)

    for layer in (s["prov_pen"], s["prov_can"]):
        for _, row in layer.iterrows():
            spec = ICONS.get(row.prov_code)
            if spec is None:
                continue
            name = _prov_name(row.prov_code, row)
            ax0, ay0 = geo.label_point(row.geometry)
            ax0, ay0 = ax0 + spec.dx * KM, ay0 + spec.dy * KM
            if spec.tx is not None:
                tx, ty = ax0 + spec.tx * KM, ay0 + spec.ty * KM
                ax.annotate("", xy=(ax0, ay0), xytext=(tx, ty), zorder=9,
                            arrowprops=dict(arrowstyle="-", color="#55524d",
                                            linewidth=2.2, shrinkA=6, shrinkB=2))
                _draw_icon_name(ax, tx, ty, spec.icon, name,
                                spec.icon_size, spec.name_size)
            else:
                _draw_icon_name(ax, ax0, ay0, spec.icon, name,
                                spec.icon_size, spec.name_size)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "España · lo más típico de cada provincia")
    draw.draw_attribution(ax, s["frame"],
                          "Datos: IGN España · iconos Noto Emoji")
    return fig


def render_spain_provincias_iconos():
    return draw.save(map_spain_iconos(), "spain-provincias-iconos")
