"""Asturias maps: the 78 concejos, labels split over two maps."""

from . import cities, draw, geo, hooks, style
from .maps_spain import KM, Label, _label_regions

_SCENE = None

NEIGHBOR_LABELS = [  # lon, lat
    ("GALICIA", -7.06, 43.11, 44),
    ("LEÓN", -5.85, 42.93, 44),
    ("CANTABRIA", -4.62, 43.14, 44),
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
    each map labels ~39 concejos of mixed sizes spread across the region.
    Keyed by concejo name — the key used in CONCEJO_OVERRIDES."""
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
        specs[row.mun_name] = spec
    return specs


def asturias_scene():
    global _SCENE
    if _SCENE is not None:
        return _SCENE
    conc = geo.load("asturias_concejos").to_crs(geo.MAIN_CRS)
    prov = geo.load("provincias").to_crs(geo.MAIN_CRS)
    context = prov[prov.prov_code.isin(["27", "24", "39", "36", "32", "34"])]
    frame = geo.compute_frame(conc.total_bounds, pad=(0.02, 0.06, 0.02, 0.15))
    _SCENE = dict(frame=frame, conc=conc, context=context)
    return _SCENE


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

    colors = greedy_colors(s["conc"], style.CONCEJO_PALETTE)
    draw.draw_layer(ax, s["conc"], colors, style.BORDER_LIGHT, 2.0, zorder=2)
    # Outer border of the region.
    outline = s["conc"].dissolve()
    draw.draw_layer(ax, outline, "none", style.BORDER_DARK, 4.0, zorder=3)

    if group:
        specs = _concejo_specs(s["conc"], group)
        _label_regions(ax, s["conc"], "mun_name",
                       lambda c, r: wrap_name(r.mun_name), specs,
                       table_id="CONCEJO_OVERRIDES")
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

# Comarca colors live in style.py (both themes), keyed by comarca name; every
# pair of neighbouring comarcas differs clearly in hue.

# Label tuning per comarca. Offsets in km. The tight coastal comarcas
# (Avilés, Gijón) keep smaller names nudged into their widest part.
COMARCA_LABELS = {
    "Eo-Navia": Label(56),
    "Narcea": Label(56, dy=-6),
    "Avilés": Label(56, dx=-0.5, dy=2.25),
    "Oviedo": Label(56),
    "Gijón": Label(56, dx=-6.25, dy=2),
    "Caudal": Label(56),
    "Nalón": Label(56),
    "Oriente": Label(56),
}


def _comarca_labels(ax, com, frame):
    """Comarca name plus its padrón population (rounded to the nearest
    thousand) on a second, smaller line, both centred on the tuned anchor."""
    m_per_pt = (frame[2] - frame[0]) / style.WIDTH_PX * style.DPI / 72.0
    for _, row in com.iterrows():
        name = row.comarca
        spec = hooks.spec_for("COMARCA_LABELS", name, COMARCA_LABELS[name])
        x0, y0 = geo.label_point(row.geometry)
        hooks.capture("COMARCA_LABELS", name, name, (x0, y0), spec)
        if hooks.SUPPRESS:
            continue
        x, y = x0 + spec.dx * KM, y0 + spec.dy * KM
        pop = f"({cities.format_population(cities.comarca_population(name))})"
        pop_size = max(24, round(spec.size * 0.6))
        gap = 0.62 * (spec.size + pop_size) * m_per_pt  # between line centres
        if spec.tx is not None:
            tx, ty = x + spec.tx * KM, y + spec.ty * KM
            draw.callout(ax, (x, y), (tx, ty), name, spec.size,
                         weight="extrabold", ha=spec.ha)
            draw.halo_text(ax, tx, ty - gap, pop, pop_size, weight="semibold",
                           ha=spec.ha)
        else:
            draw.halo_text(ax, x, y + gap / 2, name, spec.size,
                           weight="extrabold")
            draw.halo_text(ax, x, y - gap / 2, pop, pop_size,
                           weight="semibold")


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


def map_asturias_comarcas():
    s = asturias_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    conc, com = _comarcas_gdf(s["conc"])
    # Concejos filled with their comarca color, faint internal borders.
    colors = [style.COMARCA_COLORS[c] for c in conc.comarca]
    draw.draw_layer(ax, conc, colors, "#a8a59c", 1.0, zorder=2)
    # Thick dark comarca borders on top, then the outer regional boundary.
    draw.draw_layer(ax, com, "none", style.BORDER_DARK, 4.0, zorder=3)
    draw.draw_layer(ax, conc.dissolve(), "none", style.BORDER_DARK, 5.0, zorder=3)

    _comarca_labels(ax, com, s["frame"])
    _neighbor_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Comarcas de Asturias (ocho comarcas funcionales, "
                     "decreto 11/91) · población INE 2025")
    draw.draw_attribution(ax, s["frame"], "Datos: IGN España")
    return fig


def render_asturias_comarcas():
    return draw.save(map_asturias_comarcas(), "asturias-comarcas")


# ---------------------------------------------------------------------------
# Towns and cities map
# ---------------------------------------------------------------------------

TOWN_COLOR = "#b23a2e"  # warm red dots
CONCEJO_MUTED = "#ece5d4"


def _town_tier(pop):
    """(dot size, label size) by population."""
    if pop >= 100_000:
        return 26, 50
    if pop >= 20_000:
        return 20, 42
    return 14, 36


from dataclasses import dataclass as _dataclass


@_dataclass
class TownLabel(Label):
    # An explicit size overrides the population tier from _town_tier.
    size: float | None = None


# Text placement per town, offsets in km from the dot. Plain dx/dy places the
# name next to the dot; tx/ty draws a leader-line callout (coastal towns point
# into the sea; the crowded centre points into empty countryside).
TOWN_LABELS = {
    "Gijón": TownLabel(dx=2, dy=3.2, ha="left"),
    "Oviedo": TownLabel(dy=-3.25, dx=-2.5),
    "Avilés": TownLabel(tx=-2, ty=9),
    "Pola de Siero": TownLabel(dx=2.2, ha="left"),
    "Langreo": TownLabel(dy=2.9, dx=2),
    "Mieres": TownLabel(dx=-2.2, ha="right"),
    "Piedras Blancas": TownLabel(tx=-7, ty=8, ha="right"),
    "Nubledo": TownLabel(tx=-8, ty=-4, ha="right"),
    "Sotrondio": TownLabel(dy=1.7, dx=7),
    "Villaviciosa": TownLabel(dx=2, ha="left"),
    "Posada": TownLabel(dx=2, ha="left"),
    "Llanes": TownLabel(dy=2.6),
    "Pola de Laviana": TownLabel(dy=-2.2),
    "Cangas del Narcea": TownLabel(dy=2.2),
    "Luarca": TownLabel(dy=5.6, dx=-1.25),
    "Luanco": TownLabel(tx=3, ty=3.5, ha="left"),
    "Pola de Lena": TownLabel(dy=-2.2),
    "Candás": TownLabel(tx=3, ty=3, ha="left"),
    "Cabañaquinta": TownLabel(dx=2, ha="left"),
}


def map_asturias_ciudades():
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
        spec = hooks.spec_for("TOWN_LABELS", town, TOWN_LABELS[town])
        hooks.capture("TOWN_LABELS", town, town, (x, y), spec, tier_size=size)
        if hooks.SUPPRESS:
            continue
        size = spec.size or size
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
    return fig


def render_asturias_ciudades():
    return draw.save(map_asturias_ciudades(), "asturias-ciudades")


# Choropleth twin of the towns map: the whole concejo of each town over 10 000
# inhabitants is painted, shaded by population tier; the rest stay neutral.
# Sequential warm scale (lightens toward white for the smaller tiers).
TIER_FILL = [
    (100_000, "#b23a2e", "más de 100.000 hab."),
    (20_000, "#cd7f77", "20.000 – 100.000 hab."),
    (0, "#e2b4b0", "10.000 – 20.000 hab."),
]


def _tier_fill(pop):
    for floor, color, _ in TIER_FILL:
        if pop >= floor:
            return color
    return TIER_FILL[-1][1]


def render_asturias_ciudades_concejos():
    s = asturias_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    # Population of each concejo that has a town over 10 000 inhabitants.
    conc_pop = {concejo: pop for _t, concejo, pop in cities.ASTURIAS_TOWNS}
    known = set(s["conc"].mun_name)
    for concejo in conc_pop:
        if concejo not in known:
            print(f"  !! concejo not found in dataset: {concejo}")
    colors = [_tier_fill(conc_pop[name]) if name in conc_pop else CONCEJO_MUTED
              for name in s["conc"].mun_name]
    draw.draw_layer(ax, s["conc"], colors, "#d6cdb9", 1.2, zorder=2)
    draw.draw_layer(ax, s["conc"].dissolve(), "none", style.BORDER_DARK, 4.0,
                    zorder=3)

    # Dark dots (so they read on the red fills) + town names.
    points = cities.load_points()
    for town, _concejo, pop in cities.ASTURIAS_TOWNS:
        x, y = points[town]
        _ms, size = _town_tier(pop)
        draw.city_dot(ax, (x, y), size=11, zorder=8)
        spec = TOWN_LABELS[town]
        if spec.tx is not None:
            draw.callout(ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM),
                         town, size, ha=spec.ha)
        else:
            draw.halo_text(ax, x + spec.dx * KM, y + spec.dy * KM, town, size,
                           ha=spec.ha)

    # Tier legend, lower-left over the León side.
    fx0, fy0, fx1, fy1 = s["frame"]
    fw, fh = fx1 - fx0, fy1 - fy0
    lx = fx0 + 0.03 * fw
    ly = fy0 + 0.20 * fh
    step = 0.06 * fh
    for floor, color, text in TIER_FILL:
        ax.plot(lx, ly, marker="s", ms=30, mfc=color, mec="#7a6f5e", mew=1.8,
                zorder=20)
        draw.halo_text(ax, lx + 0.012 * fw, ly, text, 34, weight="semibold",
                       color="#3c3933", ha="left", va="center", zorder=20)
        ly -= step

    _neighbor_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Los concejos más poblados de Asturias · más de "
                     "10.000 habitantes (INE 2023)")
    draw.draw_attribution(ax, s["frame"], "Datos: IGN España")
    return draw.save(fig, "asturias-ciudades-concejos")


# ---------------------------------------------------------------------------
# Rivers map
# ---------------------------------------------------------------------------
# Parchment Asturias with the named rivers a local would recognise, traced
# from OpenStreetMap (data/processed/asturias_rivers.geojson, see
# process_asturias_rivers in scripts/download_data.py). Main stems in full
# blue, well-known tributaries thinner and lighter. Names run along each
# course, rotated to follow the stream.

from dataclasses import dataclass

RIVER = "#3f7fb5"          # main stems (as on the Spain physical map)
RIVER_TRIB = "#6b9cc7"     # tributaries: lighter and thinner
RIVER_MAIN_LW = 5.0
RIVER_TRIB_LW = 3.6


@dataclass
class RiverSpec:
    lon: float
    lat: float
    rotation: float = 0.0
    size: float = 30
    main: bool = True


# Which class each river is drawn in (main = full blue, thicker). The Narcea
# is a Nalón tributary but is one of Asturias' headline rivers, so it reads as
# a main stem; the Cares (Deva tributary, Picos de Europa) stays a tributary.
# lon/lat is where the name sits, rotation follows the local course. All
# hand-tuned so no name touches another name or crosses its own line awkwardly.
ASTURIAS_RIOS = {
    "Nalón":   RiverSpec(-5.4562, 43.2608, -27, 68),
    "Narcea":  RiverSpec(-6.5225, 43.1259, 60, 64),
    "Navia":   RiverSpec(-6.8986, 43.3524, 66, 64),
    "Sella":   RiverSpec(-5.0689, 43.2981, -78, 60),
    "Deva":    RiverSpec(-4.5588, 43.2624, 36.5, 56),
    "Eo":      RiverSpec(-7.0285, 43.4335, 0, 56),
    "Esva":    RiverSpec(-6.5147, 43.5, 68, 52),
    "Piloña":  RiverSpec(-5.3074, 43.391, 6, 56, main=False),
    "Nora":    RiverSpec(-5.6724, 43.4153, -6.5, 56, main=False),
    "Trubia":  RiverSpec(-6.0565, 43.273, 58, 52, main=False),
    "Pigüeña": RiverSpec(-6.320, 43.210, 53, 52, main=False),
    "Caudal":  RiverSpec(-5.8711, 43.2469, -34, 52, main=False),
    "Cares":   RiverSpec(-4.7902, 43.3263, 17, 52, main=False),
    "Piles":   RiverSpec(-5.5736, 43.5165, 0, 48, main=False),
}

# A few reference points so the rivers can be read against known places.
# Oviedo/Gijón for orientation, plus two river-mouth towns. lon, lat.
RIOS_TOWNS = {
    "Oviedo": (-5.845, 43.362),
    "Gijón": (-5.662, 43.545),
    "Ribadesella": (-5.058, 43.462),
    "San Esteban de Pravia": (-6.085, 43.557),
}

RIOS_TOWN_LABELS = {
    "Oviedo": Label(56, dx=3, dy=-1, ha="left"),
    "Gijón": Label(56, dx=3, dy=5.25, ha="left"),
    "Ribadesella": Label(48, tx=4, ty=6, ha="left"),
    "San Esteban de Pravia": Label(48, tx=-4, ty=8, ha="right"),
}


def map_asturias_rios():
    from .maps_spain import _project_lonlat

    s = asturias_scene()
    fig, ax = draw.new_map(s["frame"])
    draw.draw_context(ax, s["context"])

    # Parchment base, exactly like the ciudades map.
    draw.draw_layer(ax, s["conc"], CONCEJO_MUTED, "#d6cdb9", 1.2, zorder=2)
    outline = s["conc"].dissolve()
    draw.draw_layer(ax, outline, "none", style.BORDER_DARK, 4.0, zorder=3)

    # Rivers, clipped to the region outline (buffer a hair so mouths reach the
    # coast). Tributaries first so the main stems draw over them at junctions.
    import geopandas as gpd

    riv = geo.load("asturias_rivers").to_crs(geo.MAIN_CRS)
    clip = outline.union_all().buffer(1.5 * KM)
    for main_pass in (False, True):
        for _, row in riv.iterrows():
            spec = ASTURIAS_RIOS.get(row["name"])
            if spec is None or spec.main != main_pass:
                continue
            color = RIVER if spec.main else RIVER_TRIB
            lw = RIVER_MAIN_LW if spec.main else RIVER_TRIB_LW
            gpd.GeoSeries([row.geometry.intersection(clip)],
                          crs=geo.MAIN_CRS).plot(
                ax=ax, color=color, linewidth=lw, zorder=6, capstyle="round")

    # Reference town dots.
    for town, (lon, lat) in RIOS_TOWNS.items():
        x, y = _project_lonlat(lon, lat)
        draw.city_dot(ax, (x, y), size=13, face="#3a3733", zorder=9)
        spec = hooks.spec_for("RIOS_TOWN_LABELS", town, RIOS_TOWN_LABELS[town])
        hooks.capture("RIOS_TOWN_LABELS", town, town, (x, y), spec)
        if hooks.SUPPRESS:
            continue
        if spec.tx is not None:
            draw.callout(ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM),
                         town, spec.size, ha=spec.ha)
        else:
            draw.halo_text(ax, x + spec.dx * KM, y + spec.dy * KM, town,
                           spec.size, weight="extrabold", ha=spec.ha)

    # River names, in blue, running along each course.
    for name, spec in ASTURIAS_RIOS.items():
        spec = hooks.spec_for("ASTURIAS_RIOS", name, spec)
        x, y = _project_lonlat(spec.lon, spec.lat)
        color = RIVER if spec.main else RIVER_TRIB
        hooks.capture("ASTURIAS_RIOS", name, name, (x, y), spec,
                      color=color, halo=CONCEJO_MUTED)
        if hooks.SUPPRESS:
            continue
        t = draw.halo_text(ax, x, y, name, spec.size, weight="semibold",
                           color=color, halo=CONCEJO_MUTED, halo_width=6,
                           zorder=8)
        t.set_rotation(spec.rotation)

    _neighbor_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"], "Ríos de Asturias")
    draw.draw_attribution(ax, s["frame"], "Datos: OpenStreetMap")
    return fig


def render_asturias_rios():
    return draw.save(map_asturias_rios(), "asturias-rios")