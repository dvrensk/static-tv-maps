# El ajustador — architecture and maintenance notes

How the interactive label tuner works, the invariants that keep it safe, and
the recipes for extending it. README.md covers *using* it; this covers
*changing* it. Written so a fresh session (human or Claude) can pick up any
tuner task without re-deriving the design.

## Big picture

The old iteration loop (edit numbers → `generate.py` → open PNG) cost 10–15 s
per attempt, almost all of it fixed overhead: cold geopandas/matplotlib
imports (~2–4 s), scene rebuild (~1 s), full-res 4000×2250 PNG encode
(~2–4 s). Label drawing itself is milliseconds and label placement is pure
arithmetic on cacheable anchors, so the tuner splits the work:

- a **long-lived server** (`tune.py` → `tvmaps/tuner/server.py`, stdlib HTTP)
  renders each map once **without** tunable labels and serves it as a base
  image, plus a JSON bundle of every label's anchor and current spec;
- the **browser** (`tvmaps/tuner/static/index.html`, one file, no build)
  draws the labels as an SVG overlay and edits them live — drags and
  keyboard nudges are unit-converted client-side;
- **`r`** asks the warm server for a true matplotlib render with the edits
  applied (~1 s at preview resolution, dpi 40 → 1600×900);
- **save** patches the `maps_*.py` tables in place via libcst and mutates the
  in-memory tables so the warm process stays consistent — no reload.

`generate.py` remains the only producer of final PNGs and must never need
the tuner or the network.

## The hooks seam (`tvmaps/hooks.py`)

Three globals, all no-ops during `generate.py` runs:

- `SUPPRESS` — when True, tunable labels are skipped (base-image renders).
  Fixed ink (footers, legends, city dots, zone blobs, river lines) still
  draws: **the dot/geometry always renders; only the text is tunable.**
- `OVERRIDES` — `{table_id: {key: {field: value}}}` merged over specs at
  render time (live preview and ground-truth renders).
- `CAPTURE` — when a list, every tunable label appends its record.

Every consumer follows the same shape, in this order:

```python
spec = hooks.spec_for(TABLE_ID, key, spec)      # 1. merge overrides
# (split maps: group filter goes here, on the MERGED spec)
hooks.capture(TABLE_ID, key, text, (x, y), spec, **extra)   # 2. record
if hooks.SUPPRESS:                               # 3. gate the ink
    continue  # but draw the dot first if the map has one
... draw ...
```

`capture` records the **raw anchor** (pre-dx/dy) and the merged spec.
`extra` kwargs in use: `tier_size` (population-tier fallback size),
`rank` (ciudades badges), `icon` (iconos glyph), `color`/`halo` (river and
zone label styling for the preview), `leader` (block idiom).

## The registry (`tvmaps/tuner/registry.py`)

`TABLES` describes every editable table; `MAPS` maps each `generate.py` map
name to its Figure-returning `map_*` function, its tables, and its scene.

`Table` fields that matter:

| field | meaning |
| --- | --- |
| `id` | unique tuner id == the `table_id` string passed to hooks |
| `var` | source variable name when it differs from `id` (the two `ICONS` tables) |
| `container` | `dict` \| `list` (keyed by `key_field`) \| `tuple2` (`{k: (data, spec)}`, HAND_RIVERS) \| `single` (bare assignment, CANARY_FIRM) |
| `idiom` | `offset` (km dx/dy + optional tx/ty callout) \| `block` (tx/ty text block, fixed leader: moda/marcas/logos) \| `absolute` (lon/lat + rotation: rivers, ranges, zones) |
| `pos_field` | absolute idiom with the position stored as a `(lon, lat)` tuple field (`Zone.label`, `WineDO.label`); the tuner exposes virtual `lon`/`lat` and `registry.to_spec_fields` folds them back |
| `size_field` | which field the size stepper edits; `None` → size comes from a tier/constant |
| `exclude` | per-table non-editable fields, on top of `NON_EDITABLE` |
| `key_field` | list containers: the spec field holding the entry key (never editable) |

Other invariants: `NON_EDITABLE` holds display/identity fields (`text`,
`wrap`, `icon`, `cat`, `brands`, `lonlat`, …); `KEEP_EXPLICIT = {"group"}`
in writeback because every PROV_LABELS entry names its group even at the
default. `Map.scene` provides the frame; `Map.crs` feeds the lon/lat math
(Central America uses its own LCC strings from `geo`).

## Server notes (`tvmaps/tuner/server.py`)

- Endpoints: `/api/maps`, `/api/map/<name>` (bundle), `…/base.png` (cached
  per map until a save clears the cache), `POST …/render` (overrides →
  PNG), `POST /api/save` (edits → diffs). Static: `/` and `/assets/fonts/*`.
- Matplotlib is not thread-safe → one render lock; hooks globals are set and
  restored inside it.
- **Jacobian trick**: for absolute labels the server computes, per entry, a
  local 2×2 linear map between metres in the map CRS and degrees
  (`m_per_deg` / `deg_per_m`, finite differences at ±0.01°). The browser
  converts pixel drags to lon/lat with plain arithmetic — no projection
  library client-side. Accurate to <0.1 % over label-nudging distances.
- Validation is field-level (editable set, ha/va/group enums, numeric
  ranges); `pos_field` tables accept virtual `lon`/`lat`.
- **Restart the server after changing tier tables, palette, or any code the
  base render bakes in** — the base cache and module state are warm.

## Write-back guarantees (`tvmaps/tuner/writeback.py`)

The invariant the test suite enforces: **saving current values back — every
entry, every table, all fields marked changed — writes nothing.** Files are
sacred; the tuner may only touch what the user actually changed.

How that is achieved:

- Only fields listed in `changed` are processed; a field whose current
  source literal already equals the new value is skipped entirely
  (`_arg_equals`), preserving author spellings like `43.220` and `-5.0`
  and explicitly-written defaults like `ha="center"`.
- Positional args are mapped to fields via dataclass order and rewritten
  **in place** — never removed (removal would shift later bindings, the
  `CitySpec(0, 14)` trap). Keyword args returning to their dataclass
  default are removed; new non-default fields are appended as kwargs —
  except the first dataclass field (size in the Label family), which is
  inserted positionally per file style.
- Trailing same-line comments are re-padded so their column survives a
  value changing length.
- Inserts (auto-generated specs the user edited: concejos, NUM provinces,
  logo chips) append a formatted line before the table's closing brace,
  with a `# display name` comment for code-keyed tables. Only `dict`
  containers can take inserts.
- Every new source is `compile()`-checked before writing; writes are
  tempfile + rename; after writing, the in-memory tables are updated via
  `registry.set_entry` (dataclasses.replace) so the warm server matches.

Tests live in `tests/test_tuner_writeback.py` (`make test`). They snapshot
and restore both files and in-memory tables. When the user retunes labels,
tests must not memorize literal values — assert diff *shape*, not content
(two tests broke this way once).

## Frontend notes (`tvmaps/tuner/static/index.html`)

Single file, vanilla JS + SVG in a 4000×2250 viewBox over the base `<img>`,
so font pt → px is just ×100/72 and the CSS pan/zoom transform covers both.

Things that must stay in sync with the Python side:

- `draw.numbered_label` geometry: badge radius `0.9·size·DPI/72`, gap
  **`0.45·r`** (annotated in draw.py), group anchored by **badge radius**
  (not text height) for va, name width measured on the single joined line.
- Halo: stroke width `max(2.5, size/9)·100/72`, `paint-order: stroke`.
- Callout leader: shrinkA 8 pt at the text end, shrinkB 2 pt at the anchor.
- Rotation: matplotlib rotates CCW, SVG (y-down) needs `rotate(-rot)`.

Behavioural decisions worth knowing before "fixing" them:

- Keyboard-first is a hard requirement: pointer only for the first pick.
  `Shift+N/P` cycles maps; arrow steps are **scale-aware** (~4 px at full
  res snapped to a round km value: Spain 2 km, Asturias 0.25 km).
- Pointer capture goes on the `#viewport`, not the SVG node — `redraw()`
  replaces nodes mid-gesture and a detached capture target eats the drag.
- The map `<select>` blurs itself after change (else it swallows keys), and
  `loadMap` always restores the editing view (overlay un-hidden) even when
  leaving a real-render view.
- ⌘S/Ctrl+S both save, also while an input has focus.
- `sizeOf()` falls back to `extra.tier_size` when `size_field` is unset or
  the field is None — the `TownLabel`/ciudades `CityLabel` "explicit size
  overrides the population tier" pattern.

## Adding a new tunable table (recipe)

1. Route the drawing loop through the hooks (pattern above). Dots/geometry
   stay outside the SUPPRESS gate; text goes behind it. Pass style hints
   (`color=`, `halo=`, `tier_size=`) via capture if the preview needs them.
2. If the map's render function is inlined into `render_*`, split out a
   `map_*` that returns the Figure.
3. Register a `Table` (unique id; set `var`, `container`, `key_field`,
   `idiom`, `pos_field`, `size_field`, `exclude` as needed) and add its id
   to the owning `Map`(s). New map names must match `generate.py` keys.
4. Verify: `make test` (the no-op invariant picks the table up
   automatically), pixel-parity before/after (stash-render-compare in the
   same environment — committed PNGs differ byte-wise across machines, see
   `make unchurn`), then drive the map once in the tuner.

Playwright drive in Claude's remote sandbox:
`p.chromium.launch(executable_path="/opt/pw-browsers/chromium")`, wait on
`state.map === '<name>' && state.entries.length` before sending keys
(`state`, `schemaOf`, `sizeOf` are reachable from `page.evaluate`).

## Known gaps (deliberate, as of 2026-08)

- **Gijón street maps**: three nested per-map config dicts (`MAPA_*`) with
  tuple values, `SLabel.rot=None` meaning "computed from the street", and
  `map_gijon(cfg)` saving instead of returning a Figure. Supporting them
  needs nested-table addressing, tuple→dataclass promotion and an
  auto-rotation tri-state — its own pass.
- Hand-coded Canary inset items (Malvasía de Lanzarote, the despensa
  Canary zone), `CANAL_LABEL`/`EXT_CANAL_LABEL`, the editoriales
  Madrid/Barcelona panels (lon/lat literals at the call site), context and
  water label tuple lists, and legends are not tunable.
- The mudo maps have nothing to tune by design.

## Design principles picked up along the way

- **City dots are factual.** They come from `data/processed/cities.geojson`
  (Nominatim city centres). Bilbao's dot sits ~10 km inland because Bilbao
  is ~10 km inland — never move a dot to "look right"; move the label.
- Base label sizes live in per-map tier tables (`TIERS` in maps_ciudades,
  `_town_tier` in maps_asturias); per-label explicit sizes override tiers.
- `asturias-ciudades` and `asturias-ciudades-concejos` share `TOWN_LABELS`:
  one edit fixes both maps.
- The comarcas map paints the Eo and the Navia (COMARCA_RIOS) clipped to
  the Eo-Navia comarca so the name explains itself; the upper Navia wanders
  through Galicia and would float disconnected on an Asturias-wide clip.
- Commits from Claude sessions are authored as the repo owner via the
  SessionStart hook in `.claude/settings.json`, with Claude credited as
  Co-Authored-By.
