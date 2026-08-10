# CLAUDE.md

Guidance for working on this repository.

## What this project is

Machinery that renders **pedagogical maps of Spain, Asturias and América
Central as static 4000×2250 px (16:9) PNGs** for a TV's standby slideshow. Hard
requirements:

- Output exactly 4000×2250; the TV displays PNG or JPEG as-is.
- Text must be readable from ~5 m: prefer fewer, bigger labels. If names
  don't fit on one map, split them across two maps or use leader-line
  callouts — never shrink text below ~24 pt (33 px).
- The Canary Islands must appear on every Spain-wide map, transposed into a
  framed inset (currently lower-left, at true scale).
- Rendering must never need the network: everything a map reads is committed
  (`data/processed/`, `assets/`).

## Layout

- `generate.py` — CLI. `python generate.py all | <map-name> | --list [--jpg]`.
  Map names are derived from `render_*` functions in `tvmaps/maps_*.py`.
- `tvmaps/style.py` — canvas constants, palette (keyed by INE community
  code), `COUNTRY_COLORS` for the América Central maps (keyed by ISO alpha-2),
  display-name overrides, font loading (bundled Inter in `assets/fonts/`).
- `tvmaps/geo.py` — data loading, projections (Spain UTM 30N/28N, Central
  America LCC), 16:9 frame computation, Canary inset placement, label anchor
  (pole of inaccessibility).
- `tvmaps/draw.py` — canvas, halo text, callouts, title/attribution, side
  panels and flag images (`panel_box`, `flag`), save.
- `tvmaps/maps_spain.py`, `tvmaps/maps_asturias.py`, `tvmaps/maps_capitals.py`,
  `tvmaps/maps_ciudades.py`, `tvmaps/maps_fisica.py`, `tvmaps/maps_rios.py`,
  `tvmaps/maps_productos.py`, `tvmaps/maps_centroamerica.py`,
  `tvmaps/maps_gijon.py` (schematic Gijón street maps, spec in
  `docs/gijon-schematic-design.md`) — the actual maps and all per-feature label
  tuning. New modules must be added to the registry tuple in `generate.py`.
- `tvmaps/cities.py` — city gazetteer access (`data/processed/cities.geojson`,
  geocoded via Nominatim by the download script) plus metadata: province and
  community capitals, INE 2025 big-city populations, Asturias towns over
  10 000 inhabitants, and the 8 functional comarcas with their concejos.
- `scripts/download_data.py` — fetches raw sources into `data/raw/`
  (gitignored) and writes simplified GeoJSON to `data/processed/`
  (committed), plus the flag PNGs in `assets/flags/` (committed, one per ISO
  alpha-2 code). Rendering never needs the network.
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
- No new "mapa mudo" (nameless) variants — standing instruction from the user.
  The three that already exist stay; don't add more, and don't offer them.
- No big titles: maps identify themselves with a small footer caption
  (`draw.draw_footer`, `side="left"|"right"`) so the geography gets every
  pixel. Anything that makes the peninsula smaller is a net negative — a title
  is only allowed where it costs nothing, e.g. inside the Central America flag
  panel, which sits on space no geography wants.
- The Canary inset may cover Portugal or Morocco but must never cover any
  Spanish territory (`place_canary` takes a `max_x` cap and shrinks the
  archipelago if needed). City points move into the inset via
  `geo.canary_xy(point, scene["canary_tf"])`.
- Projections: peninsula EPSG:25830, Canaries EPSG:25828 (both metric, so
  the inset keeps true scale). Asturias maps also 25830. Central America uses
  `geo.CENTRAL_AMERICA_CRS` and the extended map `geo.MEXICO_CARIBE_CRS`, both
  metric LCCs centred on their region.
- América Central (`maps_centroamerica.py`) holds two maps that share the flag
  machinery (`_flag_entry`, `draw.panel_box`, `draw.flag`). Each flag is framed
  in a passe-partout of its country's map fill, which is what ties panel to
  map; `style.COUNTRY_COLORS` is keyed by ISO alpha-2.
  - `centroamerica`: the isthmus is much taller than 16:9, so the frame is
    height-constrained and the leftover Caribbean column holds the panel —
    widening `PANEL_FRAC` costs no map scale, but the seven countries are
    already at full width, so there is no room to shift them sideways. The
    panel stops `PANEL_BOTTOM_PX` above the bottom edge so the corner where
    Colombia enters stays visible.
  - `mexico-centroamerica-caribe`: Mexico's width sets the scale (~1.37 km/px,
    half the other map's), so the panel moves to the empty Pacific as a 3x4
    grid (`EXT_PANEL_PX`, in canvas pixels). Its top edge is capped by the
    Mexican Pacific coast — the panel must never cover Mexican territory, and
    the coast reaches y≈712 px — so cell width is scarce: long names are
    abbreviated or wrapped (`EXT_PANEL_NAMES`, `EXT_PANEL_CAPITALS`). At this
    scale six capital names will not fit inside the isthmus, so capitals are
    stars on the map and the panel is what names them.
  - In both, context/water labels that would fall inside the panel rect are
    skipped automatically by `_draw_context_labels`.
  - The Panama Canal (`CANAL_LONLAT`, `_draw_canal`) is hand-traced — Natural
    Earth has no canal here — and drawn as a white-cased navy line so ~60 km
    still reads at either scale. Its label goes north-east into the Caribbean;
    the Gulf of Panama side is taken by the capital and the Islas Perlas.
  - Panel populations (`COUNTRY_POPULATION`, extended map only) are rounded on
    purpose: whole millions above five, half millions below, thousands for
    Belice. Keep them rounded — the point is numbers a viewer can repeat, and
    the rounding outlives the estimate.
- Community colors are hand-tuned so neighbours differ; if you change one,
  check its neighbours. Provinces use `style.shade()` variations of the
  community color. Concejos use greedy graph coloring.
- Three palettes live in `style.py` (`THEMES`): "vivo" (default), "sobrio"
  (muted) and "galaxia" (vivid cosmic). `generate.py all --theme <name>`
  renders only the political maps (see `POLITICAL_MAPS`) with a per-theme
  suffix. Modules read `style.CCAA_COLORS` / `style.CONCEJO_PALETTE` /
  `style.COMARCA_COLORS` at render time, which `style.set_theme()` swaps.
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
- Most development happens in Claude on the web; the user renders locally
  via Docker. Rendering in a different environment recompresses the PNGs
  and shifts antialiasing by ±1/255 — byte churn with no visible change.
  `make unchurn` (venv; or `.venv/bin/python scripts/unchurn.py`) restores
  modified images in `output/` that are visually identical to the committed
  version. Run it after a full re-render so only real changes get committed.

## Ideas not yet built

- Provinces one-map variant with all 50 names (callouts to margins).
- Province-capital maps (city dots + names), rivers/mountains physical maps.
- Gijón (city/parroquias) maps once a good source is picked.
- Comarcas of Asturias grouping map.
