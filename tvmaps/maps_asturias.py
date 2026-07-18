"""Asturias maps: the 78 concejos, labels split over two maps."""

from . import cities, draw, geo, style
from .maps_spain import KM, Label, _label_regions

CONCEJO_PALETTE = [
    "#a8cf74", "#f2b263", "#8fbfe8", "#f2b5c4",
    "#ead98b", "#79c6b2", "#c3a3dd", "#f2a084",
]

NEIGHBOR_LABELS = [  # lon, lat
    ("GALICIA", -7.06, 42.97, 44),
    ("LEÓN", -5.85, 42.93, 44),
    ("CANTABRIA", -4.62, 43.24, 44),
    ("MAR CANTÁBRICO", -5.8, 43.75, 52),
]


def greedy_colors(gdf, palette):
    """Color polygons so that no two touching polygons share a color."""
    geoms = gdf.geometry.values
    n = len(geoms)
    adjacency = [set() for _ in range(n)]
    sindex = gdf.sindex
    for i, g in enumerate(geoms):
        for j in sindex.query(g, predicate="intersects"):
            if int(j) != i:
                adjacency[i].add(int(j))
    order = sorted(range(n), key=lambda i: -len(adjacency[i]))
    assigned = {}
    for i in order:
        used = {assigned[j] for j in adjacency[i] if j in assigned}
        assigned[i] = next(k for k in range(len(palette)) if k not in used)
    return [palette[assigned[i]] for i in range(n)]


def wrap_name(name: str) -> str:
    """Break long concejo names near the middle so labels stay compact."""
    if len(name) <= 10 or " " not in name:
        return name
    words = name.split(" ")
    best, best_diff = None, 1e9
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        diff = abs(len(a) - len(b))
        if diff < best_diff:
            best, best_diff = f"{a}\n{b}", diff
    return best


# Hand overrides: label size / anchor shift / callout, keyed by concejo name.
# Offsets are km. Small coastal concejos point up into the sea; tiny inland
# ones point away from their crowded surroundings.
CONCEJO_OVERRIDES = {
    "Noreña": Label(24, tx=7, ty=9, ha="left"),
    "Muros de Nalón": Label(24, tx=-4, ty=12, ha="right"),
    "Soto del Barco": Label(24, tx=-12, ty=18, ha="right"),
    "Avilés": Label(26, tx=-8, ty=14, ha="right"),
    "Castrillón": Label(26, tx=10, ty=14, ha="left"),
    "Carreño": Label(26, tx=2, ty=10, ha="left"),
    "Gozón": Label(26, dy=-2),
    "Caravia": Label(24, tx=2, ty=10, ha="left"),
    "Gijón": Label(30),
    "Oviedo": Label(30),
    "Santo Adriano": Label(22),
    "Sariego": Label(22),
    "Cabranes": Label(24),
    "Illas": Label(22),
    "Pesoz": Label(22, tx=-4, ty=-16, ha="right"),
    "San Tirso de Abres": Label(22, tx=5, ty=13, ha="left"),
    "San Martín de Oscos": Label(24, dy=4),
    "Ribadedeva": Label(24, tx=-6, ty=10, ha="right"),
}

DEFAULT_SIZE = 28
SMALL_SIZE = 25
SMALL_AREA_KM2 = 150


def _concejo_specs(conc, group):
    """Split the concejos into two label groups by alternating area rank, so
    each map labels ~39 concejos of mixed sizes spread across the region."""
    order = conc.geometry.area.sort_values(ascending=False).index
    specs = {}
    for rank, idx in enumerate(order):
        row = conc.loc[idx]
        g = "A" if rank % 2 == 0 else "B"
        if g != group:
            continue
        spec = CONCEJO_OVERRIDES.get(row.mun_name)
        if spec is None:
            small = row.geometry.area / 1e6 < SMALL_AREA_KM2
            spec = Label(SMALL_SIZE if small else DEFAULT_SIZE)
        specs[row.mun_code] = spec
    return specs


def asturias_scene():
    conc = geo.load("asturias_concejos").to_crs(geo.MAIN_CRS)
    prov = geo.load("provincias").to_crs(geo.MAIN_CRS)
    context = prov[prov.prov_code.isin(["27", "24", "39", "36", "32", "34"])]
    frame = geo.compute_frame(conc.total_bounds, pad=(0.02, 0.06, 0.02, 0.15))
    return dict(frame=frame, conc=conc, context=context)


def _neighbor_labels(ax, frame):
    from .maps_spain import _project_lonlat

    fx0, fy0, fx1, fy1 = frame
    for text, lon, lat, size in NEIGHBOR_LABELS:
        x, y = _project_lonlat(lon, lat)
        if fx0 < x < fx1 and fy0 < y < fy1:
            color = "#7da7bf" if text.startswith("MAR") else style.NEIGHBOR_LABEL
            draw.halo_text(ax, x, y, text, size, weight="semibold",
                           color=color, halo_width=6, zorder=5)


def map_asturias_concejos(group=None):
    s = asturias_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    colors = greedy_colors(s["conc"], CONCEJO_PALETTE)
    draw.draw_layer(ax, s["conc"], colors, style.BORDER_LIGHT, 2.0, zorder=2)
    # Outer border of the region.
    outline = s["conc"].dissolve()
    draw.draw_layer(ax, outline, "none", style.BORDER_DARK, 4.0, zorder=3)

    if group:
        specs = _concejo_specs(s["conc"], group)
        _label_regions(ax, s["conc"], "mun_code",
                       lambda c, r: wrap_name(r.mun_name), specs)
        n = "1" if group == "A" else "2"
        footer = f"Concejos de Asturias (nombres {n} de 2)"
    else:
        footer = "Mapa mudo · Concejos de Asturias"
    _neighbor_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], footer)
    draw.draw_attribution(ax, s["frame"], "Datos: IGN España")
    return fig


def render_asturias_concejos_1():
    return draw.save(map_asturias_concejos("A"), "asturias-concejos-1")


def render_asturias_concejos_2():
    return draw.save(map_asturias_concejos("B"), "asturias-concejos-2")


def render_asturias_concejos_mudo():
    return draw.save(map_asturias_concejos(None), "asturias-concejos-mudo")


# ---------------------------------------------------------------------------
# Comarcas map
# ---------------------------------------------------------------------------

# The dataset's short form differs from the list in cities.py for one concejo.
COMARCA_NAME_ALIASES = {"Tapia de Casariego": "Tapia"}

# Hand-picked pastels (from/near the CCAA palette); every pair of
# neighbouring comarcas differs clearly in hue.
COMARCA_COLORS = {
    "Eo-Navia": "#8fbfe8",   # light blue
    "Narcea": "#ead98b",     # pale gold
    "Avilés": "#f2b5c4",     # pink
    "Oviedo": "#a8cf74",     # green
    "Gijón": "#f2b263",      # orange
    "Caudal": "#c3a3dd",     # lilac
    "Nalón": "#f2a084",      # salmon
    "Oriente": "#79c6b2",    # teal
}

# Label tuning per comarca; the small coastal comarcas (Avilés, Gijón) get
# leader-line callouts into the sea. Offsets in km.
COMARCA_LABELS = {
    "Eo-Navia": Label(48),
    "Narcea": Label(48),
    "Avilés": Label(44, tx=-14, ty=26, ha="right"),
    "Oviedo": Label(48),
    "Gijón": Label(44, tx=10, ty=22, ha="left"),
    "Caudal": Label(44),
    "Nalón": Label(44),
    "Oriente": Label(48),
}


def _comarcas_gdf(conc):
    """Concejos tagged and dissolved by functional comarca."""
    mapping = {}
    for comarca, names in cities.ASTURIAS_COMARCAS.items():
        for name in names:
            mapping[COMARCA_NAME_ALIASES.get(name, name)] = comarca
    names = set(conc.mun_name)
    assert names == set(mapping), (names - set(mapping), set(mapping) - names)
    conc = conc.copy()
    conc["comarca"] = conc.mun_name.map(mapping)
    return conc, conc.dissolve(by="comarca", as_index=False)


def render_asturias_comarcas():
    s = asturias_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    conc, com = _comarcas_gdf(s["conc"])
    # Concejos filled with their comarca color, faint internal borders.
    colors = [COMARCA_COLORS[c] for c in conc.comarca]
    draw.draw_layer(ax, conc, colors, "#a8a59c", 1.0, zorder=2)
    # Thick dark comarca borders on top, then the outer regional boundary.
    draw.draw_layer(ax, com, "none", style.BORDER_DARK, 4.0, zorder=3)
    draw.draw_layer(ax, conc.dissolve(), "none", style.BORDER_DARK, 5.0, zorder=3)

    _label_regions(ax, com, "comarca", lambda c, r: c, COMARCA_LABELS)
    _neighbor_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Comarcas de Asturias (ocho comarcas funcionales, "
                     "decreto 11/91)")
    draw.draw_attribution(ax, s["frame"], "Datos: IGN España")
    return draw.save(fig, "asturias-comarcas")


# ---------------------------------------------------------------------------
# Towns and cities map
# ---------------------------------------------------------------------------

TOWN_COLOR = "#b23a2e"  # warm red dots
CONCEJO_MUTED = "#ece5d4"


def _town_tier(pop):
    """(dot size, label size) by population."""
    if pop >= 100_000:
        return 26, 36
    if pop >= 20_000:
        return 20, 30
    return 14, 26


# Text placement per town, offsets in km from the dot. Plain dx/dy places the
# name next to the dot; tx/ty draws a leader-line callout (coastal towns point
# into the sea; the crowded centre points into empty countryside).
TOWN_LABELS = {
    "Gijón": Label(dx=2, dy=3.2, ha="left"),
    "Oviedo": Label(dy=-3.5),
    "Avilés": Label(tx=-2, ty=9),
    "Pola de Siero": Label(dx=2.2, ha="left"),
    "Langreo": Label(dy=2.4),
    "Mieres": Label(dx=-2.2, ha="right"),
    "Piedras Blancas": Label(tx=-7, ty=8, ha="right"),
    "Nubledo": Label(tx=-8, ty=-4, ha="right"),
    "Sotrondio": Label(dy=2.2),
    "Villaviciosa": Label(dx=2, ha="left"),
    "Posada": Label(dx=2, ha="left"),
    "Llanes": Label(dy=2.6),
    "Pola de Laviana": Label(dy=-2.2),
    "Cangas del Narcea": Label(dy=2.2),
    "Luarca": Label(dy=3.6),
    "Luanco": Label(tx=3, ty=3.5, ha="left"),
    "Pola de Lena": Label(dy=-2.2),
    "Candás": Label(tx=3, ty=3, ha="left"),
    "Cabañaquinta": Label(dx=2, ha="left"),
}


def render_asturias_ciudades():
    s = asturias_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    # One muted fill for all concejos, faint borders, dark outer outline.
    draw.draw_layer(ax, s["conc"], CONCEJO_MUTED, "#d6cdb9", 1.2, zorder=2)
    draw.draw_layer(ax, s["conc"].dissolve(), "none", style.BORDER_DARK, 4.0,
                    zorder=3)

    points = cities.load_points()
    for town, _concejo, pop in cities.ASTURIAS_TOWNS:
        x, y = points[town]
        ms, size = _town_tier(pop)
        draw.city_dot(ax, (x, y), size=ms, face=TOWN_COLOR, zorder=8)
        spec = TOWN_LABELS[town]
        if spec.tx is not None:
            draw.callout(ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM),
                         town, size, ha=spec.ha)
        else:
            draw.halo_text(ax, x + spec.dx * KM, y + spec.dy * KM, town, size,
                           ha=spec.ha)

    _neighbor_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Villas y ciudades de Asturias · concejos de más de "
                     "10.000 habitantes (INE 2023)")
    draw.draw_attribution(ax, s["frame"], "Datos: IGN España")
    return draw.save(fig, "asturias-ciudades")