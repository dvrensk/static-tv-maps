# Editor protocol

How an external layout editor (the tvOS app in `tvos/`) reads a map's
labels, lets the user move them, and persists the result back to this
repository. The Python literals in `tvmaps/maps_*.py` remain the canonical
layout; the editor's output is a small patch file per map.

## The three artifacts

| Path | Written by | Read by |
|---|---|---|
| `editor/<map>/base.png` | `generate.py export` | editor (background image) |
| `editor/<map>/labels.json` | `generate.py export` | editor (label manifest) |
| `overrides/<map>.json` | the editor | `generate.py` at render time |

`editor/index.json` lists every exported map with its paths and label
count — fetch it first to build the map browser.

All reads are unauthenticated (`raw.githubusercontent.com`, public repo).
The only authenticated call is the override write (see below).

## Manifest (`editor/<map>/labels.json`, schema 1)

- `canvas`: always 4000×2250 px at DPI 100 (1 pt = 100/72 ≈ 1.389 px).
- `km_per_px`: one scalar for the whole canvas. Valid inside the Canary
  inset too, because offsets there are applied after the inset transform
  (they are canvas-kilometres, not ground-kilometres; `in_canary_inset`
  flags those labels, purely informational).
- `canary_inset_px`: the inset rectangle, or `null` (Asturias maps).
- `labels[]`: every editable label, suppressed from `base.png`:
  - `id` — stable key, e.g. `ccaa:12`, `prov:33`, `city:Oviedo`,
    `bigcity:Madrid`, `river:Duero`, `range:SISTEMA CENTRAL`,
    `zone:Rioja`, `town:Gijón`. Namespaced per map; the same city on two
    maps is edited independently.
  - `text` — final display string (may contain `\n`; render with
    `linespacing` 0.95).
  - `anchor_px` — the feature anchor (region pole of inaccessibility,
    city dot, river label point, zone blob centroid) **before** offsets.
  - `offset_km` (`dx`, `dy`) — anchor shift. `callout_km` (`tx`, `ty`) —
    when non-null the label is a leader-line callout: the text sits at
    anchor + offset + callout and `leader` gives both endpoints in px.
  - `text_px` — where the text anchor currently sits (= anchor_px plus
    offsets converted at `km_per_px`). `bbox_px` — measured extent
    (union of text, badge and leader; axis-aligned even when rotated).
  - Style: `size_pt`, `weight` (`regular|semibold|extrabold`, Inter),
    `color`, `halo` (`color`, `width_pt` — a centred stroke, so it
    extends `width_pt/2` outward), `ha`, `va`, `rotation` (degrees,
    counter-clockwise), `linespacing`.
  - `badge` — numbered maps only: measured circle (`center_px`,
    `radius_px`, `gap_px`) plus digit styling, so the group can be drawn
    without re-implementing the layout math. The whole group moves as
    one, anchored per `ha`/`va` exactly like plain text.
  - `marker` — a dot/star that stays baked into base.png (do not draw
    it; do not move it — labels move, features don't).
  - `sub` — product zones: a second, smaller line under the main text.
  - `editable` — which fields an override may set for this label.
- `locked[]`: text baked into base.png (footer, attribution, legends,
  swatches, inset caption) with `bbox_px`, for collision hints only.

## Drag math

Pixel coordinates have their origin at the top-left, y down; km offsets
are cartographic, y up. For a drag of (Δx, Δy) px:

```
dx' = dx + Δx * km_per_px
dy' = dy - Δy * km_per_px        # note the sign flip
```

Same formula for `tx`/`ty` when dragging a callout's text. Whole-km
values are plenty (1 km ≈ 2 px on Spain maps, ≈ 20 px on Asturias maps);
the repo convention is integer or one-decimal km.

## Overrides (`overrides/<map>.json`, schema 1)

```json
{
  "schema": 1,
  "map": "spain-comunidades",
  "labels": {
    "ccaa:12": {"dx": 60, "dy": -40, "size": 50},
    "ccaa:06": {"tx": null, "ty": null, "dy": 20}
  }
}
```

- Values are **absolute replacements** for the manifest's current
  normalized fields, not deltas. Fields: `dx`, `dy`, `tx`, `ty`, `size`,
  `ha`, `va`, `rotation` (each label's `editable` list narrows this).
- `tx: null` demotes a callout to a plain label; setting `tx` + `ty`
  promotes a plain label to a callout.
- Only include labels that changed. Delete a label's entry to revert it
  to the Python literal. A missing or empty file means no overrides.
- The renderer warns and skips unknown ids or invalid values — it never
  fails a render because of a bad override.

### Writing via the GitHub Contents API

```
GET  /repos/dvrensk/static-tv-maps/contents/overrides/<map>.json?ref=main
       -> current sha + content (404 if none yet)
PUT  /repos/dvrensk/static-tv-maps/contents/overrides/<map>.json
       {"message": "...", "content": base64(json), "sha": <sha if updating>,
        "branch": "main"}
```

Auth: fine-grained personal access token, Contents read/write, scoped to
this repository only. On 409 (concurrent update) re-GET the sha, re-apply
the local patch, retry.

After the push, the `apply-label-overrides` workflow re-renders the
affected maps (~1–2 min) and commits new `output/*.png` and `editor/`
artifacts. Poll `output/<map>.png` (compare the commit sha or ETag) to
show the true render for confirmation. The workflow only re-exports
manifests; `base.png` changes only when geometry or style change, so
cached base images stay valid across label edits.

## Round-tripping rules for the renderer (implementation notes)

- Anchors are computed at render time (polylabel, centroids, gazetteer
  points); only offsets are stored. The manifest carries the resolved
  anchor so editors never need geo data.
- Derived values stay derived: concejo A/B groups and default sizes
  (area rank), city dot/label sizes (population tiers), `wrap_name()`
  line breaks. An override's `size` wins over a derived size.
- Historical quirks preserved: `asturias-rios` town labels render
  extrabold as plain labels but semibold as callouts; converting one via
  override changes its weight accordingly.
- Renaming a Python literal key orphans its override (warned, skipped) —
  fold or delete the override entry when renaming.
