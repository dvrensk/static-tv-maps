"""Food & economy maps of Spain.

Two maps on the parchment base of maps_fisica:

- spain-vinos: the famous wine denominaciones de origen, as soft burgundy
  blobs along their real extents (Rioja follows the Ebro, Ribera del Duero
  the Duero, Rías Baixas the SW Galician coast...).
- spain-despensa: everything else worth eating — the jamón DOPs, the olive
  oil country, huertas, cheeses, shellfish rías and the Almería greenhouse
  sea — color-coded by category with a swatch legend over the Atlantic.

Zone extents are hand-placed polylines/points buffered a few tens of km,
verified against the DOP/IGP zone descriptions (see module git history).
"""

from dataclasses import dataclass

import geopandas as gpd
from matplotlib.colors import to_rgba
from shapely import affinity
from shapely.geometry import LineString, Point

from . import draw, geo, style
from .maps_spain import KM, _draw_country_labels, _project_lonlat, spain_scene

# Parchment base, borrowed from the physical map.
LAND = "#efe8d8"
LAND_EDGE = "#ddd4bf"      # faint internal province borders
COAST = "#8a857a"

FILL_ALPHA = 0.48
LEADER = "#6b675f"

# category -> (blob fill, label color)
CATS = {
    "vino":        ("#8e3a56", "#6d2740"),
    "jamon":       ("#b3653d", "#8a3f1a"),
    "aceite":      ("#8a9a3d", "#5c682a"),
    "huerta":      ("#5eae57", "#2f7332"),
    "invernadero": ("#b9bfc6", "#5f6870"),
    "queso":       ("#e0b33c", "#8f6c12"),
    "marisco":     ("#4f93c4", "#2c6491"),
}


@dataclass
class Zone:
    """A product zone: a blob plus one hand-placed label."""
    name: str
    cat: str
    axis: list                  # [(lon, lat), ...]; a single point = circle
    buffer_km: float
    label: tuple                # (lon, lat) of the label centre
    size: float = 30
    rotation: float = 0.0
    sub: str | None = None      # smaller second line under the name
    sub_size: float = 24
    leader: bool = False        # leader line from the label to the blob
    ha: str = "center"
    clip: bool = True           # clip the blob to the Spanish landmass


def _blob_geom(axis, buffer_km):
    pts = [_project_lonlat(lon, lat) for lon, lat in axis]
    base = Point(pts[0]) if len(pts) == 1 else LineString(pts)
    return base.buffer(buffer_km * KM)


def _draw_zones(ax, zones, spain, frame, zorder=5):
    kper_px = (frame[2] - frame[0]) / style.WIDTH_PX  # data units per pixel
    for z in zones:
        fill, label_color = CATS[z.cat]
        geom = _blob_geom(z.axis, z.buffer_km)
        if z.clip:
            geom = geom.intersection(spain)
        gpd.GeoSeries([geom], crs=geo.MAIN_CRS).plot(
            ax=ax, facecolor=to_rgba(fill, FILL_ALPHA),
            edgecolor=to_rgba(fill, 0.9), linewidth=1.6, zorder=zorder)
        x, y = _project_lonlat(*z.label)
        if z.leader:
            anchor = geom.centroid
            ax.annotate("", xy=(anchor.x, anchor.y), xytext=(x, y),
                        zorder=zorder + 2,
                        arrowprops=dict(arrowstyle="-", color=LEADER,
                                        linewidth=2.2, shrinkA=26, shrinkB=4))
        t = draw.halo_text(ax, x, y, z.name, z.size, weight="extrabold",
                           color=label_color, halo_width=max(3, z.size / 8),
                           ha=z.ha, zorder=zorder + 3)
        t.set_rotation(z.rotation)
        if z.sub:
            n_lines = z.name.count("\n") + 1
            dy = ((z.size * (0.45 + 0.95 * (n_lines - 1)) + z.sub_size * 0.75)
                  * (style.DPI / 72) * kper_px)
            st = draw.halo_text(ax, x, y - dy, z.sub, z.sub_size,
                                weight="semibold", color=label_color,
                                halo_width=4, ha=z.ha, zorder=zorder + 3)
            st.set_rotation(z.rotation)


# ---------------------------------------------------------------------------
# Canary inset items (coordinates in lon/lat, projected via CANARY_CRS and
# then pushed through the inset transform).
# ---------------------------------------------------------------------------

def _project_canary(lon, lat):
    return (gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
            .to_crs(geo.CANARY_CRS).iloc[0].coords[0])


def _canary_blob(axis, buffer_km, tf):
    pts = [_project_canary(lon, lat) for lon, lat in axis]
    base = Point(pts[0]) if len(pts) == 1 else LineString(pts)
    geom = base.buffer(buffer_km * KM)
    scale, origin, dx, dy = tf
    geom = affinity.scale(geom, xfact=scale, yfact=scale, origin=origin)
    return affinity.translate(geom, xoff=dx, yoff=dy)


def _draw_canary_zone(ax, scene, cat, axis, buffer_km, label, label_lonlat,
                      size=26, leader=True, ha="center", zorder=6):
    fill, label_color = CATS[cat]
    tf = scene["canary_tf"]
    geom = _canary_blob(axis, buffer_km, tf)
    geom = geom.intersection(scene["ccaa_can"].union_all())
    gpd.GeoSeries([geom], crs=geo.MAIN_CRS).plot(
        ax=ax, facecolor=to_rgba(fill, FILL_ALPHA),
        edgecolor=to_rgba(fill, 0.9), linewidth=1.4, zorder=zorder)
    x, y = geo.canary_xy(_project_canary(*label_lonlat), tf)
    if leader:
        # Point at the blob part nearest the label, not the union centroid
        # (which may fall in open sea between two islands).
        parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        anchor = min(parts, key=lambda g: g.distance(Point(x, y))).centroid
        ax.annotate("", xy=(anchor.x, anchor.y), xytext=(x, y),
                    zorder=zorder + 1,
                    arrowprops=dict(arrowstyle="-", color=LEADER,
                                    linewidth=2.0, shrinkA=22, shrinkB=4))
    draw.halo_text(ax, x, y, label, size, weight="extrabold",
                   color=label_color, halo_width=4, ha=ha, zorder=zorder + 2)


# ---------------------------------------------------------------------------
# Shared base map
# ---------------------------------------------------------------------------

def _base_map(scene):
    fig, ax = draw.new_map(scene["frame"])
    draw.draw_context(ax, scene["countries"])
    # Parchment Spain with the faintest province borders and one coastline.
    draw.draw_layer(ax, scene["prov_pen"], LAND, LAND_EDGE, 1.0, zorder=2)
    spain = scene["ccaa_pen"].union_all()
    gpd.GeoSeries([spain.boundary], crs=geo.MAIN_CRS).plot(
        ax=ax, color=COAST, linewidth=2.2, zorder=3)
    draw.draw_inset_box(ax, scene["canary_box"], label="Canarias")
    draw.draw_layer(ax, scene["ccaa_can"], LAND, COAST, 1.6, zorder=4)
    return fig, ax, spain


def _swatch_legend(ax, frame, x_frac, y_top_frac, entries, size=28,
                   leading=1.55):
    """Colored-square legend: entries are (category, text)."""
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    row = (size * style.DPI / 72 * leading) / style.HEIGHT_PX
    x_sq = fx0 + x_frac * fw
    x_text = fx0 + (x_frac + 0.011) * fw
    y = y_top_frac
    for cat, text in entries:
        fill, label_color = CATS[cat]
        yy = fy0 + y * fh
        ax.plot(x_sq, yy, marker="s", ms=size * 0.95,
                mfc=to_rgba(fill, 0.75), mec=label_color, mew=2.0, zorder=20)
        draw.halo_text(ax, x_text, yy, text, size, weight="semibold",
                       color="#3c3933", ha="left", va="center", zorder=20)
        y -= row
    return y


# ---------------------------------------------------------------------------
# Map 1 — the wine DOs
# ---------------------------------------------------------------------------

WINE_ZONES = [
    # Galicia / noroeste
    Zone("Rías Baixas", "vino",
         [(-8.85, 42.55), (-8.7, 42.35), (-8.68, 42.1), (-8.8, 41.95)], 12,
         label=(-9.7, 42.28), size=32, sub="albariño", leader=True),
    Zone("Bierzo", "vino", [(-6.65, 42.58)], 16, label=(-6.65, 42.58),
         size=30),
    # Cornisa cantábrica
    Zone("Txakoli", "vino", [(-2.9, 43.32), (-2.2, 43.28)], 12,
         label=(-2.5, 43.62), size=30, leader=True),
    # Valle del Ebro
    Zone("Rioja", "vino",
         [(-2.85, 42.57), (-2.45, 42.47), (-1.96, 42.3), (-1.75, 42.18)], 15,
         label=(-2.35, 42.42), size=36, rotation=-22),
    Zone("Somontano", "vino", [(0.1, 42.05)], 15, label=(0.1, 42.3),
         size=30),
    Zone("Cariñena", "vino", [(-1.22, 41.34)], 15, label=(-1.22, 41.12),
         size=30),
    # Duero
    Zone("Ribera del Duero", "vino",
         [(-4.35, 41.62), (-3.69, 41.67), (-3.2, 41.58)], 15,
         label=(-3.78, 41.63), size=32),
    Zone("Rueda", "vino", [(-4.95, 41.38)], 17, label=(-4.95, 41.16),
         size=30, sub="verdejo"),
    Zone("Toro", "vino", [(-5.39, 41.52)], 14, label=(-5.42, 41.75),
         size=30),
    # Cataluña
    Zone("Penedès", "vino", [(1.45, 41.2), (1.8, 41.43)], 13,
         label=(2.15, 41.1), size=32, sub="cava", leader=True),
    Zone("Priorat", "vino", [(0.82, 41.17)], 11, label=(0.3, 40.98),
         size=30, leader=True),
    # Levante / interior
    Zone("Utiel-Requena", "vino", [(-1.2, 39.57), (-1.1, 39.49)], 14,
         label=(-1.15, 39.82), size=28),
    Zone("Jumilla", "vino", [(-1.55, 38.62), (-1.25, 38.42)], 15,
         label=(-1.4, 38.75), size=30),
    # Meseta sur
    Zone("La Mancha", "vino",
         [(-3.8, 39.5), (-3.1, 39.3), (-2.3, 39.15)], 38,
         label=(-3.1, 39.33), size=40, sub="el mayor viñedo del mundo"),
    Zone("Valdepeñas", "vino", [(-3.38, 38.76)], 14, label=(-3.38, 38.5),
         size=28),
    # Andalucía
    Zone("Jerez", "vino",
         [(-6.35, 36.78), (-6.14, 36.69), (-6.23, 36.6)], 10,
         label=(-6.85, 36.45), size=32, sub="fino y manzanilla",
         leader=True),
    Zone("Montilla-Moriles", "vino", [(-4.63, 37.59), (-4.62, 37.44)], 12,
         label=(-4.62, 37.22), size=28),
]


def map_spain_vinos():
    s = spain_scene()
    fig, ax, spain = _base_map(s)
    _draw_zones(ax, WINE_ZONES, spain, s["frame"])
    # Malvasía de Lanzarote, inside the Canary inset.
    _draw_canary_zone(ax, s, "vino", [(-13.66, 28.98)], 9,
                      "Malvasía de Lanzarote", (-14.7, 28.55), size=25)
    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "El vino en España · principales denominaciones "
                     "de origen (DO)")
    draw.draw_attribution(
        ax, s["frame"],
        "Datos: IGN España · Natural Earth · MAPA (DOP/IGP), zonas aproximadas")
    return fig


def render_spain_vinos():
    return draw.save(map_spain_vinos(), "spain-vinos")


# ---------------------------------------------------------------------------
# Map 2 — the despensa: jamón, aceite, huerta, queso, marisco...
# ---------------------------------------------------------------------------

DESPENSA_ZONES = [
    # --- Jamón (DOP ibérico + DOP/IGP serrano) ---
    Zone("Guijuelo", "jamon", [(-5.67, 40.55)], 13, label=(-5.67, 40.78),
         size=30),
    Zone("Dehesa de\nExtremadura", "jamon",
         [(-6.9, 38.35), (-6.3, 38.75), (-6.0, 39.1)], 28,
         label=(-6.45, 38.65), size=32),
    Zone("Jabugo", "jamon", [(-6.9, 37.9), (-6.5, 37.95)], 12,
         label=(-6.7, 37.68), size=30),
    Zone("Los Pedroches", "jamon", [(-5.1, 38.35), (-4.5, 38.4)], 15,
         label=(-4.8, 38.62), size=28),
    Zone("Jamón de Teruel", "jamon", [(-1.1, 40.45)], 20,
         label=(-1.1, 40.45), size=28),
    Zone("Trevélez", "jamon", [(-3.27, 36.99)], 8, label=(-3.02, 37.17),
         size=26),
    Zone("Serón", "jamon", [(-2.51, 37.35)], 8, label=(-2.51, 37.58),
         size=26),
    # --- Aceite de oliva ---
    Zone("Jaén", "aceite",
         [(-3.5, 37.7), (-3.1, 37.95), (-2.7, 38.25)], 25,
         label=(-3.1, 38.0), size=36, sub="Cazorla · Segura · Mágina"),
    Zone("Baena y Priego", "aceite", [(-4.32, 37.62), (-4.2, 37.44)], 13,
         label=(-4.35, 37.24), size=26),
    Zone("Bajo Aragón", "aceite", [(-0.5, 41.1), (0.0, 40.95)], 16,
         label=(-0.25, 41.3), size=28),
    Zone("Les Garrigues", "aceite", [(0.85, 41.45)], 13,
         label=(0.85, 41.68), size=26),
    Zone("Gata-Hurdes", "aceite", [(-6.6, 40.25), (-6.25, 40.35)], 13,
         label=(-6.5, 40.02), size=26),
    Zone("Montes de Toledo", "aceite", [(-4.7, 39.45), (-4.0, 39.4)], 15,
         label=(-4.35, 39.42), size=26),
    # --- Huerta, fruta y especias ---
    Zone("Huerta de Murcia", "huerta", [(-1.13, 37.99)], 14,
         label=(-1.0, 37.67), size=28),
    Zone("Cítricos", "huerta",
         [(-0.05, 39.9), (-0.33, 39.45), (-0.15, 39.0)], 12,
         label=(0.45, 39.4), size=30, leader=True),
    Zone("Fresas", "huerta", [(-6.84, 37.27), (-7.2, 37.25)], 12,
         label=(-7.08, 36.95), size=28, leader=True),
    Zone("Espárrago y piquillo", "huerta",
         [(-2.08, 42.42), (-1.6, 42.06)], 13,
         label=(-1.35, 42.35), size=26, ha="left"),
    Zone("Pimentón de la Vera", "huerta",
         [(-5.9, 40.05), (-5.5, 40.12)], 10,
         label=(-5.65, 39.86), size=26),
    Zone("Azafrán", "huerta", [(-3.57, 39.45)], 12, label=(-3.57, 39.68),
         size=26),
    Zone("Sidra", "huerta", [(-5.7, 43.4), (-5.4, 43.45)], 12,
         label=(-5.5, 43.72), size=28, leader=True),
    # --- Invernaderos ---
    Zone("Invernaderos de Almería", "invernadero",
         [(-2.95, 36.75), (-2.65, 36.8)], 9,
         label=(-2.4, 36.45), size=28, sub="el «mar de plástico»",
         leader=True),
    # --- Queso ---
    Zone("Queso manchego", "queso", [(-2.5, 39.2)], 20,
         label=(-2.5, 39.2), size=30),
    Zone("Cabrales", "queso", [(-4.85, 43.25)], 8, label=(-4.4, 43.3),
         size=26, ha="left", leader=True),
    Zone("Idiazabal", "queso", [(-2.25, 43.0)], 13, label=(-2.25, 42.78),
         size=26),
    # --- Marisco (blobs in the rías themselves, unclipped) ---
    Zone("Marisco\nde las rías", "marisco",
         [(-9.0, 42.6), (-8.85, 42.25)], 10,
         label=(-9.85, 42.3), size=30, leader=True, clip=False),
]

DESPENSA_LEGEND = [
    ("jamon", "Jamón"),
    ("aceite", "Aceite de oliva"),
    ("huerta", "Huerta, fruta y especias"),
    ("invernadero", "Invernaderos"),
    ("queso", "Queso"),
    ("marisco", "Marisco"),
]


def map_spain_despensa():
    s = spain_scene()
    fig, ax, spain = _base_map(s)
    _draw_zones(ax, DESPENSA_ZONES, spain, s["frame"])
    # Plátano de Canarias: La Palma and north Tenerife, inside the inset.
    _draw_canary_zone(ax, s, "huerta",
                      [(-17.85, 28.65), (-16.7, 28.35)], 9,
                      "Plátano de Canarias", (-16.9, 27.83), size=25)
    _swatch_legend(ax, s["frame"], 0.03, 0.62, DESPENSA_LEGEND)
    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "La despensa de España · jamón, aceite, huerta, "
                     "queso y marisco (DOP/IGP)")
    draw.draw_attribution(
        ax, s["frame"],
        "Datos: IGN España · Natural Earth · MAPA (DOP/IGP), zonas aproximadas")
    return fig


def render_spain_despensa():
    return draw.save(map_spain_despensa(), "spain-despensa")
