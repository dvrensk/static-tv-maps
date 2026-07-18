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

# One color per autonomous community, keyed by INE acom_code.
# Hand-tuned so that neighbouring communities never share a hue.
CCAA_COLORS = {
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

# Common short names for display (official names are long).
CCAA_DISPLAY = {
    "01": "Andalucía",
    "02": "Aragón",
    "03": "Asturias",
    "04": "Islas Baleares",
    "05": "Canarias",
    "06": "Cantabria",
    "07": "Castilla y León",
    "08": "Castilla-La Mancha",
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
