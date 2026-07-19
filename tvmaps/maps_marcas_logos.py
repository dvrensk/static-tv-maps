"""Spain map of commercial brands at their origin cities, drawn with LOGOS.

The sibling of maps_marcas: same brand roster and same HQ cities (imported
from that module so the two never drift apart), but each brand is rendered as
its company LOGO when a file is available, and otherwise as a coloured
brand-name "chip" in the company's primary colour.

IMPORTANT — logo artwork is NOT shipped with this repository. Real logos are
copyrighted / trademarked, so `assets/logos/` is gitignored and starts empty.
Drop `<slug>.png` files there (see assets/logos/README.md for the exact slug
names) and this map picks them up automatically; with no files present every
brand falls back to a coloured name chip, which is what a fresh checkout
renders. The chips are deliberately plain rounded rectangles with the name in
the bundled Inter font — a coloured label, never an imitation of a logo's
bespoke lettering.

Logos/chips are much bigger than the one-line labels of maps_marcas, so the
dense hubs (Barcelona, Madrid, Bilbao, Valencia...) fan their stacked chips
out over the sea or into empty interior with a leader line back to the dot.
Placement is re-tuned here (see PLACE) because a column of chips needs far
more room than a column of text lines.
"""

import unicodedata
from pathlib import Path

import matplotlib.image as mpimg
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import FancyBboxPatch

from . import draw, geo, style
from .maps_marcas import HUBS
from .maps_productos import _base_map
from .maps_spain import KM, _draw_country_labels, _project_lonlat, spain_scene

LOGO_DIR = Path(__file__).resolve().parent.parent / "assets" / "logos"

DOT_FACE = "#33566e"
DOT_EDGE = "#ffffff"
CITY_COLOR = "#6f6a61"        # muted caption grey for the place name
LEADER = "#7a746a"
CHIP_EDGE = "#ffffff"         # thin white keyline around every chip/logo card
CHIP_TEXT_LIGHT = "#ffffff"
CHIP_TEXT_DARK = "#1c1a17"
LOGO_CARD_FACE = "#ffffff"    # white rounded card behind a real logo

CITY_SIZE = 25                # place-name caption (pt); >= 24 pt / 33 px
CHIP_TEXT_SIZE = 28           # brand name inside a chip (pt); >= 24 pt

# Row geometry, in canvas pixels (converted to data units at draw time).
ROW_H_PX = 66                 # height of one chip / logo card
ROW_GAP_PX = 16               # vertical gap between stacked rows
CHIP_PAD_X_PX = 30            # horizontal padding inside a chip (each side)
LOGO_TARGET_H_PX = 46         # on-canvas height a real logo is scaled to
LOGO_PAD_X_PX = 26            # horizontal padding inside a logo card
CAP_GAP_PX = 14               # gap between the city caption and the first row

# OffsetImage zoom so a logo renders at LOGO_TARGET_H_PX on the canvas.
# Calibrated: on-canvas px = img_px * zoom * DPI/72  ->  zoom = px*72/(img*DPI).
def _logo_zoom(img_h_px: int, target_h_px: float = LOGO_TARGET_H_PX) -> float:
    return target_h_px * 72.0 / (img_h_px * style.DPI)


# ---------------------------------------------------------------------------
# Brand primary colours (facts, hardcoded). Keyed by the exact brand strings
# used in maps_marcas.HUBS. These are plain fill colours for the fallback
# chip, NOT reconstructions of any logo. Any brand missing here falls back to
# a neutral slate.
# ---------------------------------------------------------------------------
BRAND_COLORS = {
    "Inditex · Zara":            "#1a1a1a",  # Zara/Inditex black
    "Estrella Galicia":          "#e4032e",  # red
    "Pescanova":                 "#0067b1",  # blue
    "Central Lechera Asturiana": "#1d5ba6",  # blue
    "BBVA":                      "#072146",  # navy
    "Iberdrola":                 "#74b72e",  # green
    "Corporación Mondragón":     "#2e9e5b",  # green
    "Fagor":                     "#e2001a",  # red
    "Grupo Antolín":             "#003da5",  # blue
    "Campofrío":                 "#e2001a",  # red
    "Pikolin":                   "#0060a9",  # blue
    "Tous":                      "#1a1a1a",  # black (gold bear)
    "Banco Sabadell":            "#00609c",  # blue
    "Mango":                     "#1a1a1a",  # black
    "Estrella Damm":             "#d81e05",  # red
    "Puig":                      "#1a1a1a",  # black
    "Cola Cao":                  "#b01e28",  # cocoa red
    "Gallina Blanca":            "#e2001a",  # red
    "Chupa Chups":               "#ffd200",  # yellow (dark text)
    "SEAT":                      "#e1251b",  # SEAT red
    "Freixenet":                 "#1a1a1a",  # cordón negro black
    "Codorníu":                  "#14213d",  # dark navy
    "Roca":                      "#1a1a1a",  # black
    "Porcelanosa":               "#1a1a1a",  # black
    "Mercadona":                 "#007934",  # green
    "Lladró":                    "#1a1a1a",  # elegant black
    "García Carrión":            "#7a1e2b",  # wine red
    "Don Simón":                 "#f39200",  # orange (dark text)
    "ElPozo":                    "#e2001a",  # red
    "Banco Santander":           "#ec0000",  # Santander red
    "González Byass":            "#2b2b2b",  # black/gold
    "Tío Pepe":                  "#e2001a",  # red jacket
    "Osborne":                   "#1a1a1a",  # black bull
    "Camper":                    "#d81e05",  # red
    "Meliá":                     "#0a2240",  # navy/gold
    "El Corte Inglés":           "#00693c",  # green
    "Repsol":                    "#ef7d00",  # orange (dark text)
    "Telefónica":                "#0066b3",  # blue
    "Iberia":                    "#d3122a",  # red
    "Mahou":                     "#b4121f",  # red
}
DEFAULT_BRAND_COLOR = "#4a4f55"   # neutral slate for anything unlisted


# ---------------------------------------------------------------------------
# Per-hub placement of the chip/logo column, re-tuned for the bigger cards.
# Keyed by hub.city. (tx, ty) is the block anchor offset from the dot in km;
# ha is how the column is aligned at that anchor ("left" columns grow east,
# "right" columns grow west, "center" straddle the anchor). Any hub missing
# here falls back to its maps_marcas placement.
# ---------------------------------------------------------------------------
PLACE = {
    "A Coruña · Arteixo":       (-162, 43, "right"),   # W, over the Atlantic
    "Redondela · Vigo":         (-114, 17, "right"),   # W, over the Atlantic
    "Siero":                    (-128, 102, "center"), # N, Cantabrian sea
    "Santander":                (15, 94, "center"),    # N, into the sea
    "Bilbao":                   (66, 30, "left"),      # E, over the Bay of Biscay
    "Arrasate · Mondragón":     (97, -54, "left"),     # E, over France
    "Burgos":                   (-98, 30, "right"),    # W, over the meseta
    "Zaragoza":                 (-130, -11, "center"), # empty Ebro valley
    "Manresa":                  (-46, 146, "center"),  # N, Catalan interior
    "Sabadell":                 (-27, 39, "right"),    # interior ladder
    "Palau-solità":             (20, 116, "center"),   # N, interior
    "Barcelona":                (83, 76, "left"),      # E, over the Mediterranean
    "Martorell":                (-13, -15, "right"),   # interior ladder
    "Sant Sadurní":             (-88, -71, "right"),   # interior ladder
    "Gavà":                     (73, -151, "left"),    # SE, over the sea
    "Vila-real":                (79, 28, "left"),      # E, over the sea
    "Valencia":                 (100, 4, "left"),      # E, over the sea
    "Jumilla":                  (-66, 38, "right"),    # NW, empty interior
    "Alhama de Murcia":         (72, 16, "left"),      # SE, over the sea
    "Jerez de la Frontera":     (96, 123, "center"),   # N, empty interior
    "El Puerto de Santa María": (133, 31, "left"),     # E, empty interior
    "Inca":                     (81, 20, "left"),      # E, over the sea
    "Palma":                    (29, -48, "center"),   # S, over the sea
    "Madrid":                   (68, 66, "left"),      # E/SE, empty Mancha
}


# ---------------------------------------------------------------------------
# Slug helper: lowercase, accents stripped, non-alphanumerics -> hyphens.
# ---------------------------------------------------------------------------
def brand_slug(name: str) -> str:
    """Filename stem the code looks for in assets/logos/ for a brand.

    e.g. "Inditex · Zara" -> "inditex-zara", "El Corte Inglés" ->
    "el-corte-ingles", "Tío Pepe" -> "tio-pepe"."""
    norm = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in norm if not unicodedata.combining(c))
    out = []
    prev_hyphen = False
    for ch in ascii_only.lower():
        if ch.isalnum():
            out.append(ch)
            prev_hyphen = False
        elif not prev_hyphen:
            out.append("-")
            prev_hyphen = True
    return "".join(out).strip("-")


def _find_logo(name: str):
    """Path to a logo file for `name`, or None. Accepts .png then .jpg."""
    slug = brand_slug(name)
    for ext in (".png", ".jpg", ".jpeg"):
        p = LOGO_DIR / f"{slug}{ext}"
        if p.exists():
            return p
    return None


def _text_color(hex_color: str) -> str:
    """Dark or white text, whichever reads on the given chip colour."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    # perceived luminance
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return CHIP_TEXT_DARK if lum > 0.6 else CHIP_TEXT_LIGHT


# ---------------------------------------------------------------------------
# Drawing one row (either a real logo card or a fallback colour chip).
# cx is the horizontal centre of the row; cy its vertical centre. Returns the
# row's half-width in data units so the caller can size the leader / caption.
# ---------------------------------------------------------------------------
def _row_geoms(dperpx):
    return dict(
        row_h=ROW_H_PX * dperpx,
        gap=ROW_GAP_PX * dperpx,
        pad_x=CHIP_PAD_X_PX * dperpx,
        logo_pad_x=LOGO_PAD_X_PX * dperpx,
    )


def _draw_chip(ax, cx, cy, name, g, zorder=11):
    color = BRAND_COLORS.get(name, DEFAULT_BRAND_COLOR)
    tcolor = _text_color(color)
    w_data, _ = draw._name_width_data(ax, name, CHIP_TEXT_SIZE, "semibold")
    chip_w = w_data + 2 * g["pad_x"]
    chip_h = g["row_h"]
    patch = FancyBboxPatch(
        (cx - chip_w / 2, cy - chip_h / 2), chip_w, chip_h,
        boxstyle=f"round,pad=0,rounding_size={chip_h * 0.30}",
        facecolor=color, edgecolor=CHIP_EDGE, linewidth=2.0,
        zorder=zorder, mutation_aspect=1.0)
    ax.add_patch(patch)
    draw.halo_text(ax, cx, cy, name, CHIP_TEXT_SIZE, weight="semibold",
                   color=tcolor, halo=color, halo_width=0.5,
                   ha="center", va="center", zorder=zorder + 1)
    return chip_w / 2


def _draw_logo(ax, cx, cy, path, g, zorder=11):
    img = mpimg.imread(str(path))
    img_h_px = img.shape[0]
    img_w_px = img.shape[1]
    zoom = _logo_zoom(img_h_px)
    logo_w_data = img_w_px * zoom * (style.DPI / 72) * (
        (ax.get_xlim()[1] - ax.get_xlim()[0]) / style.WIDTH_PX)
    card_w = logo_w_data + 2 * g["logo_pad_x"]
    card_h = g["row_h"]
    patch = FancyBboxPatch(
        (cx - card_w / 2, cy - card_h / 2), card_w, card_h,
        boxstyle=f"round,pad=0,rounding_size={card_h * 0.30}",
        facecolor=LOGO_CARD_FACE, edgecolor=CHIP_EDGE, linewidth=2.0,
        zorder=zorder)
    ax.add_patch(patch)
    oi = OffsetImage(img, zoom=zoom)
    ab = AnnotationBbox(oi, (cx, cy), frameon=False, pad=0, zorder=zorder + 1)
    ax.add_artist(ab)
    return card_w / 2


# When True, _draw_hub records every chip/caption bounding box (in canvas
# pixels-from-top-left) into _BOXES, for the offline overlap checker. Purely a
# development aid; it changes nothing about the rendered PNG.
RECORD = False
_BOXES = []


def _record(frame, city, name, cx, cy, half_w, half_h):
    dperpx = (frame[2] - frame[0]) / style.WIDTH_PX
    x0 = (cx - half_w - frame[0]) / dperpx
    x1 = (cx + half_w - frame[0]) / dperpx
    y0 = (frame[3] - (cy + half_h)) / dperpx   # top edge, px from top
    y1 = (frame[3] - (cy - half_h)) / dperpx   # bottom edge
    _BOXES.append((city, name, x0, y0, x1, y1))


def _draw_hub(ax, frame, hub):
    x, y = _project_lonlat(*hub.lonlat)
    tx, ty, ha = PLACE.get(hub.city, (hub.tx, hub.ty, hub.ha))
    bx, by = x + tx * KM, y + ty * KM     # by = top of the block (city caption)

    dperpx = (frame[2] - frame[0]) / style.WIDTH_PX
    g = _row_geoms(dperpx)
    cap_h = CITY_SIZE * (style.DPI / 72) * dperpx
    cap_gap = CAP_GAP_PX * dperpx
    step = g["row_h"] + g["gap"]

    n = len(hub.brands)
    total_h = cap_h + cap_gap + n * g["row_h"] + (n - 1) * g["gap"]

    # Leader from the dot to the vertical middle of the block at the anchor x.
    if tx or ty:
        ax.annotate("", xy=(x, y), xytext=(bx, by - total_h / 2), zorder=7,
                    arrowprops=dict(arrowstyle="-", color=LEADER,
                                    linewidth=2.2, shrinkA=8, shrinkB=8))

    # City caption at the top of the block.
    draw.halo_text(ax, bx, by, hub.city, CITY_SIZE, weight="semibold",
                   color=CITY_COLOR, ha=ha, va="top", halo_width=5, zorder=13)
    if RECORD:
        cw, _ = draw._name_width_data(ax, hub.city, CITY_SIZE, "semibold")
        ccx = bx + cw / 2 if ha == "left" else bx - cw / 2 if ha == "right" else bx
        _record(frame, hub.city, "(caption)", ccx, by - cap_h / 2, cw / 2, cap_h / 2)

    # Rows stacked downward. Each row's centre x depends on the block ha.
    row_top = by - cap_h - cap_gap
    for i, name in enumerate(hub.brands):
        cy = row_top - i * step - g["row_h"] / 2
        logo = _find_logo(name)
        # Measure the row width first so we can anchor it by ha, then draw.
        if logo is not None:
            half = _measure_logo_half(ax, logo, g)
        else:
            half = _measure_chip_half(ax, name, g)
        if ha == "left":
            cx = bx + half
        elif ha == "right":
            cx = bx - half
        else:
            cx = bx
        if logo is not None:
            _draw_logo(ax, cx, cy, logo, g)
        else:
            _draw_chip(ax, cx, cy, name, g)
        if RECORD:
            _record(frame, hub.city, name, cx, cy, half, g["row_h"] / 2)

    draw.city_dot(ax, (x, y), size=13, face=DOT_FACE, edge=DOT_EDGE, zorder=9)


def _measure_chip_half(ax, name, g):
    w_data, _ = draw._name_width_data(ax, name, CHIP_TEXT_SIZE, "semibold")
    return (w_data + 2 * g["pad_x"]) / 2


def _measure_logo_half(ax, path, g):
    img = mpimg.imread(str(path))
    zoom = _logo_zoom(img.shape[0])
    logo_w_data = img.shape[1] * zoom * (style.DPI / 72) * (
        (ax.get_xlim()[1] - ax.get_xlim()[0]) / style.WIDTH_PX)
    return (logo_w_data + 2 * g["logo_pad_x"]) / 2


def map_spain_marcas_logos():
    s = spain_scene()
    fig, ax, _spain = _base_map(s)

    for hub in HUBS:
        _draw_hub(ax, s["frame"], hub)

    _draw_country_labels(ax, s["frame"])
    draw.draw_footer(ax, s["frame"],
                     "Marcas de España · con sus logotipos")
    draw.draw_attribution(ax, s["frame"], "Datos: elaboración propia")
    return fig


def render_spain_marcas_logos():
    return draw.save(map_spain_marcas_logos(), "spain-marcas-logos")
