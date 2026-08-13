"""América Central, in two framings.

`centroamerica` — the seven countries of the isthmus with their capitals named
on the map. The isthmus is much taller than 16:9, so a whole column of canvas
is free on the Caribbean side: that column holds the flags, each with its
country and capital, in north-west to south-east order.

`mexico-centroamerica-caribe` — the same idea zoomed out to México and the
three Spanish-speaking Antilles (Cuba, República Dominicana, Puerto Rico).
Mexico's width sets the scale, which leaves the isthmus too small for six
capital names, so there the capitals are stars only and the panel — a 3x4 grid
of flags over the empty Pacific — is what names them.

In both, the passe-partout around every flag repeats the country's fill color
on the map, so a viewer can pair flag and country without reading a legend.
"""

from dataclasses import dataclass

from . import draw, geo, hooks, style

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


def _project_lonlat(lon, lat, crs=geo.CENTRAL_AMERICA_CRS):
    import geopandas as gpd
    from shapely.geometry import Point

    return (
        gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
        .to_crs(crs)
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
    "GT": Place(52, dx=25, dy=94),         # up into the Petén
    "BZ": Place(42, tx=108, ty=52, ha="left"),      # east, into the Caribbean
    # East end of the country, then down into the Golfo de Fonseca: the only
    # water nearby that the San Salvador label does not already occupy.
    "SV": Place(42, dx=95, dy=-20, tx=-24, ty=-128),
    "HN": Place(52, dx=10, dy=35),
    "NI": Place(52, dy=45),
    "CR": Place(44, dx=-45, dy=-70),
    "PA": Place(44, dx=-40, dy=15),
}

# Capitals: star + name. Offsets in km from the point.
CAPITAL_LABELS = {
    "GT": Place(34, dx=-30, dy=10, ha="right", text="Ciudad de\nGuatemala"),
    "BZ": Place(34, dx=96, dy=-30, ha="right"),
    "SV": Place(34, dx=-40, dy=-30),
    "HN": Place(34, dx=-22, dy=36, ha="left"),
    "NI": Place(34, dx=140, dy=-16, ha="right"),
    "CR": Place(34, dx=-46, dy=34, ha="left"),
    # East of its star, to leave the canal's leader line a clear run north-east.
    "PA": Place(34, dx=28, dy=8, ha="left", text="Ciudad de\nPanamá"),
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

# --- Panama Canal ----------------------------------------------------------
#
# Natural Earth has no canal for this region, so the course is traced by hand
# (the same treatment the Nervión and Llobregat get on the Spanish maps):
# Cristóbal/Colón on the Caribbean, up the Gatún locks and across the lake to
# Gamboa, then Pedro Miguel and Miraflores down to Balboa on the Pacific.
# Only ~60 km end to end, so it is drawn as a cased line to stay visible.
CANAL_LONLAT = [
    (-79.917, 9.371), (-79.905, 9.290), (-79.845, 9.230), (-79.780, 9.190),
    (-79.700, 9.120), (-79.630, 9.045), (-79.588, 8.985), (-79.556, 8.930),
]
CANAL_COLOR = "#1a4a8a"


def _draw_canal(ax, spec, crs=geo.CENTRAL_AMERICA_CRS, width=5.0, casing=11.0):
    """The Panama Canal as a white-cased line, plus its label on a leader."""
    pts = [_project_lonlat(lon, lat, crs) for lon, lat in CANAL_LONLAT]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ax.plot(xs, ys, "-", color="#ffffff", linewidth=casing, solid_capstyle="round",
            zorder=6)
    ax.plot(xs, ys, "-", color=CANAL_COLOR, linewidth=width,
            solid_capstyle="round", zorder=7)
    mid = pts[len(pts) // 2]
    _label_place(ax, mid, spec.text or "Canal de Panamá", spec)


# Both maps put the canal's name in the Caribbean north-east of it: the Gulf of
# Panama side is already busy with the capital and the Islas Perlas.
CANAL_LABEL = Place(34, tx=95, ty=145, ha="left")


def _draw_context_labels(ax, frame, panel, context=None, water=None,
                         crs=geo.CENTRAL_AMERICA_CRS):
    """Neighbours and seas, skipping anything that would land under the panel."""
    fx0, fy0, fx1, fy1 = frame
    px0, py0, px1, py1 = panel
    pairs = ((context if context is not None else CONTEXT_LABELS,
              style.NEIGHBOR_LABEL),
             (water if water is not None else WATER_LABELS, WATER_COLOR))
    for labels, color in pairs:
        for text, lon, lat, size, rotation in labels:
            x, y = _project_lonlat(lon, lat, crs)
            if not (fx0 < x < fx1 and fy0 < y < fy1):
                continue
            if px0 < x < px1 and py0 < y < py1:
                continue
            t = draw.halo_text(ax, x, y, text, size, weight="semibold",
                               color=color, halo_width=7, zorder=5)
            t.set_rotation(rotation)


def _flag_entry(ax, u, left, cy, iso, name, capital, flag_w=270, name_size=46,
                cap_size=34, gap=30, name_dy=10, cap_dy=40, star=22,
                star_dx=18, cap_dx=44, mat_px=8, pop=None, pop_size=24,
                pop_dy=50):
    """One panel entry: matted flag, country name, star + capital name, and
    optionally a third line with the population.

    `left`/`cy` are the flag's left edge and vertical centre; every other
    measurement is in canvas pixels, scaled to data units by `u`."""
    draw.flag(ax, FLAGS / f"{iso}.png", left, cy, width=flag_w * u,
              mat_color=style.COUNTRY_COLORS[iso], mat_px=mat_px)
    text_left = left + (flag_w + gap) * u
    draw.halo_text(ax, text_left, cy + name_dy * u, name, name_size,
                   weight="extrabold", color=style.LABEL_COLOR, halo_width=0,
                   ha="left", va="bottom", zorder=20)
    draw.city_star(ax, (text_left + star_dx * u, cy - cap_dy * u), size=star,
                   zorder=20)
    draw.halo_text(ax, text_left + cap_dx * u, cy - cap_dy * u, capital,
                   cap_size, weight="semibold", color="#4a4741", halo_width=0,
                   ha="left", zorder=20)
    if pop:
        draw.halo_text(ax, text_left, cy - pop_dy * u, pop, pop_size,
                       weight="semibold", color="#7a776f", halo_width=0,
                       ha="left", zorder=20)


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
    for i, iso in enumerate(ORDER):
        _flag_entry(ax, u, bx0 + 30 * u, top - (i + 0.5) * row_h, iso,
                    COUNTRY_NAMES[iso], capital_names[iso])


def _label_place(ax, xy, text, spec, weight="extrabold", table_id=None,
                 key=None):
    """Place `text` for a feature anchored at `xy`, per the Place spec."""
    spec = hooks.spec_for(table_id, key, spec)
    hooks.capture(table_id, key, text, xy, spec)
    if hooks.SUPPRESS:
        return
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
    colors = [style.COUNTRY_COLORS[i] for i in main.iso]
    draw.draw_layer(ax, main, colors, style.BORDER_DARK, 3.0, zorder=2)

    _draw_context_labels(ax, s["frame"], panel_rect(s["frame"]))

    for _, row in main.iterrows():
        spec = COUNTRY_LABELS[row.iso]
        xy = geo.label_point(row.geometry, tol=1000.0)
        _label_place(ax, xy, spec.text or COUNTRY_NAMES[row.iso], spec,
                     table_id="COUNTRY_LABELS", key=row.iso)

    _draw_canal(ax, CANAL_LABEL)

    capital_names = dict(zip(s["capitals"].iso, s["capitals"]["name"]))
    for _, row in s["capitals"].iterrows():
        spec = CAPITAL_LABELS[row.iso]
        xy = (row.geometry.x, row.geometry.y)
        draw.city_star(ax, xy, size=30)
        _label_place(ax, xy, spec.text or row["name"], spec,
                     table_id="CAPITAL_LABELS", key=row.iso)

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


# ---------------------------------------------------------------------------
# Extended variant: México, América Central y el Caribe hispano
# ---------------------------------------------------------------------------
#
# Mexico's width (Baja California to Yucatán) sets the scale here, so the
# isthmus is roughly half the size it has on the map above. The flag panel
# therefore moves into the empty Pacific south-west of Mexico — the only free
# block big enough — and grows a second and third column. Six capital names
# will not fit inside the isthmus at this scale, so on this map the capitals
# are stars and the panel is what names them.

# Column-major reading order: Mexico + the isthmus fill the first two columns,
# the Antilles the third.
EXT_ORDER = ["MX", "GT", "BZ", "SV", "HN", "NI", "CR", "PA", "CU", "DO", "PR"]

# Mainland framing box (lon/lat): drops Isla del Coco and the Islas del Cisne.
EXT_CORE_BOX = (-118.0, 6.9, -64.9, 33.0)

# Panel box in canvas pixels, measured from the lower-left corner. The rule the
# top edge obeys: no Mexican territory may be covered. The Pacific coast comes
# down to y≈712 px around Michoacán and the Islas Revillagigedo sit at y≈1045,
# so 700 is as tall as this panel can get at this width — and every pixel is
# needed, because each cell carries three lines of text.
EXT_PANEL_PX = (28, 24, 1716, 700)
EXT_COLS, EXT_ROWS = 3, 4

# Panel cells are ~548 px wide, which is not enough for every name at full
# length: the Dominican Republic gets the usual atlas abbreviation (a two-line
# wrap would climb into the row above).
EXT_PANEL_NAMES = {"DO": "Rep. Dominicana"}
EXT_PANEL_CAPITALS = {}

# Population for the panel, deliberately rounded to numbers a viewer can
# remember and repeat: whole millions above five, half millions below, and
# thousands for Belice. Estimates for 2024 (UN World Population Prospects);
# they move slowly enough that the rounding outlives the data.
COUNTRY_POPULATION = {
    "MX": "130 millones",
    "GT": "18 millones",
    "BZ": "400 mil",
    "SV": "6 millones",
    "HN": "11 millones",
    "NI": "7 millones",
    "CR": "5 millones",
    "PA": "4,5 millones",
    "CU": "11 millones",
    "DO": "11 millones",
    "PR": "3 millones",
}


def ext_scene():
    countries = geo.load("mexico_caribe")
    capitals = geo.load("mexico_caribe_capitales")
    core = countries[countries.role == "centro"].clip(EXT_CORE_BOX)
    frame = geo.compute_frame(core.to_crs(geo.MEXICO_CARIBE_CRS).total_bounds,
                              pad=(0.012, 0.02, 0.012, 0.02))
    return dict(
        frame=frame,
        main=countries[countries.role == "centro"].to_crs(geo.MEXICO_CARIBE_CRS),
        context=countries[countries.role == "contexto"].to_crs(geo.MEXICO_CARIBE_CRS),
        capitals=capitals.to_crs(geo.MEXICO_CARIBE_CRS),
    )


def ext_panel_rect(frame):
    u = _px(frame)
    x0, y0, x1, y1 = EXT_PANEL_PX
    return (frame[0] + x0 * u, frame[1] + y0 * u,
            frame[0] + x1 * u, frame[1] + y1 * u)


EXT_COUNTRY_LABELS = {
    "MX": Place(48, dy=60),
    "GT": Place(32, dx=15, dy=59.4),
    "BZ": Place(32, ha="left", dx=125, dy=25),
    "SV": Place(32, dx=38.2, dy=-120, ha="right"),
    "HN": Place(32, dx=25, dy=20),
    "NI": Place(32, dy=25),
    "CR": Place(32, ha="right", dx=-55, dy=-125),
    "PA": Place(32, dx=5, dy=194.1),           # north, into the Caribbean
    "CU": Place(44, dx=-445, dy=5),
    # Both Antilles labels go north into the Atlantic; keep them clear of each
    # other by stacking República Dominicana higher than Puerto Rico.
    "DO": Place(32, text="República\nDominicana", dx=-10, dy=-270.9),
    "PR": Place(32, dx=40, dy=-100),
}

EXT_CONTEXT_LABELS = [
    ("ESTADOS UNIDOS", -101.5, 31.6, 50, 0),
    ("BAHAMAS", -77.4, 24.6, 30, 0),
    ("HAITÍ", -72.75, 19.05, 26, 0),
    ("JAMAICA", -77.3, 18.15, 26, 0),
    ("COLOMBIA", -74.6, 7.4, 40, 0),
    ("VENEZUELA", -68.3, 8.2, 40, 0),
]

EXT_CANAL_LABEL = Place(28, tx=130, ty=125, ha="left")

EXT_WATER_LABELS = [
    ("GOLFO DE MÉXICO", -93.4, 24.6, 46, 0),
    ("MAR CARIBE", -76.6, 14.2, 46, 0),
    ("OCÉANO\nPACÍFICO", -108.5, 16.8, 44, 0),
    ("OCÉANO\nATLÁNTICO", -68.0, 26.0, 44, 0),
]


def _draw_ext_panel(ax, frame, capital_names):
    u = _px(frame)
    box = ext_panel_rect(frame)
    draw.panel_box(ax, box)
    bx0, by0, bx1, by1 = box

    draw.halo_text(ax, (bx0 + bx1) / 2, by1 - 20 * u,
                   "México, América Central y el Caribe hispano", 42,
                   weight="extrabold", color=style.LABEL_COLOR, halo_width=0,
                   va="top", zorder=20)
    draw.halo_text(ax, (bx0 + bx1) / 2, by1 - 76 * u,
                   "banderas, capitales y población · "
                   "la estrella marca la capital", 24,
                   weight="semibold", color="#6b6862", halo_width=0,
                   va="top", zorder=20)

    grid_top = by1 - 116 * u
    cell_w = (bx1 - bx0 - 44 * u) / EXT_COLS
    cell_h = (grid_top - by0 - 12 * u) / EXT_ROWS
    for i, iso in enumerate(EXT_ORDER):
        col, row = divmod(i, EXT_ROWS)
        _flag_entry(ax, u, bx0 + 22 * u + col * cell_w,
                    grid_top - (row + 0.5) * cell_h, iso,
                    EXT_PANEL_NAMES.get(iso, COUNTRY_NAMES[iso]),
                    EXT_PANEL_CAPITALS.get(iso, capital_names[iso]),
                    flag_w=132, name_size=30, cap_size=24, gap=16, name_dy=18,
                    cap_dy=8, star=16, star_dx=13, cap_dx=32, mat_px=6,
                    pop=COUNTRY_POPULATION[iso], pop_size=24, pop_dy=50)

    # The twelfth cell is free: use it to say what Puerto Rico is, since it is
    # the one protagonist that is not a sovereign country, and to source the
    # population figures next to where they are read.
    col, row = divmod(len(EXT_ORDER), EXT_ROWS)
    cx, cy = bx0 + 22 * u + col * cell_w, grid_top - (row + 0.5) * cell_h
    draw.halo_text(ax, cx, cy + 16 * u,
                   "Puerto Rico es un\nterritorio de Estados Unidos", 24,
                   weight="semibold", color="#6b6862", halo_width=0,
                   ha="left", zorder=20)
    draw.halo_text(ax, cx, cy - 50 * u,
                   "Población: ONU 2024, redondeada", 20,
                   weight="regular", color="#8a8880", halo_width=0,
                   ha="left", zorder=20)


# Display names for the protagonists the extended map adds.
COUNTRY_NAMES.update({
    "MX": "México", "CU": "Cuba", "DO": "República Dominicana",
    "PR": "Puerto Rico",
})


def map_mexico_centroamerica_caribe():
    s = ext_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    main = s["main"]
    colors = [style.COUNTRY_COLORS[i] for i in main.iso]
    draw.draw_layer(ax, main, colors, style.BORDER_DARK, 2.4, zorder=2)

    _draw_context_labels(ax, s["frame"], ext_panel_rect(s["frame"]),
                         context=EXT_CONTEXT_LABELS, water=EXT_WATER_LABELS,
                         crs=geo.MEXICO_CARIBE_CRS)

    for _, row in main.iterrows():
        spec = EXT_COUNTRY_LABELS[row.iso]
        xy = geo.label_point(row.geometry, tol=1000.0)
        _label_place(ax, xy, spec.text or COUNTRY_NAMES[row.iso], spec,
                     table_id="EXT_COUNTRY_LABELS", key=row.iso)

    _draw_canal(ax, EXT_CANAL_LABEL, crs=geo.MEXICO_CARIBE_CRS, width=4.0,
                casing=9.0)

    for _, row in s["capitals"].iterrows():
        draw.city_star(ax, (row.geometry.x, row.geometry.y), size=26)

    capital_names = dict(zip(s["capitals"].iso, s["capitals"]["name"]))
    _draw_ext_panel(ax, s["frame"], capital_names)

    draw.draw_attribution(ax, s["frame"],
                          "Datos: Natural Earth · Banderas: flagcdn.com")
    return fig


def render_mexico_centroamerica_caribe():
    return draw.save(map_mexico_centroamerica_caribe(),
                     "mexico-centroamerica-caribe")
