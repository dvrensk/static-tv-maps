"""Spain map of the book-publishing and record-label industry.

A neutral parchment Spain with the headquarter cities of the main book
publishers (editoriales) and record labels (discográficas), colour-coded
into the two categories with a small legend.

Barcelona and Madrid each concentrate a dozen names, so instead of stacking
labels on a single dot they get a titled list panel (a rounded box with a
leader line to the city dot). The less-crowded cities — Vigo, Pontevedra,
Bilbao and Girona — use a normal dot with a company label.

All companies were verified at their headquarter city (elaboración propia):
- Editoriales · Barcelona: Grupo Planeta, Penguin Random House, Anagrama,
  Tusquets, Salamandra, Acantilado, Edicions 62, Norma (cómic).
- Editoriales · Madrid: Santillana, SM, Anaya, Alianza, Siruela, Alfaguara.
- Editoriales · Galicia: Galaxia (Vigo), Kalandraka (Pontevedra).
- Editorial · País Vasco: Astiberri (Bilbao, cómic).
- Discográficas · Madrid: Warner, Sony, Universal, Subterfuge, Elefant,
  El Volcán.
- Discográficas · Cataluña: BCore Disc (Barcelona), Música Global (Girona).
"""

from dataclasses import dataclass, field

from . import cities, draw, geo, style
from .maps_spain import KM, _project_lonlat, spain_scene

# Parchment base, borrowed from the neighbouring maps.
LAND_FILL = "#efe8d8"
LAND_EDGE = "#c6bfb1"
COAST_EDGE = "#8f887b"

# The two industry categories.
EDIT_COLOR = "#2f5f92"        # editoriales · ink blue
DISC_COLOR = "#b23a5e"        # discográficas · music red
EDIT_FILL = "#9db9d6"         # legend swatch fills (lighter)
DISC_FILL = "#dfa1b5"

PANEL_BG = "#f7f2e6"
PANEL_EDGE = "#b3a586"
LEADER = "#6b675f"

# PORTUGAL is pushed up near Braga (as in maps_ciudades) so central and
# southern Portugal are free for the Madrid list panel.
COUNTRY_LABELS = [
    ("PORTUGAL", -8.15, 41.75, 34, 0),
    ("FRANCIA", 1.4, 43.7, 44, 0),
    ("MARRUECOS", -4.9, 35.02, 34, 0),
]


def _draw_country_labels(ax, frame):
    fx0, fy0, fx1, fy1 = frame
    for text, lon, lat, size, rotation in COUNTRY_LABELS:
        x, y = _project_lonlat(lon, lat)
        if fx0 < x < fx1 and fy0 < y < fy1:
            t = draw.halo_text(ax, x, y, text, size, weight="semibold",
                               color=style.NEIGHBOR_LABEL, halo_width=6,
                               zorder=5)
            t.set_rotation(rotation)


# ---------------------------------------------------------------------------
# City list panel (Madrid / Barcelona)
# ---------------------------------------------------------------------------

def _panel(ax, top_lonlat, title, entries, dot_xy, title_size=36,
           entry_size=28):
    """Rounded box titled with a city, listing (name, cat) entries coloured by
    category, with a leader line to the city dot at `dot_xy`."""
    x_left, y_top = _project_lonlat(*top_lonlat)

    tw, dpp = draw._name_width_data(ax, title, title_size, "extrabold")
    widths = [tw]
    for text, _cat in entries:
        w, _ = draw._name_width_data(ax, text, entry_size, "semibold")
        widths.append(w)
    content_w = max(widths)

    pad = 34 * dpp
    title_h = title_size * style.DPI / 72 * 1.5 * dpp
    entry_h = entry_size * style.DPI / 72 * 1.34 * dpp
    div_gap = entry_size * style.DPI / 72 * 0.55 * dpp

    # Total height (with one divider gap where the category switches).
    switches = sum(1 for i in range(1, len(entries))
                   if entries[i][1] != entries[i - 1][1])
    inner_h = title_h + len(entries) * entry_h + switches * div_gap
    box_left = x_left - pad
    box_top = y_top + pad
    box_w = content_w + 2 * pad
    box_h = inner_h + 2 * pad
    box_right = box_left + box_w

    # Leader first (hidden inside the box), box, then text.
    cx = box_left + box_w / 2
    cy = box_top - box_h / 2
    ax.annotate("", xy=dot_xy, xytext=(cx, cy), zorder=6,
                arrowprops=dict(arrowstyle="-", color=LEADER, linewidth=2.4,
                                shrinkA=2, shrinkB=4))

    from matplotlib.patches import FancyBboxPatch
    r = 0.03 * box_w
    ax.add_patch(FancyBboxPatch(
        (box_left, box_top - box_h), box_w, box_h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=PANEL_BG, edgecolor=PANEL_EDGE, linewidth=2.6, zorder=8))

    draw.halo_text(ax, x_left, y_top, title, title_size, weight="extrabold",
                   color=style.LABEL_COLOR, ha="left", va="top", zorder=10)
    y = y_top - title_h
    prev = None
    for text, cat in entries:
        if prev is not None and cat != prev:
            yy = y + entry_h * 0.5
            ax.plot([box_left + pad * 0.4, box_right - pad * 0.4], [yy, yy],
                    color=PANEL_EDGE, linewidth=1.4, zorder=9)
            y -= div_gap
        color = EDIT_COLOR if cat == "edit" else DISC_COLOR
        draw.halo_text(ax, x_left, y, text, entry_size, weight="semibold",
                       color=color, ha="left", va="top", zorder=10,
                       halo_width=4)
        y -= entry_h
        prev = cat


# ---------------------------------------------------------------------------
# Single-dot regional cities
# ---------------------------------------------------------------------------

@dataclass
class CityCo:
    company: str
    cat: str
    dx: float = 0.0
    dy: float = 0.0
    ha: str = "center"
    va: str = "center"
    tx: float | None = None   # if set, draw the label with a leader line
    ty: float | None = None


REGIONALS = {
    "Vigo": CityCo("Galaxia", "edit", tx=-40, ty=-42, ha="right", va="top"),
    "Pontevedra": CityCo("Kalandraka", "edit", tx=-52, ty=30, ha="right",
                         va="bottom"),
    "Bilbao": CityCo("Astiberri", "edit", tx=6, ty=70, ha="center",
                     va="bottom"),
    "Girona": CityCo("Música Global", "disc", dx=9, dy=6, ha="left",
                     va="bottom"),
}


def _regional(ax, pts, key, spec):
    x, y = pts[key]
    color = EDIT_COLOR if spec.cat == "edit" else DISC_COLOR
    draw.city_dot(ax, (x, y), size=15, face=color, edge="#ffffff")
    text = f"{spec.company}\n{key}"
    if spec.tx is not None:
        tx, ty = x + spec.tx * KM, y + spec.ty * KM
        ax.annotate("", xy=(x, y), xytext=(tx, ty), zorder=9,
                    arrowprops=dict(arrowstyle="-", color=LEADER,
                                    linewidth=2.2, shrinkA=6, shrinkB=3))
        _two_line(ax, tx, ty, spec.company, key, color, spec.ha, spec.va)
    else:
        _two_line(ax, x + spec.dx * KM, y + spec.dy * KM, spec.company, key,
                  color, spec.ha, spec.va)


def _two_line(ax, x, y, company, city, color, ha, va, size=30, city_size=25):
    """Company name (coloured) with the city underneath in grey."""
    dpp = (ax.get_xlim()[1] - ax.get_xlim()[0]) / style.WIDTH_PX
    line = size * style.DPI / 72 * dpp
    if va == "bottom":
        y_city = y
        y_co = y + city_size * style.DPI / 72 * 1.05 * dpp
        draw.halo_text(ax, x, y_co, company, size, weight="extrabold",
                       color=color, ha=ha, va="bottom", zorder=11)
        draw.halo_text(ax, x, y_city, city, city_size, weight="semibold",
                       color="#5d5a54", ha=ha, va="bottom", zorder=11)
    else:  # va top (grows downward): company on top, city below
        draw.halo_text(ax, x, y, company, size, weight="extrabold",
                       color=color, ha=ha, va="top", zorder=11)
        draw.halo_text(ax, x, y - line, city, city_size, weight="semibold",
                       color="#5d5a54", ha=ha, va="top", zorder=11)


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------

LEGEND = [
    (EDIT_FILL, EDIT_COLOR, "Editoriales (libros)"),
    (DISC_FILL, DISC_COLOR, "Discográficas (música)"),
]


def _legend(ax, frame, x_frac, y_top_frac, size=32, leading=1.7):
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    row = (size * style.DPI / 72 * leading) / style.HEIGHT_PX
    x_sq = fx0 + x_frac * fw
    x_text = fx0 + (x_frac + 0.013) * fw
    y = y_top_frac
    for fill, edge, text in LEGEND:
        yy = fy0 + y * fh
        ax.plot(x_sq, yy, marker="s", ms=size * 0.95, mfc=fill, mec=edge,
                mew=2.4, zorder=20)
        draw.halo_text(ax, x_text, yy, text, size, weight="semibold",
                       color="#3c3933", ha="left", va="center", zorder=20)
        y -= row
    return y


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

MADRID_ENTRIES = [
    ("Santillana", "edit"),
    ("SM", "edit"),
    ("Anaya", "edit"),
    ("Alianza Editorial", "edit"),
    ("Siruela", "edit"),
    ("Alfaguara", "edit"),
    ("Warner Music", "disc"),
    ("Sony Music", "disc"),
    ("Universal Music", "disc"),
    ("Subterfuge", "disc"),
    ("Elefant", "disc"),
    ("El Volcán", "disc"),
]

BARCELONA_ENTRIES = [
    ("Grupo Planeta", "edit"),
    ("Penguin Random House", "edit"),
    ("Anagrama", "edit"),
    ("Tusquets", "edit"),
    ("Salamandra", "edit"),
    ("Acantilado", "edit"),
    ("Edicions 62", "edit"),
    ("Norma (cómic)", "edit"),
    ("BCore Disc", "disc"),
]


def map_spain_editoriales():
    s = spain_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["countries"])

    draw.draw_layer(ax, s["ccaa_pen"], LAND_FILL, LAND_EDGE, 1.5, zorder=2)
    outline = s["ccaa_pen"].dissolve()
    draw.draw_layer(ax, outline, "none", COAST_EDGE, 2.5, zorder=3)
    draw.draw_inset_box(ax, s["canary_box"], label="Islas Canarias")
    draw.draw_layer(ax, s["ccaa_can"], LAND_FILL, COAST_EDGE, 1.8, zorder=4)

    pts = cities.load_points()

    # Regional single-dot cities.
    for key, spec in REGIONALS.items():
        _regional(ax, pts, key, spec)

    # The two dense cities get list panels.
    draw.city_dot(ax, pts["Madrid"], size=17, face="#3a3733", edge="#ffffff")
    draw.city_dot(ax, pts["Barcelona"], size=17, face="#3a3733", edge="#ffffff")
    _panel(ax, (-9.1, 40.9), "Madrid", MADRID_ENTRIES, pts["Madrid"])
    _panel(ax, (3.35, 41.05), "Barcelona", BARCELONA_ENTRIES, pts["Barcelona"])

    _legend(ax, s["frame"], 0.032, 0.90)
    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "Editoriales y discográficas de España")
    draw.draw_attribution(ax, s["frame"], "Datos: elaboración propia")
    return fig


def render_spain_editoriales():
    return draw.save(map_spain_editoriales(), "spain-editoriales")
