"""Shared visual style: canvas size, colors, fonts."""

from pathlib import Path

from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent

# Canvas — the TV wants exactly 4000x2250 (16:9).
WIDTH_PX = 4000
HEIGHT_PX = 2250
DPI = 100  # figsize 40 x 22.5 inches at dpi 100

OCEAN = "#cfe5f2"
NEIGHBOR_FILL = "#e7e6e1"
NEIGHBOR_EDGE = "#c9c8c2"
NEIGHBOR_LABEL = "#a09f99"

BORDER_DARK = "#4d4a45"      # community / outer borders
BORDER_LIGHT = "#7d7a74"     # province / concejo internal borders
LABEL_COLOR = "#26241f"
HALO = "#ffffff"
TITLE_COLOR = "#26241f"

# --- Color themes -----------------------------------------------------------
#
# Political maps come in two palettes, switchable with set_theme():
#   "vivo"   — the original bright scheme.
#   "sobrio" — a muted, desaturated "antique atlas" scheme.
# Each theme defines the community colors (keyed by INE acom_code), the eight
# concejo colors (greedy graph coloring, Asturias) and the eight comarca
# colors. Neighbouring regions are kept distinct within each palette.

# One color per autonomous community. Hand-tuned so neighbours never share a
# hue.
CCAA_COLORS_VIVO = {
    "01": "#a8cf74",  # Andalucía        green
    "02": "#f2b263",  # Aragón           orange
    "03": "#79c6b2",  # Asturias         teal
    "04": "#f2b5c4",  # Illes Balears    pink
    "05": "#f0c95f",  # Canarias         warm yellow
    "06": "#f2a084",  # Cantabria        salmon
    "07": "#ead98b",  # Castilla y León  pale gold
    "08": "#93c6e0",  # Castilla-La Mancha light blue
    "09": "#dd8288",  # Cataluña         soft red
    "10": "#cbb0e3",  # C. Valenciana    light purple
    "11": "#d999b4",  # Extremadura      rose
    "12": "#8fbfe8",  # Galicia          light blue
    "13": "#c3a3dd",  # Madrid           lilac
    "14": "#f0d06b",  # Murcia           gold
    "15": "#e8b0d8",  # Navarra          pink-lilac
    "16": "#b1d98d",  # País Vasco       green
    "17": "#ef8f8f",  # La Rioja         light red
    "18": "#b9c2ea",  # Ceuta            pale indigo
    "19": "#b9e3cf",  # Melilla          pale mint
}

# Muted "antique atlas" palette: lower saturation, earthy and harmonious,
# still keeping every pair of neighbours distinct.
CCAA_COLORS_SOBRIO = {
    "01": "#c9b184",  # Andalucía        muted ochre
    "02": "#cc9e71",  # Aragón           warm amber
    "03": "#86b0a4",  # Asturias         muted teal
    "04": "#c9a1aa",  # Illes Balears    dusty rose
    "05": "#d2c091",  # Canarias         warm sand
    "06": "#8ba6b6",  # Cantabria        slate blue
    "07": "#cdc3a3",  # Castilla y León  pale taupe
    "08": "#a7b88f",  # Castilla-La Mancha sage green
    "09": "#b47f77",  # Cataluña         dusty brick
    "10": "#b3a0bd",  # C. Valenciana    heather
    "11": "#cfa39f",  # Extremadura      dusty coral
    "12": "#8ba0b8",  # Galicia          denim blue
    "13": "#b0a8c6",  # Madrid           stone lilac
    "14": "#cf9e86",  # Murcia           soft terracotta
    "15": "#ad9fbb",  # Navarra          mauve
    "16": "#9cb488",  # País Vasco       soft sage
    "17": "#d2a9ad",  # La Rioja         clay pink
    "18": "#9aa7bd",  # Ceuta            muted indigo
    "19": "#9fc0ab",  # Melilla          muted mint
}

# Eight colors for the Asturias concejo greedy coloring, per theme.
CONCEJO_PALETTE_VIVO = [
    "#a8cf74", "#f2b263", "#8fbfe8", "#f2b5c4",
    "#ead98b", "#79c6b2", "#c3a3dd", "#f2a084",
]
CONCEJO_PALETTE_SOBRIO = [
    "#a7b58a", "#c9a884", "#8ba6b6", "#c9a1aa",
    "#cdc3a3", "#86b0a4", "#ad9fbb", "#cc9e8c",
]

# The eight functional comarcas of Asturias, per theme (neighbours differ).
COMARCA_COLORS_VIVO = {
    "Eo-Navia": "#8fbfe8", "Narcea": "#ead98b", "Avilés": "#f2b5c4",
    "Oviedo": "#a8cf74", "Gijón": "#f2b263", "Caudal": "#c3a3dd",
    "Nalón": "#f2a084", "Oriente": "#79c6b2",
}
COMARCA_COLORS_SOBRIO = {
    "Eo-Navia": "#8ba6b6", "Narcea": "#cdc3a3", "Avilés": "#c9a1aa",
    "Oviedo": "#a7b58a", "Gijón": "#c9a884", "Caudal": "#ad9fbb",
    "Nalón": "#cc9e8c", "Oriente": "#86b0a4",
}

# Vivid "galaxy" palette: saturated pinks, purples, cyans and gold, in the
# cosmic register some younger viewers love. Still medium-light so the dark
# labels and white halos stay readable.
CCAA_COLORS_GALAXIA = {
    "01": "#f2c34d",  # Andalucía        gold
    "02": "#f79a5c",  # Aragón           tiger orange
    "03": "#3fd0c0",  # Asturias         turquoise
    "04": "#f483c0",  # Illes Balears    hot pink
    "05": "#f4d868",  # Canarias         yellow
    "06": "#6fb0ef",  # Cantabria        sky blue
    "07": "#c3a6ee",  # Castilla y León  lavender
    "08": "#5cc2e8",  # Castilla-La Mancha cyan
    "09": "#d15fc0",  # Cataluña         magenta
    "10": "#8f7ce6",  # C. Valenciana    violet
    "11": "#f28cb0",  # Extremadura      pink
    "12": "#7f9cf0",  # Galicia          periwinkle
    "13": "#a86fe0",  # Madrid           bright purple
    "14": "#f78fa0",  # Murcia           coral pink
    "15": "#cf8fe6",  # Navarra          orchid
    "16": "#58cfa8",  # País Vasco       mint green
    "17": "#ec6fb0",  # La Rioja         magenta pink
    "18": "#6fd0e0",  # Ceuta            aqua
    "19": "#b98fe6",  # Melilla          lilac
}
CONCEJO_PALETTE_GALAXIA = [
    "#4fcbd6", "#f483c0", "#8f7ce6", "#f2c34d",
    "#6fb0ef", "#d15fc0", "#f79a5c", "#58cfa8",
]
COMARCA_COLORS_GALAXIA = {
    "Eo-Navia": "#6fb0ef", "Narcea": "#f2c34d", "Avilés": "#f483c0",
    "Oviedo": "#a88fea", "Gijón": "#f79a5c", "Caudal": "#d15fc0",
    "Nalón": "#4fcbd6", "Oriente": "#7f9cf0",
}

THEMES = {
    "vivo": dict(ccaa=CCAA_COLORS_VIVO, concejo=CONCEJO_PALETTE_VIVO,
                 comarca=COMARCA_COLORS_VIVO, suffix=""),
    "sobrio": dict(ccaa=CCAA_COLORS_SOBRIO, concejo=CONCEJO_PALETTE_SOBRIO,
                   comarca=COMARCA_COLORS_SOBRIO, suffix="-sobrio"),
    "galaxia": dict(ccaa=CCAA_COLORS_GALAXIA, concejo=CONCEJO_PALETTE_GALAXIA,
                    comarca=COMARCA_COLORS_GALAXIA, suffix="-galaxia"),
}

# Active theme (mutated by set_theme). Modules read these at render time.
THEME = "vivo"
THEME_SUFFIX = ""
CCAA_COLORS = CCAA_COLORS_VIVO
CONCEJO_PALETTE = CONCEJO_PALETTE_VIVO
COMARCA_COLORS = COMARCA_COLORS_VIVO


def set_theme(name: str) -> None:
    """Switch the active political-map palette ("vivo" or "sobrio")."""
    global THEME, THEME_SUFFIX, CCAA_COLORS, CONCEJO_PALETTE, COMARCA_COLORS
    theme = THEMES[name]
    THEME = name
    THEME_SUFFIX = theme["suffix"]
    CCAA_COLORS = theme["ccaa"]
    CONCEJO_PALETTE = theme["concejo"]
    COMARCA_COLORS = theme["comarca"]

# Common short names for display (official names are long).
CCAA_DISPLAY = {
    "01": "Andalucía",
    "02": "Aragón",
    "03": "Asturias",
    "04": "Islas Baleares",
    "05": "Canarias",
    "06": "Cantabria",
    "07": "Castilla y León",
    "08": "Castilla-\nLa Mancha",
    "09": "Cataluña",
    "10": "Comunidad\nValenciana",
    "11": "Extremadura",
    "12": "Galicia",
    "13": "Madrid",
    "14": "Murcia",
    "15": "Navarra",
    "16": "País Vasco",
    "17": "La Rioja",
    "18": "Ceuta",
    "19": "Melilla",
}

# Castilian display names where the dataset carries the co-official local form.
PROVINCE_DISPLAY = {
    "01": "Álava",
    "03": "Alicante",
    "07": "Islas Baleares",
    "12": "Castellón",
    "38": "Santa Cruz\nde Tenerife",
    "46": "Valencia",
}


def shade(hex_color: str, amount: float) -> str:
    """Lighten (amount > 0) or darken (amount < 0) a hex color by mixing it
    with white/black. Used to tell sibling provinces apart subtly."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    target = 255 if amount > 0 else 0
    t = abs(amount)
    mixed = [round(c + (target - c) * t) for c in rgb]
    return "#" + "".join(f"{c:02x}" for c in mixed)


# Cycle of shade offsets applied to provinces within one community so that
# neighbouring sibling provinces are distinguishable without a border hunt.
PROVINCE_SHADES = [0.12, -0.08, 0.22, -0.16, 0.0, 0.17, -0.12, 0.07, -0.04]


_FONTS_LOADED = False


def load_fonts() -> None:
    """Register the bundled Inter font files with matplotlib."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return
    for ttf in sorted((ROOT / "assets" / "fonts").glob("*.ttf")):
        font_manager.fontManager.addfont(str(ttf))
    _FONTS_LOADED = True


def font(weight: str = "semibold") -> font_manager.FontProperties:
    """FontProperties for the bundled Inter family at a given weight."""
    load_fonts()
    weights = {"regular": 400, "semibold": 600, "extrabold": 800}
    return font_manager.FontProperties(family="Inter", weight=weights[weight])
