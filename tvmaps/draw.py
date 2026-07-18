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


# When True (see generate.py --jpg), each map is also written as JPEG —
# handy for TVs that only accept JPEG from USB sticks or DLNA servers.
SAVE_JPG = False


def save(fig, name: str) -> Path:
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"{name}.png"
    fig.savefig(path, dpi=style.DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    if SAVE_JPG:
        from PIL import Image

        Image.open(path).convert("RGB").save(
            path.with_suffix(".jpg"), quality=92, optimize=True)
    return path
