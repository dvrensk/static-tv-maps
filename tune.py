#!/usr/bin/env python3
"""Run the interactive label tuner ("el ajustador").

Usage:
    python tune.py                     # http://localhost:8321/
    python tune.py --port 9000
    python tune.py --host 0.0.0.0     # reachable from the LAN / a phone
    python tune.py --theme sobrio     # tune against another palette

The tuner edits label placement in the tvmaps/maps_*.py tables and writes
the values back into those files; final maps still come from generate.py.
"""

import argparse


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8321)
    ap.add_argument("--theme", default="vivo")
    args = ap.parse_args()

    from tvmaps import style

    if args.theme not in style.THEMES:
        ap.error(f"unknown theme {args.theme!r}; options: "
                 + ", ".join(style.THEMES))
    style.set_theme(args.theme)

    from tvmaps.tuner.server import serve

    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
