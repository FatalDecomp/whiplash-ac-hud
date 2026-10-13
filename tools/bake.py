"""Bake Whiplash's panel art into the textures the AC app draws.

The game's dial is one 79x70 sprite that encodes two gauges in its palette
indices, and `print_damage` in func2.c reads it like this:

  index 0            transparent
  index < 0x31       the rev arc: the index IS the step, 1..48. Lit when the
                     step is at or below fRPMRatio * 48, drawn 0xF3 (blue);
                     unlit, drawn 0xED (dark blue).
  index >= 0x31      the damage body. dam_remap[index] gives the zone's level
                     1..13; the zone keeps its own colour once the car's
                     damage has reached that level, and is 0x7B (grey) before
                     that. Indices the table leaves at -1 are always drawn.

Doing that per pixel every frame is fine in C on a 320x200 framebuffer and
silly in Python at 60 Hz, so it is baked out once: 49 rev frames and 14
damage frames, stacked at draw time.

Usage: bake.py <FATDATA dir> <out dir> [scale ...]

A scale is how many screen pixels to a panel pixel. The art is enlarged
here, with nearest neighbour, rather than in the game: AC's Python API has
no way to turn texture filtering off (the documentation gives only
ac.newTexture and ac.glQuadTextured, with nothing about sampling), so the
only way to keep the pixels hard-edged is to hand it a texture that is drawn
at exactly its own size.

Every scale asked for is baked into its own folder -- out/x2, out/x4 and so
on -- and the HUD draws from one of them. That is what lets the size be
changed in the game: switching folders swaps one crisp set of art for
another, where scaling a texture would just hand it to AC's filtering.

Reads the user's own retail data and writes PNGs wherever they say. Neither
the data nor what comes out of it belongs in a repository.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import whiplash_bm

# func2.c ascii_conv3: character code -> block in MINITEXT.BM. Taken from the
# game's own table rather than from the look of the contact sheet -- block 37
# is an accented E with no ASCII mapping, and guessing the order put it over
# the letter E. Space is the table's 0xFF sentinel, which prt_letter answers
# by advancing four pixels without drawing. [prt_letter, func2.c]
def read_charmap(path):
    chars = {}
    handle = open(path, "r")
    try:
        for line in handle:
            parts = line.split()
            if len(parts) == 2:
                chars[int(parts[0])] = int(parts[1])
    finally:
        handle.close()
    return chars


SPACE_ADVANCE = 4

# func2.c dam_remap: palette index -> damage level that lights it.
DAM_REMAP = {169: 8, 170: 7, 171: 6, 203: 5, 227: 13, 228: 12, 229: 11,
             230: 10, 231: 9, 252: 4, 253: 3, 254: 2, 255: 1}

REV_MAX = 48          # fRPMRatio * 48, the arc's own step numbering
DAM_MAX = 13          # thirteen zones, plus 0 for an undamaged car
REV_LIT = 0xF3        # blue
REV_DARK = 0xED       # dark blue
DAM_DULL = 0x7B       # grey

# Which block is what in PANEL2.BM, read off func2.c's own indexing.
PANEL = {
    "dial": 0,
    "gear": (1, 8),        # R, N, 1..6 -- block is (gear + 3)
    "speed": (9, 18),      # small white digits, block is (digit + 9)
    "bar": 19,             # the dark bar the lap number sits on
    "lap_label": 20,
    "pos_label": 21,
    "big": (22, 31),       # chrome digits, block is (digit + 22)
    "kmh": 32,
    "mph": 33,
}


def split_dial(block):
    """The dial's pixels, sorted into the two gauges that share them."""
    rev = []
    dam = []
    for p in block.pixels:
        if p == 0 or p >= 0x31:
            rev.append(0)
        else:
            rev.append(p)
        if p >= 0x31:
            dam.append(p)
        else:
            dam.append(0)
    return bytes(rev), bytes(dam)


def rev_frame(rev_pixels, step):
    """The arc at one rev step, lit up to `step`."""
    out = bytearray(len(rev_pixels))
    for i, p in enumerate(rev_pixels):
        if not p:
            continue
        out[i] = REV_LIT if p <= step else REV_DARK
    return bytes(out)


def dam_frame(dam_pixels, level):
    """The body at one damage level: zones it has reached keep their colour."""
    out = bytearray(len(dam_pixels))
    for i, p in enumerate(dam_pixels):
        if not p:
            continue
        zone = DAM_REMAP.get(p, -1)
        out[i] = p if level >= zone else DAM_DULL
    return bytes(out)


def enlarge(pixels, width, height, scale):
    """Nearest neighbour, the way the game's own scaled blitter steps."""
    if scale <= 1:
        return pixels, width, height
    out = bytearray(width * scale * height * scale)
    for y in range(height * scale):
        row = pixels[(y // scale) * width:(y // scale) * width + width]
        wide = bytearray()
        for p in row:
            wide.extend([p] * scale)
        out[y * width * scale:(y + 1) * width * scale] = wide
    return bytes(out), width * scale, height * scale


DEFAULT_SCALES = (2, 3, 4, 6)


def bake_one(art, out, scale):
    """Every texture, enlarged to one scale, into one folder."""
    palette, panel, font, cars = art
    os.makedirs(out, exist_ok=True)
    dial = panel[PANEL["dial"]]
    rev_pixels, dam_pixels = split_dial(dial)
    emitted = {}
    written = 0

    def put(name, pixels, width, height):
        px, w, h = enlarge(pixels, width, height, scale)
        if whiplash_bm.write_png(os.path.join(out, name + ".png"), w, h, px,
                                 palette):
            emitted[name] = (w, h)
            return 1
        return 0

    def emit(name, block):
        return put(name, block.pixels, block.width, block.height)

    for step in range(REV_MAX + 1):
        written += put("rev_%02d" % step, rev_frame(rev_pixels, step),
                       dial.width, dial.height)
    for level in range(DAM_MAX + 1):
        written += put("dam_%02d" % level, dam_frame(dam_pixels, level),
                       dial.width, dial.height)
    for d in range(10):
        written += emit("speed_%d" % d, panel[PANEL["speed"][0] + d])
        written += emit("big_%d" % d, panel[PANEL["big"][0] + d])
    for i, name in enumerate(["R", "N", "1", "2", "3", "4", "5", "6"]):
        written += emit("gear_%s" % name, panel[PANEL["gear"][0] + i])
    written += emit("bar", panel[PANEL["bar"]])
    written += emit("lap", panel[PANEL["lap_label"]])
    written += emit("pos", panel[PANEL["pos_label"]])
    written += emit("kmh", panel[PANEL["kmh"]])
    written += emit("mph", panel[PANEL["mph"]])

    # The mini font, one texture per block, named by block so the character
    # table decides what maps to what.
    for i in range(len(font)):
        written += emit("font_%02d" % i, font[i])

    # Whiplash's cars; the skull at the end is its kill counter, which has no
    # meaning in AC and is left for whoever wants it.
    for i in range(len(cars)):
        written += emit("car_%d" % i, cars[i])

    # What the app needs to lay any of this out: every texture's real size,
    # and the character table. Sizes vary -- the chrome 1 is 14 wide against
    # 21 for the rest, and the speed 1 is 7 against 12 -- so a fixed width
    # would stretch them.
    here = os.path.dirname(os.path.abspath(__file__))
    chars = read_charmap(os.path.join(here, "ascii_conv3.txt"))
    sizes = ["# scale %d" % scale]
    for name, size in sorted(emitted.items()):
        sizes.append("%s %d %d" % (name, size[0], size[1]))
    handle = open(os.path.join(out, "sizes.txt"), "w")
    try:
        handle.write("\n".join(sizes) + "\n")
    finally:
        handle.close()
    handle = open(os.path.join(out, "charmap.txt"), "w")
    try:
        handle.write("space %d\n" % SPACE_ADVANCE)
        for code in sorted(chars):
            handle.write("%d %d\n" % (code, chars[code]))
    finally:
        handle.close()
    return written


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    fat, out = argv[1], argv[2]
    try:
        scales = [int(v) for v in argv[3:]] or list(DEFAULT_SCALES)
    except ValueError:
        print(__doc__)
        return 2
    scales = sorted(set(s for s in scales if 1 <= s <= 12))
    if not scales:
        print("scales run 1 to 12")
        return 2

    def fat_path(name):
        for n in (name, name.upper(), name.lower()):
            p = os.path.join(fat, n)
            if os.path.exists(p):
                return p
        raise SystemExit("%s not found in %s" % (name, fat))

    art = (whiplash_bm.read_palette(fat_path("PALETTE.PAL")),
           whiplash_bm.load(fat_path("PANEL2.BM")),
           whiplash_bm.load(fat_path("MINITEXT.BM")),
           whiplash_bm.load(fat_path("PANCAR1.BM")))

    for scale in scales:
        folder = os.path.join(out, "x%d" % scale)
        written = bake_one(art, folder, scale)
        print("%d textures at %dx in %s" % (written, scale, folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
