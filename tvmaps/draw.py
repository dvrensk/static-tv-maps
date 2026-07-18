"""Drawing primitives on the 4000x2250 canvas."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from . import style

OUTPUT = Path(__file__).resolve().parent.parent / "output"


def new_map(frame):
    """Full-bleed 16:9 canvas covering `frame` in data coordinates."""
    fig = plt.figure(
        figsize=(style.WIDTH_PX / style.DPI, style.HEIGHT_PX / style.DPI),
        dpi=style.DPI,
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(frame[0], frame[2])
    ax.set_ylim(frame[1], frame[3])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor(style.OCEAN)
    fig.patch.set_facecolor(style.OCEAN)
    return fig, ax


def draw_layer(ax, gdf, facecolor, edgecolor, linewidth, zorder=2):
    gdf.plot(ax=ax, facecolor=facecolor, edgecolor=edgecolor,
             linewidth=linewidth, zorder=zorder)


def draw_context(ax, countries, zorder=1):
    countries.plot(ax=ax, facecolor=style.NEIGHBOR_FILL,
                   edgecolor=style.NEIGHBOR_EDGE, linewidth=1.2, zorder=zorder)


def halo_text(ax, x, y, text, size, weight="semibold", color=style.LABEL_COLOR,
              halo=style.HALO, halo_width=None, ha="center", va="center",
              zorder=10, linespacing=0.95):
    if halo_width is None:
        halo_width = max(2.5, size / 9)
    return ax.text(
        x, y, text, fontproperties=style.font(weight), fontsize=size,
        color=color, ha=ha, va=va, zorder=zorder, linespacing=linespacing,
        path_effects=[pe.withStroke(linewidth=halo_width, foreground=halo)],
    )


def callout(ax, anchor, text_xy, text, size, weight="semibold",
            color=style.LABEL_COLOR, line_color="#55524d", ha="center",
            va="center", zorder=11):
    """A label placed away from its feature, with a leader line pointing in."""
    ax.annotate(
        "", xy=anchor, xytext=text_xy, zorder=zorder - 1,
        arrowprops=dict(arrowstyle="-", color=line_color, linewidth=2.2,
                        shrinkA=8, shrinkB=2),
    )
    return halo_text(ax, text_xy[0], text_xy[1], text, size, weight=weight,
                     color=color, ha=ha, va=va, zorder=zorder)


def draw_title(ax, frame, title, subtitle=None):
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    halo_text(ax, fx0 + 0.5 * fw, fy1 - 0.045 * fh, title, 92,
              weight="extrabold", color=style.TITLE_COLOR, halo_width=16,
              va="top", zorder=20)
    if subtitle:
        # Bottom-right corner, above the attribution line, where there is sea.
        halo_text(ax, fx1 - 0.008 * fw, fy0 + 0.042 * fh, subtitle, 36,
                  weight="semibold", color="#55524d", halo_width=7,
                  ha="right", va="bottom", zorder=20)


def draw_attribution(ax, frame, text="Datos: IGN España · Natural Earth"):
    fx0, fy0, fx1, fy1 = frame
    halo_text(ax, fx1 - 0.008 * (fx1 - fx0), fy0 + 0.012 * (fy1 - fy0), text,
              20, weight="regular", color="#8a8880", halo_width=4,
              ha="right", va="bottom", zorder=20)


def draw_footer(ax, frame, text):
    """Small caption in the lower-right corner saying what the map shows."""
    fx0, fy0, fx1, fy1 = frame
    halo_text(ax, fx1 - 0.008 * (fx1 - fx0), fy0 + 0.038 * (fy1 - fy0), text,
              30, weight="semibold", color="#5d5a54", halo_width=6,
              ha="right", va="bottom", zorder=20)


def draw_inset_box(ax, box, label=None, zorder=3):
    """Rounded rectangle that hosts the Canary Islands inset."""
    x0, y0, x1, y1 = box
    r = 0.03 * (x1 - x0)
    patch = FancyBboxPatch(
        (x0, y0), x1 - x0, y1 - y0,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=style.OCEAN, edgecolor=style.BORDER_DARK, linewidth=2.5,
        zorder=zorder,
    )
    ax.add_patch(patch)
    if label:
        halo_text(ax, x0 + 0.5 * (x1 - x0), y1 - 0.02 * (y1 - y0), label, 40,
                  weight="extrabold", color="#55524d", ha="center", va="top",
                  zorder=zorder + 7)
    return patch


def city_dot(ax, xy, size=13, face="#3a3733", edge="#ffffff", zorder=8):
    ax.plot(xy[0], xy[1], "o", ms=size, mfc=face, mec=edge, mew=2.2, zorder=zorder)


def city_star(ax, xy, size=26, face="#f2c53d", edge="#4d4a45", zorder=8):
    ax.plot(xy[0], xy[1], "*", ms=size, mfc=face, mec=edge, mew=2.0, zorder=zorder)


def _name_width_data(ax, text, size, weight):
    """Width of a text string in data units (axes are aspect-equal)."""
    fig = ax.figure
    x0, x1 = ax.get_xlim()
    data_per_px = (x1 - x0) / style.WIDTH_PX
    renderer = fig.canvas.get_renderer()
    tmp = ax.text(x0, ax.get_ylim()[0], text, fontproperties=style.font(weight),
                  fontsize=size)
    w = tmp.get_window_extent(renderer).width
    tmp.remove()
    return w * data_per_px, data_per_px


def numbered_label(ax, xy, number, text, size, ha="center", va="center",
                   badge_face="#b23a2e", name_color=style.LABEL_COLOR,
                   weight="extrabold", zorder=10):
    """A rank badge (filled circle with the number) followed by the name.

    The badge is a fixed size regardless of digit count, so it reads like a
    ranking medallion for numbers 1–99. `xy` is anchored per `ha`/`va` exactly
    like halo_text, treating the badge+name as one group."""
    from matplotlib.patches import Circle

    name_w, data_per_px = _name_width_data(ax, text.replace("\n", " "), size,
                                           weight)
    r = 0.9 * size * (style.DPI / 72) * data_per_px   # badge radius, data units
    gap = 0.9 * r
    group_w = 2 * r + gap + name_w
    x, y = xy
    left = x if ha == "left" else x - group_w if ha == "right" else x - group_w / 2
    cy = y + r if va == "bottom" else y - r if va == "top" else y
    bcx = left + r

    ax.add_patch(Circle((bcx, cy), r, facecolor=badge_face, edgecolor="#ffffff",
                        linewidth=2.2, zorder=zorder))
    ax.text(bcx, cy, str(number), fontproperties=style.font(weight),
            fontsize=size * 0.72, color="#ffffff", ha="center", va="center",
            zorder=zorder + 1)
    return halo_text(ax, bcx + r + gap, cy, text, size, weight=weight,
                     color=name_color, ha="left", va="center", zorder=zorder)


def numbered_callout(ax, anchor, text_xy, number, text, size, ha="center",
                     va="center", badge_face="#b23a2e", line_color="#55524d",
                     zorder=11):
    """numbered_label placed away from its point, with a leader line."""
    ax.annotate("", xy=anchor, xytext=text_xy, zorder=zorder - 1,
                arrowprops=dict(arrowstyle="-", color=line_color, linewidth=2.2,
                                shrinkA=8, shrinkB=2))
    return numbered_label(ax, text_xy, number, text, size, ha=ha, va=va,
                          badge_face=badge_face, zorder=zorder)


def legend_column(ax, frame, x_frac, y_top_frac, rows, size=26,
                  color=style.LABEL_COLOR, leading=1.5, num_gap_frac=0.0045):
    """A numbered legend column.

    `rows` is a list of (number, text) tuples; numbers are right-aligned at
    x_frac, texts left-aligned just after. Returns the bottom y fraction."""
    fx0, fy0, fx1, fy1 = frame
    fw, fh = fx1 - fx0, fy1 - fy0
    row_frac = (size * style.DPI / 72 * leading) / style.HEIGHT_PX
    x_num = fx0 + x_frac * fw
    x_text = fx0 + (x_frac + num_gap_frac) * fw
    y = y_top_frac
    for num, text in rows:
        yy = fy0 + y * fh
        if num is not None:
            halo_text(ax, x_num, yy, str(num), size, weight="extrabold",
                      color=color, ha="right", va="top", zorder=20)
        halo_text(ax, x_text, yy, text, size, weight="semibold",
                  color=color, ha="left", va="top", zorder=20)
        y -= row_frac
    return y


# When True (see generate.py --jpg), each map is also written as JPEG —
# handy for TVs that only accept JPEG from USB sticks or DLNA servers.
SAVE_JPG = False


def save(fig, name: str) -> Path:
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"{name}{style.THEME_SUFFIX}.png"
    fig.savefig(path, dpi=style.DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    if SAVE_JPG:
        from PIL import Image

        Image.open(path).convert("RGB").save(
            path.with_suffix(".jpg"), quality=92, optimize=True)
    return path
