"""Normalized label layer: overrides, and export of editable-label manifests.

Every hand-tuned label on a map flows through `emit()` as a `Spec`. In normal
rendering, emit applies any committed overrides (overrides/<map>.json) on top
of the Python literals and draws via the existing draw.* helpers with the
exact same arguments as before (pixel parity). In export mode
(`generate.py export <map>`), emit additionally measures each label, removes
it from the figure, and records a manifest entry, so that `draw.save`
produces editor/<map>/base.png (labels suppressed) plus labels.json with
every label in canvas-pixel coordinates. The external editor (tvOS app)
round-trips its edits through the overrides files; the Python literals stay
canonical.
"""

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import style

ROOT = Path(__file__).resolve().parent.parent
OVERRIDES_DIR = ROOT / "overrides"
EDITOR_DIR = ROOT / "editor"

KM = 1000.0
SCHEMA = 1

# Fields an override may set (per-Spec `editable` narrows this further).
OVERRIDABLE = ("dx", "dy", "tx", "ty", "size", "ha", "va", "rotation")
_NUMERIC = ("dx", "dy", "tx", "ty", "size", "rotation")
_HA = ("left", "center", "right")
_VA = ("top", "center", "bottom", "baseline", "center_baseline")


@dataclass
class Spec:
    """One label, normalized across all the per-module dataclass shapes."""

    id: str                      # "<kind>:<feature-key>", stable across renders
    kind: str                    # region|country|city|numbered|river|range|zone|...
    text: str                    # final display text (may contain \n)
    anchor: tuple                # data coords (post canary transform)
    dx: float = 0.0              # km; moves the anchor
    dy: float = 0.0
    tx: float | None = None     # km from the moved anchor; not None => callout
    ty: float | None = None
    size: float = 28.0           # points
    weight: str = "semibold"
    weight_callout: str | None = None  # weight when drawn as callout, if different
    color: str | None = None    # None => style.LABEL_COLOR
    halo: str | None = None     # None => style.HALO
    halo_width: float | None = None
    ha: str = "center"
    va: str = "center"
    rotation: float = 0.0
    linespacing: float = 0.95
    line_color: str = "#55524d"  # leader line
    zorder: float | None = None  # None => draw helper default
    badge: dict | None = None   # {"number": int, "face": "#..."} => numbered label
    marker: dict | None = None  # descriptive only; dots/stars stay baked
    in_inset: bool = False
    editable: tuple = ("dx", "dy", "tx", "ty", "size", "ha")


@dataclass
class Ctx:
    map_name: str                # registry key, without theme suffix
    mode: str = "render"         # "render" | "export"
    overrides: dict = field(default_factory=dict)   # label id -> {field: value}
    records: list = field(default_factory=list)     # editable manifest entries
    locked: list = field(default_factory=list)      # locked manifest entries
    warnings: list = field(default_factory=list)
    fig: object = None
    ax: object = None
    frame: tuple | None = None
    canary_box: tuple | None = None
    _seen_ids: set = field(default_factory=set)
    _lock_counts: dict = field(default_factory=dict)

    def warn(self, msg):
        self.warnings.append(f"{self.map_name}: {msg}")


CTX: Ctx | None = None


def begin(map_name: str, mode: str = "render", use_overrides: bool = True) -> Ctx:
    global CTX
    CTX = Ctx(map_name=map_name, mode=mode,
              overrides=load_overrides(map_name) if use_overrides else {})
    return CTX


def finish() -> Ctx | None:
    global CTX
    ctx, CTX = CTX, None
    if ctx is not None:
        for label_id in ctx.overrides:
            ctx.warn(f"override for unknown label id {label_id!r} "
                     "was never applied")
    return ctx


def current() -> Ctx | None:
    return CTX


def load_overrides(map_name: str) -> dict:
    path = OVERRIDES_DIR / f"{map_name}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError as e:
        print(f"warning: unreadable overrides file {path}: {e}")
        return {}
    labels = data.get("labels", {})
    return labels if isinstance(labels, dict) else {}


def on_new_map(fig, ax, frame):
    """Called by draw.new_map so emit/export know the canvas."""
    if CTX is not None:
        CTX.fig, CTX.ax, CTX.frame = fig, ax, frame


def on_inset_box(box):
    """Called by draw.draw_inset_box (Canary inset rectangle, data coords)."""
    if CTX is not None:
        CTX.canary_box = box


# ---------------------------------------------------------------------------
# Emitting labels
# ---------------------------------------------------------------------------

def _apply_override(spec: Spec, ov: dict):
    for key, value in ov.items():
        if key not in OVERRIDABLE or key not in spec.editable:
            CTX.warn(f"{spec.id}: field {key!r} is not editable; ignored")
            continue
        if key in _NUMERIC:
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            if key in ("tx", "ty"):
                ok = ok or value is None
        elif key == "ha":
            ok = value in _HA
        elif key == "va":
            ok = value in _VA
        else:
            ok = False
        if not ok:
            CTX.warn(f"{spec.id}: bad value for {key!r}: {value!r}; ignored")
            continue
        setattr(spec, key, value)


def emit(ax, spec: Spec):
    """Draw one label (with overrides applied); record it when exporting."""
    from . import draw  # late import to avoid a cycle

    if CTX is not None:
        ov = CTX.overrides.pop(spec.id, None)
        if ov:
            _apply_override(spec, ov)
        if spec.id in CTX._seen_ids:
            CTX.warn(f"duplicate label id {spec.id}")
        CTX._seen_ids.add(spec.id)

    is_callout = spec.tx is not None and spec.ty is not None
    x = spec.anchor[0] + spec.dx * KM
    y = spec.anchor[1] + spec.dy * KM
    color = spec.color if spec.color is not None else style.LABEL_COLOR
    halo = spec.halo if spec.halo is not None else style.HALO
    weight = spec.weight
    if is_callout and spec.weight_callout is not None:
        weight = spec.weight_callout

    exporting = CTX is not None and CTX.mode == "export"
    before = set(id(c) for c in ax.get_children()) if exporting else None

    if spec.badge is not None:
        if is_callout:
            t = draw.numbered_callout(
                ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM),
                spec.badge["number"], spec.text, spec.size,
                ha=spec.ha, va=spec.va, badge_face=spec.badge["face"],
                line_color=spec.line_color,
                **({"zorder": spec.zorder} if spec.zorder is not None else {}))
        else:
            t = draw.numbered_label(
                ax, (x, y), spec.badge["number"], spec.text, spec.size,
                ha=spec.ha, va=spec.va, badge_face=spec.badge["face"],
                weight=weight,
                **({"zorder": spec.zorder} if spec.zorder is not None else {}))
    elif is_callout:
        t = draw.callout(
            ax, (x, y), (x + spec.tx * KM, y + spec.ty * KM), spec.text,
            spec.size, weight=weight, color=color, line_color=spec.line_color,
            ha=spec.ha, va=spec.va,
            **({"zorder": spec.zorder} if spec.zorder is not None else {}))
    else:
        t = draw.halo_text(
            ax, x, y, spec.text, spec.size, weight=weight, color=color,
            halo=halo, halo_width=spec.halo_width, ha=spec.ha, va=spec.va,
            linespacing=spec.linespacing,
            **({"zorder": spec.zorder} if spec.zorder is not None else {}))
    if spec.rotation:
        t.set_rotation(spec.rotation)

    if exporting:
        new = [c for c in ax.get_children() if id(c) not in before]
        _record(ax, spec, weight, x, y, is_callout, new)
        for artist in new:
            artist.remove()
    return t


def record_locked(kind: str, text: str, artists):
    """Report text that stays baked into the base image (footers, legends...)."""
    if CTX is None or CTX.mode != "export":
        return
    n = CTX._lock_counts.get(kind, 0)
    CTX._lock_counts[kind] = n + 1
    suffix = f":{n}" if kind in ("legend", "swatch") else ""
    bbox = _union_bbox(CTX.ax, [a for a in artists if a is not None])
    CTX.locked.append({
        "id": f"locked:{kind}{suffix}",
        "kind": kind,
        "text": text,
        "bbox_px": bbox,
    })


# ---------------------------------------------------------------------------
# Pixel geometry
# ---------------------------------------------------------------------------

def _to_px(ax, x, y):
    """Data coords -> image pixels (origin top-left, y down)."""
    dx, dy = ax.transData.transform((x, y))
    return round(float(dx), 1), round(float(style.HEIGHT_PX - dy), 1)


def _union_bbox(ax, artists):
    renderer = ax.figure.canvas.get_renderer()
    boxes = []
    for a in artists:
        try:
            b = a.get_window_extent(renderer)
        except (TypeError, RuntimeError):
            continue
        if b.width > 0 or b.height > 0:
            boxes.append(b)
    if not boxes:
        return None
    x0 = min(b.x0 for b in boxes)
    x1 = max(b.x1 for b in boxes)
    y0 = min(b.y0 for b in boxes)
    y1 = max(b.y1 for b in boxes)
    return {"x0": round(x0, 1), "y0": round(style.HEIGHT_PX - y1, 1),
            "x1": round(x1, 1), "y1": round(style.HEIGHT_PX - y0, 1)}


def _in_inset(x, y):
    if CTX is None or CTX.canary_box is None:
        return False
    bx0, by0, bx1, by1 = CTX.canary_box
    return bool(bx0 <= x <= bx1 and by0 <= y <= by1)


def _record(ax, spec: Spec, weight, x, y, is_callout, artists):
    """Append a manifest entry for an emitted (and about to be removed) label."""
    if is_callout:
        tx_x, tx_y = x + spec.tx * KM, y + spec.ty * KM
    else:
        tx_x, tx_y = x, y
    axp, ayp = _to_px(ax, *spec.anchor)
    txp, typ = _to_px(ax, tx_x, tx_y)
    halo_width = spec.halo_width
    if halo_width is None:
        halo_width = max(2.5, spec.size / 9)

    entry = {
        "id": spec.id,
        "kind": spec.kind,
        "text": spec.text,
        "anchor_px": {"x": axp, "y": ayp},
        "offset_km": {"dx": spec.dx, "dy": spec.dy},
        "callout_km": ({"tx": spec.tx, "ty": spec.ty} if is_callout else None),
        "text_px": {"x": txp, "y": typ},
        "bbox_px": _union_bbox(ax, artists),
        "size_pt": spec.size,
        "weight": weight,
        "color": spec.color if spec.color is not None else style.LABEL_COLOR,
        "halo": {
            "color": spec.halo if spec.halo is not None else style.HALO,
            "width_pt": round(halo_width, 2),
        },
        "ha": spec.ha,
        "va": spec.va,
        "rotation": spec.rotation,
        "linespacing": spec.linespacing,
        "leader": ({
            "from_px": {"x": txp, "y": typ},
            "to_px": {"x": _to_px(ax, x, y)[0], "y": _to_px(ax, x, y)[1]},
            "color": spec.line_color,
            "width_pt": 2.2,
            "shrink_from_pt": 8,
            "shrink_to_pt": 2,
        } if is_callout else None),
        "badge": _badge_geometry(ax, spec, weight, tx_x, tx_y, artists),
        "marker": spec.marker,
        "in_canary_inset": _in_inset(tx_x, tx_y),
        "editable": list(spec.editable),
    }
    CTX.records.append(entry)


def _badge_geometry(ax, spec, weight, tx_x, tx_y, artists):
    """Measured badge geometry so the editor can draw the group verbatim."""
    if spec.badge is None:
        return None
    from matplotlib.patches import Circle

    circle = next((a for a in artists if isinstance(a, Circle)), None)
    out = {"number": spec.badge["number"], "face": spec.badge["face"],
           "number_color": "#ffffff",
           "number_size_pt": round(spec.size * 0.72, 2)}
    if circle is not None:
        cx, cy = circle.center
        cpx = _to_px(ax, cx, cy)
        edge = _to_px(ax, cx + circle.radius, cy)
        r_px = round(edge[0] - cpx[0], 1)
        out.update({"center_px": {"x": cpx[0], "y": cpx[1]},
                    "radius_px": r_px, "gap_px": round(0.9 * r_px, 1)})
    return out


# ---------------------------------------------------------------------------
# Export artifacts
# ---------------------------------------------------------------------------

def export_paths(map_name: str):
    d = EDITOR_DIR / map_name
    return d / "base.png", d / "labels.json"


def save_export(fig, name: str) -> Path:
    """Export-mode replacement for draw.save: base image + manifest."""
    import matplotlib.pyplot as plt

    ctx = CTX
    base_path, manifest_path = export_paths(name)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base_path, dpi=style.DPI, facecolor=fig.get_facecolor())
    plt.close(fig)

    frame = ctx.frame
    km_per_px = float(frame[2] - frame[0]) / style.WIDTH_PX / KM
    canary = None
    if ctx.canary_box is not None:
        m_per_px = (frame[2] - frame[0]) / style.WIDTH_PX
        bx0, by0, bx1, by1 = ctx.canary_box
        canary = {
            "x0": round(float(bx0 - frame[0]) / m_per_px, 1),
            "y0": round(float(frame[3] - by1) / m_per_px, 1),
            "x1": round(float(bx1 - frame[0]) / m_per_px, 1),
            "y1": round(float(frame[3] - by0) / m_per_px, 1),
        }
    manifest = {
        "schema": SCHEMA,
        "map": name,
        "canvas": {"width_px": style.WIDTH_PX, "height_px": style.HEIGHT_PX,
                   "dpi": style.DPI},
        "km_per_px": round(km_per_px, 6),
        "canary_inset_px": canary,
        "font": {"family": "Inter",
                 "weights": {"regular": 400, "semibold": 600, "extrabold": 800}},
        "labels": ctx.records,
        "locked": ctx.locked,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1)
                             + "\n")
    return base_path


def write_index(map_names):
    """Update editor/index.json with entries for the maps just exported."""
    EDITOR_DIR.mkdir(exist_ok=True)
    path = EDITOR_DIR / "index.json"
    existing = {}
    if path.exists():
        try:
            existing = {m["name"]: m
                        for m in json.loads(path.read_text()).get("maps", [])}
        except ValueError:
            pass
    for name in map_names:
        base, manifest = export_paths(name)
        if not (base.exists() and manifest.exists()):
            continue
        data = json.loads(manifest.read_text())
        existing[name] = {
            "name": name,
            "base": f"editor/{name}/base.png",
            "manifest": f"editor/{name}/labels.json",
            "output": f"output/{name}.png",
            "labels": len(data.get("labels", [])),
        }
    index = {"schema": SCHEMA,
             "maps": [existing[k] for k in sorted(existing)]}
    path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
