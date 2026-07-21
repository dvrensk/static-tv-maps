"""Gijón: three nested schematic street maps (metro-map-adjacent but
geographically true). Only the structural streets as bold coloured strokes
with names along them, a handful of landmark pictograms, sea/beach/green
shading. See docs/gijon-schematic-design.md for the full design spec.

Data: data/processed/gijon_{streets,coast,parks,landmarks}.geojson (OSM via
Overpass, see scripts/download_data.py) plus the Piles from
asturias_rivers.geojson and the concejo polygons as the land mask.
"""

from dataclasses import dataclass
from math import atan2, degrees

import geopandas as gpd
import matplotlib.patheffects as pe
import shapely
from shapely.geometry import Point, box
from shapely.ops import polygonize, unary_union

from . import draw, geo, style
from .maps_iconos import _emoji_font
from .maps_spain import _project_lonlat

# --- Canvas arithmetic -------------------------------------------------------
# The spec gives stroke widths in px on the 4000x2250 canvas; matplotlib wants
# points. At style.DPI the conversion is 72/DPI points per pixel.
PX = 72.0 / style.DPI

# --- Frames (EPSG:25830, exact 16:9 — see spec §1; fed straight to new_map,
# NOT through geo.compute_frame). All three share the north edge so they nest.
FRAME_CENTRO = (283076, 4823205, 287593, 4825745)
FRAME_MEDIO = (282020, 4822120, 288465, 4825745)
FRAME_AMPLIO = (279482, 4819997, 289700, 4825745)

# --- Palette (spec §2/§4) ----------------------------------------------------
GROUND = "#f7f4ee"
SAND = "#f2dfae"
SAND_LABEL = "#b5924c"
PARK = "#cde8c4"
PARK_LABEL = "#6f9a5d"
SEA_LABEL = "#7da7bf"
BARRIO = "#c9c2b4"
PIER = "#55524d"
CASING = "#ffffff"


# --- Streets -----------------------------------------------------------------

@dataclass(frozen=True)
class Street:
    label: str                 # display name used when the map labels it
    color: str
    width: float               # stroke width, px at 4000x2250
    rank: int                  # 0 carretera, 1 avenida, 2 calle (drawn last)
    names: tuple = ()          # exact OSM names merged into one stroke
    ref: str | None = None     # ... and/or an OSM ref
    highways: tuple = ()       # highway filter used with `ref`
    keep: tuple | None = None  # lon/lat box: drop everything outside
    cut: tuple | None = None   # lon/lat box: drop everything inside


# The in-city corridor the user means by "AS-19 (Tremañes/Puente Seco)" is
# tagged ref=GJ-10 ("Carretera Xixón-Avilés" / "Ronda de Tremañes"); the
# signed AS-19 only starts west of Veriña, outside every frame. Drawn from
# the GJ-10 ways, labelled "AS-19 · a Avilés" (the pedagogically useful name).
STREETS = {
    # In OSM the "Paseo del Muro de San Lorenzo" runs the WHOLE seafront
    # (the southern half is only officially Avenida de Rufo García Rendueles,
    # which OSM applies to the parallel roadway one block inland — drawing it
    # too doubles the stroke, so the Paseo alone is used) and then continues
    # north-east past the Piles mouth (the Cervigón coastal walk), which the
    # cut box removes.
    "muro": Street("Muro de San Lorenzo", "#e03131", 22, 1,
                   ("Paseo del Muro de San Lorenzo",),
                   keep=(-5.6625, 43.5395, -5.6416, 43.5466),
                   cut=(-5.6448, 43.5414, -5.60, 43.56)),
    "costa": Street("Avenida de la Costa", "#1971c2", 22, 1,
                    ("Avenida de la Costa",)),
    "pablo": Street("Avenida de Pablo Iglesias", "#2f9e44", 22, 1,
                    ("Avenida de Pablo Iglesias",)),
    "llaneza": Street("Avenida de Manuel Llaneza", "#f08c00", 20, 1,
                      ("Avenida de Manuel Llaneza",)),
    "constitucion": Street("Avenida de la Constitución", "#9c36b5", 22, 1,
                           ("Avenida de la Constitución",)),
    "corrida": Street("Calle Corrida", "#0c8599", 16, 2,
                      ("Calle Corrida",)),
    "moros": Street("Calle de Los Moros", "#f06595", 16, 2,
                    ("Calle de Los Moros",)),
    "cajal": Street("Calle Ramón y Cajal", "#a05a2c", 18, 2,
                    ("Calle Ramón y Cajal",)),
    "castilla": Street("Avenida de Castilla", "#495057", 16, 1,
                       ("Avenida de Castilla",)),
    "schulz": Street("Avenida de Schulz", "#c2255c", 20, 1,
                     ("Avenida de Schulz",)),
    "llano": Street("Avenida de El Llano", "#4263eb", 22, 1,
                    ("Avenida de El Llano",)),
    "quevedo": Street("Calle Quevedo", "#15aabf", 18, 2,
                      ("Calle Quevedo",)),
    "portugal": Street("Avenida de Portugal", "#74b816", 18, 1,
                       ("Avenida de Portugal",)),
    "as19": Street("AS-19 · a Avilés", "#343a40", 26, 0,
                   ref="GJ-10", highways=("trunk",)),
    "principe": Street("Avenida Príncipe de Asturias", "#3b7ea1", 22, 1,
                       ("Avenida Príncipe de Asturias",)),
    "galicia": Street("Avenida de Galicia", "#0ca678", 18, 1,
                      ("Avenida de Galicia",)),
    "obispo": Street("Carretera del Obispo", "#7d4a1e", 18, 1,
                     ("Carretera del Obispo",)),
    # The stretch between the Rotonda de Roces and the autovía proper is
    # plain "Avenida de Oviedo" (no ref), hence names + ref combined.
    "as2": Street("AS-II · a Oviedo", "#343a40", 26, 0,
                  ("Avenida de Oviedo",),
                  ref="AS-II", highways=("trunk", "motorway", "primary")),
    "einstein": Street("Avda. de Albert Einstein", "#7048e8", 18, 1,
                       ("Avenida de Albert Einstein",
                        "Avenida de la Pecuaria")),
}


@dataclass(frozen=True)
class SLabel:
    """A street-name label: anchor in lon/lat, size in pt. Rotation comes
    from the local stroke direction unless overridden; `text` overrides the
    street's display name (used where the full name will not fit)."""
    lon: float
    lat: float
    size: float
    rot: float | None = None
    text: str | None = None


# --- Landmarks ---------------------------------------------------------------

@dataclass(frozen=True)
class Mark:
    icon: str | None           # Noto Emoji glyph; None = the Elogio star
    text: str
    side: str = "below"        # name relative to the icon
    name_size: float = 28
    dx: float = 0.0            # nudge of the whole group, km
    dy: float = 0.0


# --- Per-map configuration ---------------------------------------------------

MAPA_CENTRO = dict(
    frame=FRAME_CENTRO,
    key="gijon-calles-centro",
    footer="Gijón · calles principales del centro",
    streets=("muro", "costa", "pablo", "llaneza", "constitucion",
             "castilla", "schulz", "llano", "corrida", "moros", "cajal"),
    labels={
        "muro": SLabel(-5.6515, 43.5442, 40, rot=-15),
        "costa": SLabel(-5.6560, 43.5379, 36),
        "pablo": SLabel(-5.6518, 43.5346, 36),
        "llaneza": SLabel(-5.6643, 43.5350, 28),
        "constitucion": SLabel(-5.6710, 43.5340, 32),
        "corrida": SLabel(-5.6655, 43.5418, 28),
        "moros": SLabel(-5.6620, 43.5410, 26),
        # The full name does not fit between Pablo Iglesias and the frame
        # edge at this scale; the short form everyone uses does.
        "cajal": SLabel(-5.6560, 43.5322, 26, text="Ramón y Cajal"),
        "castilla": SLabel(-5.6468, 43.5382, 26),
    },
    icon_size=54,
    marks={
        "Elogio del Horizonte": Mark(None, "Elogio del Horizonte", "below", 30),
        "Ayuntamiento de Gijón": Mark("\U0001F3DB", "Ayuntamiento", "right", 30),
        "Iglesia de San Pedro": Mark("⛪", "Iglesia de San Pedro",
                                     "right", 28),
        "Puerto Deportivo": Mark("⚓", "Puerto Deportivo", "below", 30),
        "Acuario de Gijón": Mark("\U0001F41F", "Acuario", "below", 30),
        "Teatro Jovellanos": Mark("\U0001F3AD", "Teatro Jovellanos", "below", 28),
        "Estadio El Molinón": Mark("⚽", "El Molinón", "left", 30),
        "CMI El Coto": Mark("\U0001F4DA", "CMI de El Coto", "below", 28),
    },
    sea=(-5.650, 43.552, 48),
    beaches={"Playa de San Lorenzo": (-5.648, 43.5429, 28, -18),
             "Playa de Poniente": (-5.676, 43.5434, 26, 0)},
    parks=("Cerro de Santa Catalina", "Parque de Isabel la Católica",
           "Parque de Begoña"),
    park_labels={"Parque de Isabel la Católica": (-5.643, 43.538, 26)},
    barrios=(),
    barrio_size=46,
    piles_label=None,
    plazas=True,
)

MAPA_MEDIO = dict(
    frame=FRAME_MEDIO,
    key="gijon-calles-medio",
    footer="Gijón · calles principales, del mar a Ceares",
    streets=("muro", "costa", "pablo", "llaneza", "constitucion",
             "castilla", "schulz", "llano", "portugal", "galicia", "principe",
             "corrida", "moros", "cajal", "quevedo"),
    labels={
        "muro": SLabel(-5.6517, 43.5431, 36, rot=-16),
        "costa": SLabel(-5.6570, 43.5381, 32),
        "pablo": SLabel(-5.6518, 43.5344, 32),
        "llaneza": SLabel(-5.6645, 43.5348, 26),
        "constitucion": SLabel(-5.6740, 43.5310, 30),
        "corrida": SLabel(-5.6657, 43.5418, 24),
        "cajal": SLabel(-5.6557, 43.5320, 26),
        "schulz": SLabel(-5.6672, 43.5300, 30),
        "llano": SLabel(-5.6585, 43.5290, 30),
        "quevedo": SLabel(-5.6500, 43.5308, 28),
        "portugal": SLabel(-5.6740, 43.5368, 26),
    },
    icon_size=48,
    marks={
        "Elogio del Horizonte": Mark(None, "Elogio del Horizonte", "below", 28),
        "Ayuntamiento de Gijón": Mark("\U0001F3DB", "Ayuntamiento", "right", 28),
        "Puerto Deportivo": Mark("⚓", "Puerto Deportivo", "below", 28),
        "Estadio El Molinón": Mark("⚽", "El Molinón", "left", 28),
        "CMI El Coto": Mark("\U0001F4DA", "CMI de El Coto", "below", 26),
        "Museo del Ferrocarril": Mark("\U0001F682", "Museo del Ferrocarril",
                                      "below", 26),
        "Estación Sanz Crespo": Mark("\U0001F686", "Estación Sanz Crespo",
                                     "left", 26),
        "Los Fresnos": Mark("\U0001F6CD", "C.C. Los Fresnos", "below", 26,
                            dx=-0.12),
    },
    sea=(-5.648, 43.552, 52),
    beaches={"Playa de San Lorenzo": (-5.6495, 43.5419, 26, -20),
             "Playa de Poniente": (-5.676, 43.5434, 26, 0),
             "Playa L'Arbeyal": None},
    parks=("Cerro de Santa Catalina", "Parque de Isabel la Católica",
           "Parque de Los Pericones"),
    park_labels={"Parque de Isabel la Católica": (-5.643, 43.538, 26),
                 "Parque de Los Pericones": (-5.657, 43.5245, 26)},
    barrios=(("CIMAVILLA", -5.6631, 43.5471), ("EL NATAHOYO", -5.6830, 43.5392),
             ("EL LLANO", -5.6625, 43.5285), ("EL COTO", -5.6503, 43.5336),
             ("CEARES", -5.6553, 43.5304), ("SOMIÓ", -5.6219, 43.5361)),
    barrio_size=46,
    piles_label=(-5.6408, 43.5330, 24),
    plazas=True,
)

MAPA_AMPLIO = dict(
    frame=FRAME_AMPLIO,
    key="gijon-calles-amplio",
    footer="Gijón · calles principales, del mar a Roces y Tremañes",
    streets=tuple(STREETS),
    labels={
        "muro": SLabel(-5.6513, 43.5432, 32, rot=-16),
        "costa": SLabel(-5.6580, 43.5382, 28),
        "pablo": SLabel(-5.6518, 43.5342, 28),
        "constitucion": SLabel(-5.6752, 43.5300, 28),
        "schulz": SLabel(-5.6692, 43.5290, 26),
        "llano": SLabel(-5.6580, 43.5285, 26),
        "quevedo": SLabel(-5.6495, 43.5306, 24),
        "obispo": SLabel(-5.6745, 43.5137, 26),
        "as19": SLabel(-5.7152, 43.5400, 30),
        "principe": SLabel(-5.6952, 43.5393, 26),
        "galicia": SLabel(-5.6872, 43.5411, 26),
        "einstein": SLabel(-5.6340, 43.5257, 26),
        "as2": SLabel(-5.6908, 43.5140, 30),
    },
    icon_size=44,
    marks={
        "Elogio del Horizonte": Mark(None, "Elogio del Horizonte", "below", 26),
        "Ayuntamiento de Gijón": Mark("\U0001F3DB", "Ayuntamiento", "right", 26),
        "Estadio El Molinón": Mark("⚽", "El Molinón", "left", 26),
        "Estación Sanz Crespo": Mark("\U0001F686", "Estación Sanz Crespo",
                                     "left", 26),
        "Universidad Laboral": Mark("\U0001F5FC", "Universidad Laboral",
                                    "left", 26),
        "Jardín Botánico Atlántico": Mark("\U0001F33F", "Jardín Botánico",
                                          "below", 26),
        "Hospital de Cabueñes": Mark("\U0001F3E5", "Hospital de Cabueñes",
                                     "below", 26, dx=-0.25),
        "Acuario de Gijón": Mark("\U0001F41F", "Acuario", "below", 26),
    },
    # The spec point (-5.660, 43.550) sits on the Cerro headland at this
    # scale; moved east over the open bay.
    sea=(-5.628, 43.5515, 56),
    beaches={"Playa de San Lorenzo": (-5.6514, 43.5416, 26, -12),
             "Playa de Poniente": None,
             "Playa L'Arbeyal": (-5.694, 43.5448, 26, 0)},
    parks=("Cerro de Santa Catalina", "Parque de Isabel la Católica",
           "Parque de Los Pericones", "Jardín Botánico Atlántico",
           "Parque de Moreda"),
    park_labels={"Parque de Los Pericones": (-5.657, 43.5245, 26)},
    barrios=(("LA CALZADA", -5.6976, 43.5403), ("EL NATAHOYO", -5.6830, 43.5392),
             ("EL LLANO", -5.6625, 43.5285), ("SOMIÓ", -5.6219, 43.5361),
             ("PUMARÍN", -5.6732, 43.5258), ("ROCES", -5.6812, 43.5174)),
    barrio_size=44,
    piles_label=(-5.6408, 43.5330, 24),
    piles_stop_lat=43.515,
    plazas=False,
)

# Unnamed white dots at the two street hubs (maps 1–2), à la city_dot.
PLAZAS = ((-5.6656, 43.5384), (-5.6591, 43.5361))  # El Humedal, Pl. de Europa


# --- Data loading ------------------------------------------------------------

_CACHE = {}


def _lonlat_box(b):
    """A lon/lat box as a projected polygon (frames tilt ~1.8° vs parallels,
    so the corners are projected and hulled rather than boxed)."""
    lon0, lat0, lon1, lat1 = b
    pts = [_project_lonlat(lon, lat)
           for lon in (lon0, lon1) for lat in (lat0, lat1)]
    return shapely.MultiPoint(pts).convex_hull


def _bridge_gaps(geom, tol=110.0):
    """Connect nearly-touching components of a merged street. OSM interrupts
    a street's name at plazas and roundabouts (whose ways carry other names),
    which would leave white gaps in the stroke."""
    if geom.geom_type != "MultiLineString":
        return geom
    from shapely.geometry import LineString

    parts = list(geom.geoms)
    ends = [(Point(p.coords[0]), Point(p.coords[-1])) for p in parts]
    connectors = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            pair = min(((a, b) for a in ends[i] for b in ends[j]),
                       key=lambda ab: ab[0].distance(ab[1]))
            if 0 < pair[0].distance(pair[1]) < tol:
                connectors.append(LineString([pair[0], pair[1]]))
    return shapely.line_merge(unary_union(parts + connectors))


def _dedupe_parallel(geom, sep=45.0, frac=0.6):
    """Collapse dual carriageways: drop a component when most of it runs
    within `sep` metres of an already-kept longer component."""
    if geom.geom_type != "MultiLineString":
        return geom
    kept = []
    for p in sorted(geom.geoms, key=lambda p: -p.length):
        if kept:
            u = unary_union(kept)
            n = max(2, int(p.length // 30))
            pts = [p.interpolate(i / n, normalized=True) for i in range(n + 1)]
            close = sum(1 for q in pts if u.distance(q) < sep)
            if close / (n + 1) > frac:
                continue
        kept.append(p)
    return shapely.line_merge(unary_union(kept))


def _drop_shreds(geom, min_len=60.0):
    """Remove isolated fragments too short to read as anything but litter."""
    if geom.geom_type != "MultiLineString":
        return geom
    parts = [p for p in geom.geoms if p.length >= min_len]
    return unary_union(parts) if parts else geom


def _data():
    """Load and project everything once; merge each street into one stroke."""
    if _CACHE:
        return _CACHE
    st = geo.load("gijon_streets").to_crs(geo.MAIN_CRS)
    strokes = {}
    for key, spec in STREETS.items():
        mask = st.name.isin(spec.names)  # exact names only
        if spec.ref:
            mask |= (st.ref == spec.ref) & st.highway.isin(spec.highways)
        geom = shapely.line_merge(unary_union(list(st[mask].geometry)))
        if spec.keep:
            geom = geom.intersection(_lonlat_box(spec.keep))
        if spec.cut:
            geom = geom.difference(_lonlat_box(spec.cut))
        strokes[key] = _drop_shreds(_bridge_gaps(_dedupe_parallel(geom)))

    coast = geo.load("gijon_coast").to_crs(geo.MAIN_CRS)
    parks = geo.load("gijon_parks").to_crs(geo.MAIN_CRS)
    lms = geo.load("gijon_landmarks").to_crs(geo.MAIN_CRS)
    riv = geo.load("asturias_rivers").to_crs(geo.MAIN_CRS)
    _CACHE.update(
        strokes=strokes,
        coastline=list(coast[coast.kind == "coastline"].geometry),
        beaches=coast[coast.kind == "beach"],
        marina=coast[coast.kind == "marina"],
        piers=coast[coast.kind == "pier"],
        parks={row["name"]: row.geometry for _, row in parks.iterrows()},
        landmarks={row["name"]: (row.geometry.x, row.geometry.y)
                   for _, row in lms.iterrows()},
        land=geo.load("asturias_concejos").to_crs(geo.MAIN_CRS).union_all(),
        piles=riv[riv.name == "Piles"].union_all(),
    )
    return _CACHE


def _land_faces(frame, data):
    """Polygonize the frame against the OSM coastline; classify each face as
    land or sea by overlap with the concejo polygons. This keeps the harbour
    basins (Puerto Deportivo, El Musel) reading as water."""
    fp = geo.frame_polygon(frame)
    pieces = [g.intersection(fp) for g in data["coastline"]]
    merged = unary_union([p for p in pieces if not p.is_empty] + [fp.boundary])
    return [f for f in polygonize(merged)
            if f.intersection(data["land"]).area / f.area > 0.5]


def _angle_at(geom, x, y):
    """Direction (degrees, in (-90, 90] so text is never upside-down) of the
    stroke nearest to (x, y)."""
    pt = Point(x, y)
    lines = (list(geom.geoms) if geom.geom_type == "MultiLineString"
             else [geom])
    # Short leftovers (roundabout arcs etc.) must not decide the rotation.
    long_lines = [l for l in lines if l.length >= 150]
    line = min(long_lines or lines, key=lambda l: l.distance(pt))
    d = line.project(pt)
    p1 = line.interpolate(max(d - 60, 0))
    p2 = line.interpolate(min(d + 60, line.length))
    ang = degrees(atan2(p2.y - p1.y, p2.x - p1.x)) % 180.0
    return ang - 180.0 if ang > 90.0 else ang


def _plot_geoms(ax, geoms, **kw):
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if geoms:
        gpd.GeoSeries(geoms, crs=geo.MAIN_CRS).plot(ax=ax, **kw)


ICON_COLOR = "#2b2824"


def _draw_mark(ax, xy, mark, icon_size, gap):
    """A landmark: pictograph (or the Elogio star) plus its name."""
    x, y = xy[0] + mark.dx * 1000, xy[1] + mark.dy * 1000
    if mark.icon is None:  # the Elogio del Horizonte
        draw.city_star(ax, (x, y), size=icon_size * 0.8, zorder=11)
    else:
        ax.text(x, y, mark.icon, fontproperties=_emoji_font(icon_size),
                color=ICON_COLOR, ha="center", va="center", zorder=11,
                path_effects=[pe.withStroke(linewidth=max(4, icon_size / 9),
                                            foreground="#ffffff")])
    if mark.side == "below":
        draw.halo_text(ax, x, y - gap, mark.text, mark.name_size,
                       weight="extrabold", ha="center", va="top", zorder=11)
    elif mark.side == "above":
        draw.halo_text(ax, x, y + gap, mark.text, mark.name_size,
                       weight="extrabold", ha="center", va="bottom", zorder=11)
    elif mark.side == "left":
        draw.halo_text(ax, x - gap, y, mark.text, mark.name_size,
                       weight="extrabold", ha="right", va="center", zorder=11)
    else:  # right
        draw.halo_text(ax, x + gap, y, mark.text, mark.name_size,
                       weight="extrabold", ha="left", va="center", zorder=11)


def map_gijon(cfg):
    data = _data()
    frame = cfg["frame"]
    fx0, fy0, fx1, fy1 = frame
    fh = fy1 - fy0
    clip = geo.frame_polygon(frame).buffer(500)

    fig, ax = draw.new_map(frame)

    # Ground: sea (figure background) under near-white land.
    _plot_geoms(ax, _land_faces(frame, data), facecolor=GROUND,
                edgecolor="none", zorder=1)

    # Green, sand, harbour water and piers.
    _plot_geoms(ax, [data["parks"][n].intersection(clip)
                     for n in cfg["parks"] if n in data["parks"]],
                facecolor=PARK, edgecolor="none", zorder=1.6)
    _plot_geoms(ax, [g.intersection(clip) for g in data["beaches"].geometry],
                facecolor=SAND, edgecolor="none", zorder=1.7)
    _plot_geoms(ax, [g.intersection(clip) for g in data["marina"].geometry],
                facecolor=style.OCEAN, edgecolor="none", zorder=1.8)
    _plot_geoms(ax, [g.intersection(clip) for g in data["piers"].geometry],
                color=PIER, linewidth=2.0, zorder=2.2)

    # Río Piles ribbon (a street-style stroke of sea colour).
    piles = data["piles"].intersection(clip)
    if "piles_stop_lat" in cfg:
        _, ystop = _project_lonlat(-5.640, cfg["piles_stop_lat"])
        piles = piles.intersection(box(fx0 - 500, ystop, fx1 + 500, fy1 + 500))
    _plot_geoms(ax, [piles], color=style.OCEAN, linewidth=30 * PX, zorder=2.0,
                capstyle="round")

    # Barrio ghost names, under the strokes.
    for text, lon, lat in cfg["barrios"]:
        x, y = _project_lonlat(lon, lat)
        ax.text(x, y, text, fontproperties=style.font("semibold"),
                fontsize=cfg["barrio_size"], color=BARRIO, ha="center",
                va="center", zorder=3)

    # Streets: carreteras first, then avenidas, calles on top. Each stroke
    # carries its own white casing just underneath, so crossings read.
    drawn = sorted(cfg["streets"], key=lambda k: (STREETS[k].rank, k))
    for i, key in enumerate(drawn):
        spec = STREETS[key]
        geom = data["strokes"][key].intersection(clip)
        if geom.is_empty:
            continue
        z = 4 + 0.02 * i
        for lw, color, dz in ((spec.width + 8, CASING, 0.0),
                              (spec.width, spec.color, 0.01)):
            _plot_geoms(ax, [geom], color=color, linewidth=lw * PX,
                        zorder=z + dz, capstyle="round", joinstyle="round")

    # Small white hub dots at El Humedal and Plaza de Europa (maps 1–2).
    if cfg["plazas"]:
        for lon, lat in PLAZAS:
            x, y = _project_lonlat(lon, lat)
            draw.city_dot(ax, (x, y), size=11, face="#ffffff", edge="#3a3733",
                          zorder=6)

    # Street names: rotated along the stroke, darkened stroke colour.
    for key, lab in cfg["labels"].items():
        spec = STREETS[key]
        x, y = _project_lonlat(lab.lon, lab.lat)
        rot = (lab.rot if lab.rot is not None
               else _angle_at(data["strokes"][key], x, y))
        t = draw.halo_text(ax, x, y, lab.text or spec.label, lab.size,
                           weight="extrabold",
                           color=style.shade(spec.color, -0.25), zorder=8)
        t.set_rotation(rot)

    # Sea, beach, river and park names.
    lon, lat, size = cfg["sea"]
    x, y = _project_lonlat(lon, lat)
    draw.halo_text(ax, x, y, "MAR CANTÁBRICO", size, weight="semibold",
                   color=SEA_LABEL, halo_width=6, zorder=7)
    for name, lab in cfg["beaches"].items():
        if lab is None:
            continue
        lon, lat, size, rot = lab
        x, y = _project_lonlat(lon, lat)
        t = draw.halo_text(ax, x, y, name, size, weight="semibold",
                           color=SAND_LABEL, halo_width=5, zorder=7)
        t.set_rotation(rot)
    if cfg["piles_label"]:
        lon, lat, size = cfg["piles_label"]
        x, y = _project_lonlat(lon, lat)
        rot = _angle_at(data["piles"], x, y)
        t = draw.halo_text(ax, x, y, "río Piles", size, weight="semibold",
                           color=SEA_LABEL, halo_width=5, zorder=7)
        t.set_rotation(rot)
    for name, (lon, lat, size) in cfg["park_labels"].items():
        short = "Los Pericones" if "Pericones" in name else name
        x, y = _project_lonlat(lon, lat)
        draw.halo_text(ax, x, y, short, size, weight="semibold",
                       color=PARK_LABEL, halo_width=5, zorder=7)

    # Landmarks.
    gap = 0.014 * fh
    for name, mark in cfg["marks"].items():
        _draw_mark(ax, data["landmarks"][name], mark, cfg["icon_size"], gap)

    draw.draw_footer(ax, frame, cfg["footer"])
    draw.draw_attribution(ax, frame, "Datos: © OpenStreetMap")
    return draw.save(fig, cfg["key"])


def render_gijon_calles_centro():
    return map_gijon(MAPA_CENTRO)


def render_gijon_calles_medio():
    return map_gijon(MAPA_MEDIO)


def render_gijon_calles_amplio():
    return map_gijon(MAPA_AMPLIO)
