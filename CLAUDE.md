# CLAUDE.md

Guidance for working on this repository.

## What this project is

Machinery that renders **pedagogical maps of Spain and Asturias as static
4000×2250 px (16:9) PNGs** for a TV's standby slideshow. Hard requirements:

- Output exactly 4000×2250; the TV displays PNG or JPEG as-is.
- Text must be readable from ~5 m: prefer fewer, bigger labels. If names
  don't fit on one map, split them across two maps or use leader-line
  callouts — never shrink text below ~24 pt (33 px).
- The Canary Islands must appear on every Spain-wide map, transposed into a
  framed inset (currently lower-left, at true scale).

## Layout

- `generate.py` — CLI. `python generate.py all | <map-name> | --list [--jpg]`.
  Map names are derived from `render_*` functions in `tvmaps/maps_*.py`.
- `tvmaps/style.py` — canvas constants, palette (keyed by INE community
  code), display-name overrides, font loading (bundled Inter in
  `assets/fonts/`).
- `tvmaps/geo.py` — data loading, 16:9 frame computation, Canary inset
  placement, label anchor (pole of inaccessibility).
- `tvmaps/draw.py` — canvas, halo text, callouts, title/attribution, save.
- `tvmaps/maps_spain.py`, `tvmaps/maps_asturias.py`, `tvmaps/maps_capitals.py`,
  `tvmaps/maps_ciudades.py`, `tvmaps/maps_fisica.py`, `tvmaps/maps_rios.py`,
  `tvmaps/maps_productos.py` — the actual maps and all per-feature label
  tuning. New modules must be added to the registry tuple in `generate.py`.
- `tvmaps/cities.py` — city gazetteer access (`data/processed/cities.geojson`,
  geocoded via Nominatim by the download script) plus metadata: province and
  community capitals, INE 2025 big-city populations, Asturias towns over
  10 000 inhabitants, and the 8 functional comarcas with their concejos.
- `scripts/download_data.py` — fetches raw sources into `data/raw/`
  (gitignored) and writes simplified GeoJSON to `data/processed/`
  (committed). Rendering never needs the network.
- `output/` — rendered maps, committed.

## Working on maps

The iteration loop: render (`.venv/bin/python generate.py <map>`, ~1 s per
map), open the PNG, adjust, repeat. Label tuning is all data:

- `Label(size, dx, dy)` — nudge the in-region anchor; **offsets are in km**.
- `Label(size, tx, ty, ha=...)` — draw the name away from the feature with a
  leader line ending at (anchor + tx/ty km). Used for small features
  (Basque provinces, Ceuta/Melilla, small coastal concejos → sea above).
- Split maps: each province/concejo has a `group` ("A"/"B") deciding which of
  the two maps carries its name. Concejo groups are automatic (alternating
  area rank); provinces are hand-assigned in `PROV_LABELS`.

Conventions:

- ALL user-visible map text is in Spanish (standing instruction from the
  user), including footers, legends and neighbour-country labels.
- No big titles: maps identify themselves with a small footer caption
  (`draw.draw_footer`) so the geography gets every pixel. Anything that
  makes the peninsula smaller is a net negative.
- The Canary inset may cover Portugal or Morocco but must never cover any
  Spanish territory (`place_canary` takes a `max_x` cap and shrinks the
  archipelago if needed). City points move into the inset via
  `geo.canary_xy(point, scene["canary_tf"])`.
- Projections: peninsula EPSG:25830, Canaries EPSG:25828 (both metric, so
  the inset keeps true scale). Asturias maps also 25830.
- Community colors are hand-tuned so neighbours differ; if you change one,
  check its neighbours. Provinces use `style.shade()` variations of the
  community color. Concejos use greedy graph coloring.
- Names: common Castilian (see `PROVINCE_DISPLAY` / `CCAA_DISPLAY`).
- Every visible collision matters: after any change, re-render and actually
  look at the image at full size before committing.

## Environment

- Local: `make local-setup` then `make local-maps` (venv, Python 3.11+).
- Docker: `make setup` / `make maps` — the intended way for the user to run
  it. The Dockerfile is plain `python:3.12-slim` + pip requirements.
- `shapely>=2.1` is needed for `coverage_simplify` (the download script
  falls back to per-feature simplify on older versions).
- Committed data means `make data` is only needed to refresh sources.
- In Claude's remote sandbox there is no Docker daemon — use the venv path
  and say so rather than claiming the image was tested.

## Ideas not yet built

- Provinces one-map variant with all 50 names (callouts to margins).
- Province-capital maps (city dots + names), rivers/mountains physical maps.
- Gijón (city/parroquias) maps once a good source is picked.
- Comarcas of Asturias grouping map.
