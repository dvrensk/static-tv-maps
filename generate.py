#!/usr/bin/env python3
"""Render the TV maps.

Usage:
    python generate.py all              # render every map into output/
    python generate.py <map-name>       # render one map
    python generate.py --list           # list available maps
    python generate.py all --jpg        # also write JPEG copies
    python generate.py all --theme sobrio   # muted palette for political maps

The political maps (communities, provinces, capitals, Asturias concejos and
comarcas) come in two color themes: "vivo" (default, bright) and "sobrio"
(muted "antique atlas"). The sobrio variants are written with a "-sobrio"
suffix, so both sets coexist in output/. `all --theme sobrio` renders only the
political maps (the rest look identical across themes).
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
    from tvmaps import (maps_asturias, maps_capitals, maps_ciudades,
                        maps_comcap, maps_editoriales, maps_fisica, maps_marcas,
                        maps_moda, maps_productos, maps_rios, maps_spain)

    maps = {}
    for mod in (maps_spain, maps_asturias, maps_capitals, maps_ciudades,
                maps_fisica, maps_rios, maps_productos, maps_moda,
                maps_editoriales, maps_marcas, maps_comcap):
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
    theme = "vivo"
    if "--theme" in argv:
        i = argv.index("--theme")
        theme = argv[i + 1]
        del argv[i:i + 2]
    from tvmaps import style

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
    if argv[0] == "all":
        # A non-default theme only changes the political maps; rendering the
        # rest again would just duplicate identical images under a suffix.
        targets = POLITICAL_MAPS if theme != "vivo" else sorted(maps)
    else:
        targets = argv
    for name in targets:
        if name not in maps:
            print(f"Unknown map: {name!r}. Use --list to see options.")
            return 1
        t0 = time.time()
        path = maps[name]()
        print(f"{name}: {path} ({time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
