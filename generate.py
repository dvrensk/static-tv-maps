#!/usr/bin/env python3
"""Render the TV maps.

Usage:
    python generate.py all              # render every map into output/
    python generate.py <map-name>       # render one map
    python generate.py export all       # write editor/<map>/{base.png,labels.json}
    python generate.py export <map-name>
    python generate.py --list           # list available maps
    python generate.py all --jpg        # also write JPEG copies
    python generate.py all --theme sobrio   # muted palette for political maps
    python generate.py <map-name> --no-overrides  # ignore overrides/*.json

The political maps (communities, provinces, capitals, Asturias concejos and
comarcas) come in two color themes: "vivo" (default, bright) and "sobrio"
(muted "antique atlas"). The sobrio variants are written with a "-sobrio"
suffix, so both sets coexist in output/. `all --theme sobrio` renders only the
political maps (the rest look identical across themes).

Label positions are the Python literals in tvmaps/maps_*.py patched by any
committed overrides/<map>.json (written by the external layout editor).
`export` renders each map with its editable labels suppressed (base.png) plus
a labels.json manifest describing them in pixel coordinates — the input the
editor works from.
"""

import sys
import time

# Maps whose appearance depends on the political color palette.
POLITICAL_MAPS = [
    "spain-comunidades", "spain-comunidades-mudo",
    "spain-provincias-1", "spain-provincias-2", "spain-provincias-mudo",
    "spain-provincias-numeros",
    "spain-capitales-provincias", "spain-capitales-comunidades",
    "asturias-concejos-1", "asturias-concejos-2", "asturias-concejos-mudo",
    "asturias-comarcas",
]


def registry():
    from tvmaps import (maps_asturias, maps_capitals, maps_centroamerica,
                        maps_ciudades, maps_comcap, maps_cotidiano,
                        maps_editoriales, maps_fisica, maps_gijon, maps_iconos,
                        maps_marcas, maps_marcas_logos, maps_moda,
                        maps_productos, maps_rios, maps_spain)

    maps = {}
    for mod in (maps_spain, maps_asturias, maps_capitals, maps_ciudades,
                maps_fisica, maps_rios, maps_productos, maps_moda,
                maps_editoriales, maps_marcas, maps_marcas_logos, maps_comcap,
                maps_iconos, maps_cotidiano, maps_gijon, maps_centroamerica):
        for name in dir(mod):
            if name.startswith("render_"):
                key = name[len("render_"):].replace("_", "-")
                maps[key] = getattr(mod, name)
    return maps


def main(argv):
    if "--jpg" in argv:
        from tvmaps import draw

        draw.SAVE_JPG = True
        argv = [a for a in argv if a != "--jpg"]
    use_overrides = "--no-overrides" not in argv
    argv = [a for a in argv if a != "--no-overrides"]
    theme = "vivo"
    if "--theme" in argv:
        i = argv.index("--theme")
        theme = argv[i + 1]
        del argv[i:i + 2]
    from tvmaps import style

    mode = "render"
    if argv and argv[0] == "export":
        mode = "export"
        theme = "vivo"  # label positions are theme-invariant
        argv = argv[1:]

    if theme not in style.THEMES:
        print(f"Unknown theme: {theme!r}. Options: {', '.join(style.THEMES)}")
        return 1
    style.set_theme(theme)

    maps = registry()
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("Maps:", ", ".join(sorted(maps)))
        return 0
    if argv[0] == "--list":
        for name in sorted(maps):
            print(name)
        return 0
    if argv[0] == "--list-political":
        for name in POLITICAL_MAPS:
            print(name)
        return 0
    if argv[0] == "all":
        # A non-default theme only changes the political maps; rendering the
        # rest again would just duplicate identical images under a suffix.
        targets = POLITICAL_MAPS if theme != "vivo" and mode == "render" \
            else sorted(maps)
    else:
        targets = argv
    from tvmaps import labeling

    for name in targets:
        if name not in maps:
            print(f"Unknown map: {name!r}. Use --list to see options.")
            return 1
        t0 = time.time()
        labeling.begin(name, mode=mode, use_overrides=use_overrides)
        try:
            path = maps[name]()
        finally:
            ctx = labeling.finish()
        for warning in ctx.warnings:
            print(f"  warning: {warning}")
        print(f"{name}: {path} ({time.time() - t0:.1f}s)")
    if mode == "export":
        labeling.write_index(targets)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
