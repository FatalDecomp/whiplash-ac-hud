"""Dump a Whiplash .bm to one PNG per block, in the game's own palette.

Usage: dump_bm.py <PALETTE.PAL> <out-dir> <file.bm> [...]

The art is the user's own retail data and stays wherever they point this; it
is never part of the project.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import whiplash_bm


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    palette = whiplash_bm.read_palette(argv[1])
    out = argv[2]
    os.makedirs(out, exist_ok=True)

    for path in argv[3:]:
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        blocks = whiplash_bm.load(path)
        written = 0
        for i, b in enumerate(blocks):
            name = os.path.join(out, "%s_%02d.png" % (stem, i))
            if whiplash_bm.write_png(name, b.width, b.height, b.pixels,
                                     palette):
                written += 1
        print("%-12s %2d blocks, %2d written" % (stem, len(blocks), written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
