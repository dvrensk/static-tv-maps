"""A piano keyboard with the note names: Spanish solfège (Do Re Mi …) and
English letters (A B C …). Not a map, but it shares the TV slideshow, so it
uses the same canvas, fonts, footer and palette.

The keyboard runs from G to the D above the second C, drawn as a realistic
ivory-and-ebony keyboard in a dark case. Half black keys cut off at both ends
keep the first G and the last D from reading as an F and a B.

Each white key carries its solfège name large and its letter in a pill above.
Both are graded by how much they should be read:

- Do to Do is the octave everyone learns: full strength in both languages.
- A and B lead into it in the letters only: A to A is the historical octave,
  so they are lighter, a place where reading could also start.
- Everything else (the first G, the last D, Sol La Si and Re in solfège) is
  greyed out: there for completeness, not to be read.

Black keys follow the same grading for their letter names (C♯ / D♭). Inside
Do to Do they also carry the Spanish names, spelled out ("Do sostenido",
"Re bemol") and running up the key: ♯ and ♭ give no hint of how to say them.
"""

import logging

from matplotlib import patheffects as pe
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

from . import draw, style

WHITE = ["G", "A", "B", "C", "D", "E", "F", "G", "A", "B", "C", "D"]
# Per white key: how strongly each name is shown ("full", "light", "ghost").
LETTER_TIER = ["ghost", "light", "light"] + ["full"] * 8 + ["ghost"]
SOLFEO_TIER = ["ghost"] * 3 + ["full"] * 8 + ["ghost"]

SOLFEO = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La",
          "B": "Si"}
ORDER = "CDEFGAB"
# A black key sits after these white keys (no black key after B or E).
HAS_SHARP_AFTER = {"C", "D", "F", "G", "A"}
NEXT = {"C": "D", "D": "E", "F": "G", "G": "A", "A": "B"}
SHARP, FLAT = "♯", "♭"

# Canvas geometry (design pixels, y up; see `scale` in render_piano).
MARGIN_X = 150
KEY_TOP = 1930
KEY_BOTTOM = 210
BLACK_W_FRAC = 0.58     # of a white key's width
BLACK_LEN_FRAC = 0.63   # of a white key's length
PAD_KEYS = 1            # extra empty space each side, in white-key widths
GAP_PX = 12             # between white keys, on screen

BACKGROUND = style.PANEL_FILL
CASE = "#2b211b"
FELT = "#9b2f2f"
WHITE_EDGE = "#8d877c"
BLACK = "#1d1c1a"
PILL = style.CCAA_COLORS_VIVO["09"]

# Large solfège on the white keys.
SOLFEO_COLOR = {"full": style.LABEL_COLOR, "ghost": "#c4bcac"}
# Letter pills: (fill, edge, text).
PILL_STYLE = {
    "full": (PILL, style.BORDER_DARK, style.LABEL_COLOR),
    "light": (style.shade(PILL, 0.6), "#b39a97", "#6f6862"),
    "ghost": ("#f1ece1", "#c4bcac", "#c4bcac"),
}
# Letter names on the black keys.
BLACK_TEXT = {"full": "#ffffff", "light": "#a39d93", "ghost": "#57534d"}
BLACK_SOLFEO = "#f0c95f"


# The ♯/♭ fallback has no 800 weight; matplotlib would warn on every glyph.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def _font(weight):
    """Inter, falling back to matplotlib's bundled DejaVu for ♯ and ♭."""
    fp = style.font(weight)
    fp.set_family(["Inter", "DejaVu Sans"])
    return fp


def _text(ax, x, y, s, size, color, scale, rotation=0, linespacing=1.2,
          multialignment="center", zorder=10):
    ax.text(x, y, s, fontproperties=_font("extrabold"), fontsize=size * scale,
            color=color, ha="center", va="center", zorder=zorder,
            rotation=rotation, linespacing=linespacing,
            multialignment=multialignment)


def _key_patch(x, y, w, h, radius, **kw):
    return FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={radius}", **kw)


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _gradient(ax, box, top, bottom, clip, zorder):
    """Vertical colour gradient filling `box`, clipped to a key patch."""
    x0, y0, x1, y1 = box
    t = np.linspace(0, 1, 256)[:, None, None]
    a = np.array(_rgb(bottom))[None, None, :]
    b = np.array(_rgb(top))[None, None, :]
    im = ax.imshow(a + (b - a) * t, extent=(x0, x1, y0, y1), origin="lower",
                   aspect="auto", zorder=zorder, interpolation="bilinear")
    im.set_clip_path(clip)


def _black_tier(i):
    """Tier for the black key right of white key i: the weaker neighbour's."""
    rank = {"ghost": 0, "light": 1, "full": 2}
    return min(LETTER_TIER[i], LETTER_TIER[i + 1], key=rank.get)


FOOTER = "Notas del piano · en español (Do Re Mi) y en inglés (A B C)"


def render_piano():
    W, H = style.WIDTH_PX, style.HEIGHT_PX
    n = len(WHITE)
    kw = (W - 2 * MARGIN_X) / n
    # The keyboard is laid out on a W x H design canvas; zooming the view out
    # by `scale` pads PAD_KEYS key widths each side and keeps the proportions.
    # Data-unit geometry shrinks with the view; point sizes (text, lines) are
    # multiplied by `scale` to match.
    scale = W / (W + 2 * PAD_KEYS * kw)
    hw, hh = W / 2 / scale, H / 2 / scale
    frame = (W / 2 - hw, H / 2 - hh, W / 2 + hw, H / 2 + hh)
    fig, ax = draw.new_map(frame)
    ax.set_facecolor(BACKGROUND)
    fig.patch.set_facecolor(BACKGROUND)

    klen = KEY_TOP - KEY_BOTTOM
    bw, blen = kw * BLACK_W_FRAC, klen * BLACK_LEN_FRAC
    x0, xend = MARGIN_X, MARGIN_X + n * kw
    gap = GAP_PX / scale  # without it the keys read as one slab

    # Case: a dark lid above the keys with a strip of red felt, and a dark bed
    # behind them so the gaps show.
    ax.add_patch(_key_patch(x0 - 60, KEY_TOP - 40, n * kw + 120, 230, 30,
                            facecolor=CASE, edgecolor="none", zorder=16))
    ax.add_patch(_key_patch(x0 - 60, KEY_BOTTOM - 60, n * kw + 120, 60, 20,
                            facecolor=CASE, edgecolor="none", zorder=1))
    ax.add_patch(Rectangle((x0 - 60, KEY_BOTTOM - 40), n * kw + 120,
                           klen + 40, facecolor=CASE, zorder=1))
    ax.add_patch(Rectangle((x0, KEY_TOP - 4), n * kw, 22, facecolor=FELT,
                           zorder=17))

    # White keys.
    for i, note in enumerate(WHITE):
        x = x0 + i * kw
        patch = _key_patch(x + gap / 2, KEY_BOTTOM, kw - gap, klen + 60, 22,
                           facecolor="#fbf8f0", edgecolor=WHITE_EDGE,
                           linewidth=1.5 * scale, zorder=2)
        ax.add_patch(patch)
        _gradient(ax, (x, KEY_BOTTOM, x + kw, KEY_TOP + 60),
                  "#e9e3d4", "#fffdf7", patch, zorder=3)
        # Front lip: a slightly darker band at the near end.
        ax.add_patch(_key_patch(x + gap / 2, KEY_BOTTOM, kw - gap, 46, 22,
                                facecolor="#e2dccd", edgecolor="none",
                                zorder=4))

        cx = x + kw / 2
        # "Sol" is the widest name; 98 pt keeps it clear of the key edges.
        _text(ax, cx, KEY_BOTTOM + 190, SOLFEO[note], 98,
              SOLFEO_COLOR[SOLFEO_TIER[i]], scale)
        fill, edge, color = PILL_STYLE[LETTER_TIER[i]]
        py = KEY_BOTTOM + 445
        pill_w, pill_h = kw - 44, 150
        ax.add_patch(_key_patch(cx - pill_w / 2, py - pill_h / 2, pill_w,
                                pill_h, 70, facecolor=fill, edgecolor=edge,
                                linewidth=2.5 * scale, zorder=8))
        _text(ax, cx, py - 4, note, 76, color, scale, zorder=9)

    # Black keys, on the boundary after each C, D, F, G, A. That includes
    # both outer edges, where they are cut off and stay unnamed.
    keyboard = Rectangle((x0, KEY_BOTTOM - 100), n * kw, klen + 400,
                         transform=ax.transData)
    before_first = ORDER[(ORDER.index(WHITE[0]) - 1) % 7]
    for b, note in enumerate([before_first] + WHITE):
        if note not in HAS_SHARP_AFTER:
            continue
        bx = x0 + b * kw - bw / 2
        by = KEY_TOP - blen
        patch = _key_patch(bx, by, bw, blen + 60, 16, facecolor=BLACK,
                           edgecolor="#141311", linewidth=2 * scale,
                           zorder=12)
        ax.add_patch(patch)
        patch.set_clip_path(keyboard)
        _gradient(ax, (max(bx, x0), by, min(bx + bw, xend), KEY_TOP),
                  "#3b3936", "#151413", patch, zorder=13)
        bevel = _key_patch(bx + 14, by + 16, bw - 28, 70, 12,
                           facecolor="#4a4743", edgecolor="none", zorder=14)
        ax.add_patch(bevel)
        bevel.set_clip_path(keyboard)
        if b in (0, n):
            continue

        i = b - 1  # white key to the left
        cx = bx + bw / 2
        upper = NEXT[note]
        color = BLACK_TEXT[_black_tier(i)]
        _text(ax, cx, by + 250, f"{note}{SHARP}", 50, color, scale, zorder=15)
        _text(ax, cx, by + 165, f"{upper}{FLAT}", 50, color, scale, zorder=15)
        if SOLFEO_TIER[i] == SOLFEO_TIER[i + 1] == "full":
            # Too long to sit across a black key, so they run up it, at the
            # same size as the letter names.
            _text(ax, cx, (by + 330 + KEY_TOP - 30) / 2,
                  f"{SOLFEO[note]} sostenido\n{SOLFEO[upper]} bemol", 50,
                  BLACK_SOLFEO, scale, rotation=90, linespacing=1.05,
                  multialignment="left", zorder=15)

    draw.draw_footer(ax, frame, FOOTER, side="right")
    return draw.save(fig, "piano")
