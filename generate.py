#!/usr/bin/env python3
"""Render the TV maps.

Usage:
    python generate.py all            # render every map into output/
    python generate.py <map-name>     # render one map
    python generate.py --list         # list available maps
    python generate.py all --jpg      # also write JPEG copies
"""

import sys
import time


def registry():
    from tvmaps import (maps_asturias, maps_capitals, maps_ciudades,
                        maps_fisica, maps_productos, maps_rios, maps_spain)

    maps = {}
    for mod in (maps_spain, maps_asturias, maps_capitals, maps_ciudades,
                maps_fisica, maps_rios, maps_productos):
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
    maps = registry()
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("Maps:", ", ".join(sorted(maps)))
        return 0
    if argv[0] == "--list":
        for name in sorted(maps):
            print(name)
        return 0
    targets = sorted(maps) if argv[0] == "all" else argv
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
