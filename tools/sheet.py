"""A contact sheet of every block in a .bm, scaled up so it can be looked at.

Usage: sheet.py <PALETTE.PAL> <out.png> <scale> <file.bm>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import whiplash_bm

def main(argv):
    pal = whiplash_bm.read_palette(argv[1])
    out, scale, path = argv[2], int(argv[3]), argv[4]
    blocks = [b for b in whiplash_bm.load(path) if b.width > 0]
    cols = 8
    cw = max(b.width for b in blocks) + 2
    ch = max(b.height for b in blocks) + 2
    rows = (len(blocks) + cols - 1) // cols
    W, H = cw * cols, ch * rows
    canvas = bytearray([126]) * (W * H)
    for i, b in enumerate(blocks):
        ox, oy = (i % cols) * cw + 1, (i // cols) * ch + 1
        for y in range(b.height):
            row = b.pixels[y * b.width:(y + 1) * b.width]
            canvas[(oy + y) * W + ox:(oy + y) * W + ox + b.width] = row
    # nearest-neighbour upscale
    big = bytearray(W * scale * H * scale)
    for y in range(H * scale):
        src = canvas[(y // scale) * W:(y // scale) * W + W]
        row = bytearray()
        for p in src:
            row.extend([p] * scale)
        big[y * W * scale:(y + 1) * W * scale] = row
    whiplash_bm.write_png(out, W * scale, H * scale, bytes(big), pal,
                          transparent=-1)
    print("%s  %d blocks  %dx%d" % (out, len(blocks), W * scale, H * scale))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
