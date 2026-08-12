"""Revert no-op re-renders: restore images in output/ whose bytes changed
but whose pixels didn't (visibly).

Re-rendering in a different environment (Docker vs venv, library upgrades)
recompresses the PNGs and shifts antialiasing rounding by ±1/255 on a
handful of pixels. Strict equality would keep that churn, so an image is
considered unchanged when the per-channel delta is at most MAX_DELTA and
at most MAX_FRACTION of pixels differ — far below anything visible, and
far below any real edit (moving a label or tweaking a color changes many
pixels at large deltas).

Compares the working tree against the index (so staged changes are never
touched) and uses `git restore`, which also restores from the index.
"""

import io
import subprocess
import sys

import numpy as np
from PIL import Image

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
MAX_DELTA = 2         # per-channel, out of 255
MAX_FRACTION = 0.005  # of all pixels


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def pixels(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"), dtype=np.int16)


def main() -> int:
    changed = git("diff", "--name-only", "--", "output").decode().splitlines()
    images = [p for p in changed if p.lower().endswith(IMAGE_SUFFIXES)]
    if not images:
        print("No modified images in output/.")
        return 0

    restore = []
    for path in images:
        try:
            indexed = pixels(git("show", f":{path}"))
            with open(path, "rb") as fh:
                worktree = pixels(fh.read())
        except Exception as exc:
            print(f"kept      {path}  (could not compare: {exc})")
            continue
        if indexed.shape != worktree.shape:
            print(f"kept      {path}  (dimensions differ)")
            continue
        delta = np.abs(indexed - worktree)
        max_delta = int(delta.max())
        fraction = float((delta.max(axis=2) > 0).mean())
        if max_delta <= MAX_DELTA and fraction <= MAX_FRACTION:
            restore.append(path)
        else:
            print(f"kept      {path}  (max delta {max_delta}, "
                  f"{fraction:.2%} of pixels differ)")

    if restore:
        subprocess.run(["git", "restore", "--", *restore], check=True)
        for path in restore:
            print(f"restored  {path}")
    print(f"{len(restore)} restored, {len(images) - len(restore)} kept.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
