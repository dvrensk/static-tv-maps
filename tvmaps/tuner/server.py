"""The tuner's HTTP server: stdlib only, one long-lived process.

Endpoints (JSON unless noted):
  GET  /                        the editor page
  GET  /assets/fonts/<file>     bundled Inter faces for the browser preview
  GET  /api/maps                tunable maps
  GET  /api/map/<name>          label bundle: frame, anchors, specs, schemas
  GET  /api/map/<name>/base.png map rendered without tunable labels (cached)
  POST /api/map/<name>/render   {overrides} -> PNG with the edits applied
  POST /api/save                {edits} -> patch source files, return diffs

Matplotlib (Agg) is not thread-safe, so a lock serializes renders; the
figure size is 40x22.5 in, so PREVIEW_DPI 40 yields 1600x900 previews.
"""

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import hooks, style
from . import registry, writeback

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
PREVIEW_DPI = 40

_render_lock = threading.Lock()
_base_cache = {}  # map name -> dict(png=..., bundle=...)

VA_VALUES = {"top", "center", "bottom", "baseline", "center_baseline"}
HA_VALUES = {"left", "center", "right"}


def _render(map_name, overrides=None, suppress=False, capture=False,
            dpi=PREVIEW_DPI):
    import matplotlib.pyplot as plt

    fn, kwargs = registry.map_fn(map_name)
    with _render_lock:
        hooks.OVERRIDES = overrides or {}
        hooks.SUPPRESS = suppress
        hooks.CAPTURE = [] if capture else None
        try:
            fig = fn(**kwargs)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=dpi,
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            captured = hooks.CAPTURE
        finally:
            hooks.OVERRIDES = {}
            hooks.SUPPRESS = False
            hooks.CAPTURE = None
    return buf.getvalue(), captured


def _add_lonlat_jacobians(map_name, entries):
    """For absolute (lon/lat + rotation) labels: a local linear map between
    metres in the map CRS and degrees, so the browser can drag in pixels and
    produce lon/lat without a projection library."""
    absolute = [e for e in entries
                if registry.TABLES[e["table"]].idiom == "absolute"]
    if not absolute:
        return
    import geopandas as gpd
    from shapely.geometry import Point

    EPS = 0.01  # degrees
    pts = []
    for e in absolute:
        lon, lat = e["fields"]["lon"], e["fields"]["lat"]
        pts += [Point(lon, lat), Point(lon + EPS, lat), Point(lon, lat + EPS)]
    proj = gpd.GeoSeries(pts, crs="EPSG:4326").to_crs(registry.map_crs(map_name))
    for i, e in enumerate(absolute):
        p0, px, py = proj[3 * i], proj[3 * i + 1], proj[3 * i + 2]
        m = [[(px.x - p0.x) / EPS, (py.x - p0.x) / EPS],
             [(px.y - p0.y) / EPS, (py.y - p0.y) / EPS]]  # metres per degree
        det = m[0][0] * m[1][1] - m[0][1] * m[1][0]
        e["extra"]["m_per_deg"] = m
        e["extra"]["deg_per_m"] = [
            [m[1][1] / det, -m[0][1] / det],
            [-m[1][0] / det, m[0][0] / det],
        ]


def _bundle(map_name):
    cached = _base_cache.get(map_name)
    if cached is None:
        png, captured = _render(map_name, suppress=True, capture=True)
        m = registry.MAPS[map_name]
        seen = set()
        entries = []
        for rec in captured:
            handle = (rec["table"], rec["key"])
            if handle in seen:
                continue
            seen.add(handle)
            display = registry.display_name(rec["table"], rec["key"])
            if display == rec["key"] and rec["text"]:
                display = rec["text"].split("\n")[0]
            pos = registry.TABLES[rec["table"]].pos_field
            if pos and rec["fields"]:
                lon, lat = rec["fields"].pop(pos)
                rec["fields"].update(lon=lon, lat=lat)
            entries.append(dict(
                table=rec["table"], key=rec["key"], text=rec["text"],
                display=display,
                anchor=rec["anchor"], fields=rec["fields"],
                extra=rec["extra"],
                auto=rec["key"] not in registry.entries(rec["table"]),
            ))
        _add_lonlat_jacobians(map_name, entries)
        frame = registry.map_frame(map_name)
        bundle = dict(
            name=map_name, title=m.title, group=m.group,
            frame=list(frame),
            width_px=style.WIDTH_PX, height_px=style.HEIGHT_PX,
            entries=entries,
            schemas={t: registry.schema(t) for t in m.tables},
            theme=style.THEME,
        )
        cached = _base_cache[map_name] = dict(png=png, bundle=bundle)
    return cached


def _validate_overrides(raw):
    """{table: {key: {field: value}}} with only known editable fields."""
    if not isinstance(raw, dict):
        raise ValueError("overrides must be an object")
    out = {}
    for table_id, keys in raw.items():
        if table_id not in registry.TABLES:
            raise ValueError(f"unknown table {table_id!r}")
        editable = set(registry.editable_fields(table_id))
        if registry.TABLES[table_id].pos_field:
            editable |= {"lon", "lat"}
        defaults = registry.field_defaults(table_id)
        for key, fields in keys.items():
            clean = {}
            for field, value in fields.items():
                if field not in editable:
                    raise ValueError(f"field {field!r} not editable")
                if field in ("ha", "va", "group"):
                    allowed = (HA_VALUES if field == "ha"
                               else VA_VALUES if field == "va" else {"A", "B"})
                    if value not in allowed:
                        raise ValueError(f"bad {field}: {value!r}")
                elif value is None:
                    # Only the callout pair (and size where the tier decides)
                    # may be unset.
                    if field not in ("tx", "ty") and not (
                            field == "size" and defaults[field] is None):
                        raise ValueError(f"{field} cannot be None")
                else:
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        raise ValueError(f"bad {field}: {value!r}")
                    if field == "size" and not 6 <= value <= 200:
                        raise ValueError(f"size out of range: {value!r}")
                    if field != "size" and abs(value) > 5000:
                        raise ValueError(f"{field} out of range: {value!r}")
                clean[field] = value
            out.setdefault(table_id, {})[str(key)] = clean
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter than the default
        print(f"  {self.address_string()} {fmt % args}")

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _error(self, code, message):
        self._json(dict(error=message), code=code)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/":
                body = (STATIC / "index.html").read_bytes()
                self._send(200, body, "text/html; charset=utf-8")
            elif path.startswith("/assets/fonts/"):
                name = Path(path).name
                f = ROOT / "assets" / "fonts" / name
                if f.suffix == ".ttf" and f.is_file():
                    self._send(200, f.read_bytes(), "font/ttf")
                else:
                    self._error(404, "no such font")
            elif path == "/api/maps":
                self._json(dict(maps=[
                    dict(name=m.name, title=m.title, group=m.group)
                    for m in registry.MAPS.values()
                ], theme=style.THEME))
            elif path.startswith("/api/map/"):
                rest = path[len("/api/map/"):]
                if rest.endswith("/base.png"):
                    name = rest[:-len("/base.png")]
                    if name not in registry.MAPS:
                        return self._error(404, f"unknown map {name!r}")
                    self._send(200, _bundle(name)["png"], "image/png")
                else:
                    if rest not in registry.MAPS:
                        return self._error(404, f"unknown map {rest!r}")
                    self._json(_bundle(rest)["bundle"])
            else:
                self._error(404, "not found")
        except BrokenPipeError:
            pass
        except Exception as e:  # surface errors to the UI, don't kill the thread
            self._error(500, f"{type(e).__name__}: {e}")

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path.startswith("/api/map/") and path.endswith("/render"):
                name = path[len("/api/map/"):-len("/render")]
                if name not in registry.MAPS:
                    return self._error(404, f"unknown map {name!r}")
                body = self._read_json()
                overrides = _validate_overrides(body.get("overrides", {}))
                overrides = {
                    t: {k: registry.to_spec_fields(t, k, f)
                        for k, f in keys.items()}
                    for t, keys in overrides.items()
                }
                png, _ = _render(name, overrides=overrides)
                self._send(200, png, "image/png")
            elif path == "/api/save":
                body = self._read_json()
                edits = body.get("edits", {})
                # Validate every entry's final field values first.
                _validate_overrides({t: {k: e.get("fields", {})
                                         for k, e in keys.items()}
                                     for t, keys in edits.items()})
                with _render_lock:
                    files = writeback.apply_edits(edits)
                _base_cache.clear()  # NUM/group defaults may have shifted
                self._json(dict(files=files))
            else:
                self._error(404, "not found")
        except BrokenPipeError:
            pass
        except ValueError as e:
            self._error(400, str(e))
        except Exception as e:
            self._error(500, f"{type(e).__name__}: {e}")


def serve(host="127.0.0.1", port=8321):
    server = ThreadingHTTPServer((host, port), Handler)
    shown = "localhost" if host == "127.0.0.1" else host
    print(f"El ajustador: http://{shown}:{port}/  (Ctrl+C para salir)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nHasta luego.")
