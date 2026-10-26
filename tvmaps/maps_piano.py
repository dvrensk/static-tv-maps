"""A piano keyboard with the note names: English letters (A B C …) and
Spanish solfège (Do Re Mi …). Not a map, but it shares the TV slideshow, so it
uses the same canvas, fonts, footer and palette.

The keyboard runs from G (unlabelled, so the first name you read is A) up to
the D above the second C. Letters go on every key from that A onwards; the
solfège covers one octave, Do to Do, and carries on greyed out over the
keys either side. Half black keys cut off at both ends keep the first G and
the last D from reading as an F and a B. Black keys carry both sharp and flat
names; inside that octave also the Spanish ones, spelled out ("Do sostenido",
"Re bemol") and running up the key.

Three designs share the geometry and labels: "clasico" (realistic ivory and
ebony), "esquema" (flat, map-like outlines) and "colores" (one pastel per
note, from the political-map palette).
"""

import logging

from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

from . import draw, style

# White keys left to right; the first one is deliberately unlabelled.
WHITE = ["G", "A", "B", "C", "D", "E", "F", "G", "A", "B", "C", "D"]
FIRST_LABEL = 1         # index of the first labelled white key (A)
SOLFEO_RANGE = (3, 10)  # white-key indices of the Do..Do octave, inclusive

SOLFEO = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La",
          "B": "Si"}
# A black key sits after these white keys (no black key after B or E).
HAS_SHARP_AFTER = {"C", "D", "F", "G", "A"}
NEXT = {"C": "D", "D": "E", "F": "G", "G": "A", "A": "B"}

ORDER = "CDEFGAB"

# Solfège outside the Do..Do octave: present but greyed out.
GHOST_TEXT = "#c4bcac"
GHOST_PILL = "#f1ece1"
GHOST_EDGE = "#c4bcac"

SHARP, FLAT = "♯", "♭"

# Canvas geometry (pixels, y up).
MARGIN_X = 150
KEY_TOP = 1930
KEY_BOTTOM = 210
BLACK_W_FRAC = 0.58     # of a white key's width
BLACK_LEN_FRAC = 0.63   # of a white key's length
PAD_KEYS = 1            # extra empty space each side, in white-key widths
GAP_PX = 12             # between white keys, on screen

# One pastel per note, from the "vivo" political palette (a gentle rainbow
# from Do).
NOTE_COLORS = {
    "C": "#dd8288", "D": "#f2b263", "E": "#f0d06b", "F": "#a8cf74",
    "G": "#79c6b2", "A": "#8fbfe8", "B": "#c3a3dd",
}

THEMES = {
    "clasico": dict(
        background=style.PANEL_FILL, white="#fbf8f0", white_edge="#8d877c",
        black="#1d1c1a", case="#2b211b", felt="#9b2f2f",
        pill=style.CCAA_COLORS_VIVO["09"], pill_text="#26241f",
        black_text="#ffffff", black_solfeo="#f0c95f"),
    "esquema": dict(
        background=style.OCEAN, white="#ffffff", white_edge=style.BORDER_DARK,
        black="#3a3732", case=None, felt=None,
        pill="#f2b263", pill_text="#26241f",
        black_text="#ffffff", black_solfeo="#f0c95f"),
    "colores": dict(
        background=style.PANEL_FILL, white=None, white_edge=style.BORDER_DARK,
        black="#2f2c28", case=None, felt=None,
        pill="#ffffff", pill_text="#26241f",
        black_text="#ffffff", black_solfeo="#f0c95f"),
}


# The ♯/♭ fallback has no 800 weight; matplotlib would warn on every glyph.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def _font(weight):
    """Inter, falling back to matplotlib's bundled DejaVu for ♯ and ♭."""
    fp = style.font(weight)
    fp.set_family(["Inter", "DejaVu Sans"])
    return fp


def _text(ax, x, y, s, size, weight, color, halo=None, halo_width=0,
          zorder=10, scale=1.0, rotation=0, linespacing=1.2,
          multialignment="center"):
    from matplotlib import patheffects as pe

    effects = ([pe.withStroke(linewidth=halo_width * scale, foreground=halo)]
               if halo else [])
    ax.text(x, y, s, fontproperties=_font(weight), fontsize=size * scale,
            color=color, ha="center", va="center", zorder=zorder,
            rotation=rotation, linespacing=linespacing,
            multialignment=multialignment,
            path_effects=effects)


def _key_patch(x, y, w, h, radius, **kw):
    return FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={radius}", **kw)


def _gradient(ax, box, top, bottom, clip, zorder):
    """Vertical colour gradient filling `box`, clipped to a key patch."""
    x0, y0, x1, y1 = box
    t = np.linspace(0, 1, 256)[:, None, None]
    a = np.array(style_rgb(bottom))[None, None, :]
    b = np.array(style_rgb(top))[None, None, :]
    img = a + (b - a) * t
    im = ax.imshow(img, extent=(x0, x1, y0, y1), origin="lower",
                   aspect="auto", zorder=zorder, interpolation="bilinear")
    im.set_clip_path(clip)


def style_rgb(hex_color):
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _render(theme_name, footer, big="letras", name=None):
    """`big` picks which white-key name is the large, unboxed one: "letras"
    (A B C, solfège in pills) or "solfeo" (Do Re Mi, letters in pills)."""
    t = THEMES[theme_name]
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
    ax.set_facecolor(t["background"])
    fig.patch.set_facecolor(t["background"])

    klen = KEY_TOP - KEY_BOTTOM
    bw, blen = kw * BLACK_W_FRAC, klen * BLACK_LEN_FRAC
    x0 = MARGIN_X
    gap = GAP_PX / scale  # without it the keys read as one slab

    # Case: a dark lid above the keys with a strip of red felt.
    if t["case"]:
        ax.add_patch(_key_patch(x0 - 60, KEY_TOP - 40, n * kw + 120, 230, 30,
                                facecolor=t["case"], edgecolor="none",
                                zorder=16))
        ax.add_patch(Rectangle((x0 - 60, KEY_BOTTOM - 40), 60, klen + 40,
                               facecolor=t["case"], zorder=1))
        ax.add_patch(Rectangle((x0 + n * kw, KEY_BOTTOM - 40), 60, klen + 40,
                               facecolor=t["case"], zorder=1))
        ax.add_patch(_key_patch(x0 - 60, KEY_BOTTOM - 60, n * kw + 120, 60,
                                20, facecolor=t["case"], edgecolor="none",
                                zorder=1))
        # Dark bed behind the keys, so the gaps between them show.
        ax.add_patch(Rectangle((x0, KEY_BOTTOM), n * kw, klen,
                               facecolor=t["case"], zorder=1))
        ax.add_patch(Rectangle((x0, KEY_TOP - 4), n * kw, 22,
                               facecolor=t["felt"], zorder=17))
    else:
        # A plain rail so the keys hang from something.
        ax.add_patch(_key_patch(x0 - 20, KEY_TOP - 10, n * kw + 40, 110, 18,
                                facecolor=style.BORDER_DARK,
                                edgecolor="none", zorder=16))

    # White keys.
    for i, note in enumerate(WHITE):
        x = x0 + i * kw
        fill = t["white"] or NOTE_COLORS[note]
        patch = _key_patch(x + gap / 2, KEY_BOTTOM, kw - gap, klen + 60, 22,
                           facecolor=fill, edgecolor=t["white_edge"],
                           linewidth=(3 if theme_name != "clasico" else 1.5)
                           * scale,
                           zorder=2)
        ax.add_patch(patch)
        if theme_name == "clasico":
            _gradient(ax, (x, KEY_BOTTOM, x + kw, KEY_TOP + 60),
                      "#e9e3d4", "#fffdf7", patch, zorder=3)
            # Front lip: a slightly darker band at the near end.
            lip = _key_patch(x + gap / 2, KEY_BOTTOM, kw - gap, 46, 22,
                             facecolor="#e2dccd", edgecolor="none", zorder=4)
            ax.add_patch(lip)

        cx = x + kw / 2
        letter = note if i >= FIRST_LABEL else None
        # Outside the Do..Do octave the solfège is still shown, greyed out,
        # so the names visibly carry on past both ends.
        solfeo = SOLFEO[note]
        ghost = not SOLFEO_RANGE[0] <= i <= SOLFEO_RANGE[1]
        large, boxed = (letter, solfeo) if big == "letras" else (solfeo, letter)
        large_ghost = ghost and big == "solfeo"
        boxed_ghost = ghost and big == "letras"
        if large:
            # "Sol" is the widest name; 98 pt keeps it clear of the key edges.
            size = 140 if big == "letras" else 98
            halo = "#ffffff" if theme_name == "colores" else None
            _text(ax, cx, KEY_BOTTOM + 190, large, size, "extrabold",
                  GHOST_TEXT if large_ghost else style.LABEL_COLOR,
                  halo=halo, halo_width=14, scale=scale)
        if boxed:
            py = KEY_BOTTOM + 445
            pill_w, pill_h = kw - 44, 150
            ax.add_patch(_key_patch(
                cx - pill_w / 2, py - pill_h / 2, pill_w, pill_h, 70,
                facecolor=GHOST_PILL if boxed_ghost else t["pill"],
                edgecolor=GHOST_EDGE if boxed_ghost else style.BORDER_DARK,
                linewidth=2.5 * scale, zorder=8))
            _text(ax, cx, py - 4, boxed, 76, "extrabold",
                  GHOST_TEXT if boxed_ghost else t["pill_text"], zorder=9,
                  scale=scale)

    # Black keys, on the boundary after each C, D, F, G, A. That includes
    # both outer edges: without the half key cut off there, the first G
    # would read as an F and the last D as a B.
    xend = x0 + n * kw
    keyboard = Rectangle((x0, KEY_BOTTOM - 100), n * kw, klen + 400,
                         transform=ax.transData)
    before_first = ORDER[(ORDER.index(WHITE[0]) - 1) % 7]
    for i, note in enumerate([before_first] + WHITE):
        if note not in HAS_SHARP_AFTER:
            continue
        bx = x0 + i * kw - bw / 2
        by = KEY_TOP - blen
        patch = _key_patch(bx, by, bw, blen + 60, 16, facecolor=t["black"],
                           edgecolor="#141311", linewidth=2 * scale,
                           zorder=12)
        ax.add_patch(patch)
        patch.set_clip_path(keyboard)
        if theme_name == "clasico":
            _gradient(ax, (max(bx, x0), by, min(bx + bw, xend), KEY_TOP),
                      "#3b3936", "#151413", patch, zorder=13)
            bevel = _key_patch(bx + 14, by + 16, bw - 28, 70, 12,
                               facecolor="#4a4743", edgecolor="none",
                               zorder=14)
            ax.add_patch(bevel)
            bevel.set_clip_path(keyboard)
        if i in (0, n):
            continue  # the cut-off edge keys stay unnamed

        cx = bx + bw / 2
        upper = NEXT[note]
        i -= 1  # index of the white key to the left, as below
        if i + 1 > FIRST_LABEL:
            _text(ax, cx, by + 250, f"{note}{SHARP}", 50, "extrabold",
                  t["black_text"], zorder=15, scale=scale)
            _text(ax, cx, by + 165, f"{upper}{FLAT}", 50, "extrabold",
                  t["black_text"], zorder=15, scale=scale)
        if SOLFEO_RANGE[0] <= i < SOLFEO_RANGE[1]:
            # Spelled out: "sostenido"/"bemol" are what you say aloud, and
            # ♯/♭ give no hint of that. Too long to sit across a black key,
            # so they run up it, at the same size as the letter names.
            _text(ax, cx, (by + 330 + KEY_TOP - 30) / 2,
                  f"{SOLFEO[note]} sostenido\n{SOLFEO[upper]} bemol", 50,
                  "extrabold", t["black_solfeo"], zorder=15, scale=scale,
                  rotation=90, linespacing=1.05, multialignment="left")

    draw.draw_footer(ax, frame, footer, side="right")
    return draw.save(fig, name or f"piano-{theme_name}")


FOOTER = "Notas del piano · en inglés (A B C) y en español (Do Re Mi)"


def render_piano_clasico():
    return _render("clasico", FOOTER)


def render_piano_clasico_solfeo():
    """Clásico with the emphasis swapped: Do Re Mi large, letters boxed."""
    return _render("clasico", FOOTER, big="solfeo",
                   name="piano-clasico-solfeo")


def render_piano_esquema():
    return _render("esquema", FOOTER)


def render_piano_colores():
    return _render("colores", FOOTER)
