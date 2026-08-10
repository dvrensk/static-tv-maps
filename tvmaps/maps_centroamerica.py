"""América Central: the seven countries, their capitals and a flag panel.

The isthmus is much taller than 16:9, so a whole column of canvas is free on
the Caribbean side: that column holds the flags, each with its country and
capital, in north-west to south-east order. The passe-partout around every flag
repeats the country's fill color on the map, so a viewer can pair flag and
country without reading a legend.
"""

from dataclasses import dataclass

from . import draw, geo, style

KM = 1000.0
FLAGS = geo.ROOT / "assets" / "flags"

# North-west to south-east, the order the panel lists them in.
ORDER = ["GT", "BZ", "SV", "HN", "NI", "CR", "PA"]

# Share of the canvas width taken by the flag panel. The isthmus is limited by
# the canvas *height*, so widening the panel costs no map scale — it only eats
# empty Caribbean. The panel stops short of the bottom edge, leaving the corner
# where Colombia enters the frame visible.
PANEL_FRAC = 0.235
PANEL_BOTTOM_PX = 300

# Framing box (lon/lat): the mainland isthmus only. Costa Rica's Isla del Coco
# (5.5° N) and Honduras' Islas del Cisne lie far offshore and would shrink
# everything else if they set the frame.
CORE_BOX = (-93.0, 6.9, -76.4, 18.6)


def _px(frame):
    """Data units per pixel (the canvas is always 4000 px wide)."""
    return (frame[2] - frame[0]) / style.WIDTH_PX


def panel_rect(frame):
    """The flag panel's box (minx, miny, maxx, maxy) in data coordinates."""
    fx0, fy0, fx1, fy1 = frame
    u = _px(frame)
    return (fx1 - PANEL_FRAC * (fx1 - fx0) + 20 * u, fy0 + PANEL_BOTTOM_PX * u,
            fx1 - 26 * u, fy1 - 26 * u)


def scene():
    countries = geo.load("centroamerica")
    capitals = geo.load("centroamerica_capitales")

    core = countries[countries.role == "centro"].clip(CORE_BOX)
    core = core.to_crs(geo.CENTRAL_AMERICA_CRS)
    minx, miny, maxx, maxy = core.total_bounds

    # Height-constrained: fix the vertical padding, then centre the isthmus in
    # the part of the canvas the panel leaves free.
    pad_y = 0.03
    h = (maxy - miny) * (1 + 2 * pad_y)
    w = h * geo.RATIO
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    x0 = cx - (1 - PANEL_FRAC) * w / 2
    frame = (x0, cy - h / 2, x0 + w, cy + h / 2)

    return dict(
        frame=frame,
        main=countries[countries.role == "centro"].to_crs(geo.CENTRAL_AMERICA_CRS),
        context=countries[countries.role == "contexto"].to_crs(geo.CENTRAL_AMERICA_CRS),
        capitals=capitals.to_crs(geo.CENTRAL_AMERICA_CRS),
    )


def _project_lonlat(lon, lat):
    import geopandas as gpd
    from shapely.geometry import Point

    return (
        gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
        .to_crs(geo.CENTRAL_AMERICA_CRS)
        .iloc[0]
        .coords[0]
    )


@dataclass
class Place:
    """Label placement, offsets in km. With (tx, ty) it becomes a callout."""

    size: float = 46
    dx: float = 0.0
    dy: float = 0.0
    tx: float | None = None
    ty: float | None = None
    ha: str = "center"
    text: str | None = None


# Display names (Natural Earth's NAME_ES is already Castilian, but the map
# module owns what the viewer reads).
COUNTRY_NAMES = {
    "GT": "Guatemala", "BZ": "Belice", "SV": "El Salvador", "HN": "Honduras",
    "NI": "Nicaragua", "CR": "Costa Rica", "PA": "Panamá",
}

# Country names on the map. Belice and El Salvador are too narrow for their
# name, so they get leader lines out to the water.
COUNTRY_LABELS = {
    "GT": Place(52, dx=25, dy=190),        # up into the Petén
    "BZ": Place(42, tx=250, ty=40, ha="left"),      # east, into the Caribbean
    # East end of the country, then down into the Golfo de Fonseca: the only
    # water nearby that the San Salvador label does not already occupy.
    "SV": Place(42, dx=95, dy=-20, tx=20, ty=-150),
    "HN": Place(52, dx=10, dy=35),
    "NI": Place(52, dy=45),
    "CR": Place(44, dx=-45, dy=-70),
    "PA": Place(44, dx=-40, dy=15),
}

# Capitals: star + name. Offsets in km from the point.
CAPITAL_LABELS = {
    "GT": Place(34, dx=-24, dy=-14, ha="right", text="Ciudad de\nGuatemala"),
    "BZ": Place(34, dx=-22, dy=0, ha="right"),
    "SV": Place(34, dx=-10, dy=-42),
    "HN": Place(34, dx=22, dy=-16, ha="left"),
    "NI": Place(34, dx=-20, dy=-24, ha="right"),
    "CR": Place(34, dx=20, dy=24, ha="left"),
    "PA": Place(34, dx=6, dy=32, ha="left", text="Ciudad de\nPanamá"),
}

# Neighbours and waters, in the muted register of the Spanish maps.
CONTEXT_LABELS = [
    ("MÉXICO", -91.6, 18.05, 54, 0),
    ("COLOMBIA", -76.85, 7.25, 40, 0),
    ("CUBA", -80.4, 21.9, 44, 0),
    ("JAMAICA", -77.3, 18.1, 34, 0),
]

WATER_LABELS = [
    ("MAR CARIBE", -81.5, 15.6, 56, 0),
    ("OCÉANO\nPACÍFICO", -89.5, 9.3, 52, 0),
]

WATER_COLOR = "#8fb4c9"


def _draw_context_labels(ax, frame):
    """Neighbours and seas, skipping anything that would land under the panel."""
    fx0, fy0, fx1, fy1 = frame
    px0, py0, px1, py1 = panel_rect(frame)
    for labels, color in ((CONTEXT_LABELS, style.NEIGHBOR_LABEL),
                          (WATER_LABELS, WATER_COLOR)):
        for text, lon, lat, size, rotation in labels:
            x, y = _project_lonlat(lon, lat)
            if not (fx0 < x < fx1 and fy0 < y < fy1):
                continue
            if px0 < x < px1 and py0 < y < py1:
                continue
            t = draw.halo_text(ax, x, y, text, size, weight="semibold",
                               color=color, halo_width=7, zorder=5)
            t.set_rotation(rotation)


def _draw_flag_panel(ax, frame, capital_names):
    u = _px(frame)                     # one pixel in data units
    box = panel_rect(frame)
    draw.panel_box(ax, box)
    bx0, by0, bx1, by1 = box

    draw.halo_text(ax, (bx0 + bx1) / 2, by1 - 30 * u, "América Central", 54,
                   weight="extrabold", color=style.LABEL_COLOR, halo_width=0,
                   va="top", zorder=20)
    draw.halo_text(ax, (bx0 + bx1) / 2, by1 - 112 * u,
                   "banderas y capitales", 32, weight="semibold",
                   color="#6b6862", halo_width=0, va="top", zorder=20)

    top = by1 - 150 * u
    row_h = (top - by0 - 10 * u) / len(ORDER)
    flag_left = bx0 + 30 * u
    text_left = flag_left + 300 * u
    for i, iso in enumerate(ORDER):
        cy = top - (i + 0.5) * row_h
        draw.flag(ax, FLAGS / f"{iso}.png", flag_left, cy, width=270 * u,
                  mat_color=style.CENTRO_COLORS[iso], mat_px=8)
        draw.halo_text(ax, text_left, cy + 10 * u, COUNTRY_NAMES[iso], 46,
                       weight="extrabold", color=style.LABEL_COLOR,
                       halo_width=0, ha="left", va="bottom", zorder=20)
        draw.city_star(ax, (text_left + 18 * u, cy - 40 * u), size=22, zorder=20)
        draw.halo_text(ax, text_left + 44 * u, cy - 40 * u,
                       capital_names[iso], 34, weight="semibold",
                       color="#4a4741", halo_width=0, ha="left", zorder=20)


def _label_place(ax, xy, text, spec, weight="extrabold"):
    """Place `text` for a feature anchored at `xy`, per the Place spec."""
    x, y = xy[0] + spec.dx * KM, xy[1] + spec.dy * KM
    if spec.tx is not None:
        draw.callout(ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM), text,
                     spec.size, weight=weight, ha=spec.ha)
    else:
        draw.halo_text(ax, x, y, text, spec.size, weight=weight, ha=spec.ha)


def map_centroamerica():
    s = scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    main = s["main"]
    colors = [style.CENTRO_COLORS[i] for i in main.iso]
    draw.draw_layer(ax, main, colors, style.BORDER_DARK, 3.0, zorder=2)

    _draw_context_labels(ax, s["frame"])

    for _, row in main.iterrows():
        spec = COUNTRY_LABELS[row.iso]
        xy = geo.label_point(row.geometry, tol=1000.0)
        _label_place(ax, xy, spec.text or COUNTRY_NAMES[row.iso], spec)

    capital_names = dict(zip(s["capitals"].iso, s["capitals"]["name"]))
    for _, row in s["capitals"].iterrows():
        spec = CAPITAL_LABELS[row.iso]
        xy = (row.geometry.x, row.geometry.y)
        draw.city_star(ax, xy, size=30)
        _label_place(ax, xy, spec.text or row["name"], spec)

    _draw_flag_panel(ax, s["frame"], capital_names)

    # Bottom-left: the Pacific is empty there, and the panel owns the right.
    draw.draw_footer(ax, s["frame"],
                     "Los siete países de América Central y sus capitales",
                     side="left")
    draw.draw_attribution(ax, s["frame"],
                          "Datos: Natural Earth · Banderas: flagcdn.com",
                          side="left")
    return fig


def render_centroamerica():
    return draw.save(map_centroamerica(), "centroamerica")
