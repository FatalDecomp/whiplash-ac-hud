"""Whiplash's packed sprite files, read the way the game reads them.

A `.bm` is one of the game's "compacted" files: a four-byte uncompressed
length, then a byte-opcode stream (`loadcompactedfilepart` in sound.c). What
comes out is a table of `tBlockHeader { int width, height, dataOffset; }`
followed by 8-bit palette-index pixels, rows unpadded, offsets measured from
the start of the table. Index 0 is transparent -- every blitter in func2.c
skips it.

Nothing here is guessed: each opcode below is the same branch the game takes.
"""

import struct
import sys
import zlib


def unmangle(data):
    """The game's loadcompactedfilepart, byte for byte.

    `data` is the whole file including the four-byte length header.
    """
    want = struct.unpack_from("<i", data, 0)[0]
    src = 4
    out = bytearray()

    while len(out) < want:
        if src >= len(data):
            break
        c = data[src]
        src += 1
        if not c:
            break

        if c & 128:
            # Block: a run copied from what has already been written.
            if c & 64:
                if c & 32:
                    # Long
                    off = ((c & 31) << 8) + data[src] + 3
                    src += 1
                    size = data[src] + 5
                    src += 1
                else:
                    # Medium
                    off = ((c & 3) << 8) + data[src] + 3
                    src += 1
                    size = ((c >> 2) & 7) + 4
                at = len(out) - off
                for i in range(size):
                    out.append(out[at + i])
            else:
                # Short: three bytes, a fixed distance back.
                at = len(out) - (c & 63) - 3
                out.append(out[at])
                out.append(out[at + 1])
                out.append(out[at + 2])
        else:
            if c & 64:
                if c & 32:
                    if c & 16:
                        # Word sequence: repeat the last two bytes.
                        size = (c & 15) + 2
                        word = bytes(out[-2:])
                        out.extend(word * size)
                    else:
                        # Byte sequence: repeat the last byte.
                        size = (c & 15) + 3
                        out.extend(bytes([out[-1]]) * size)
                else:
                    if c & 16:
                        # Word difference: carry on the last step, in words.
                        size = (c & 15) + 2
                        u = struct.unpack_from("<h", out, len(out) - 2)[0]
                        v = u - struct.unpack_from("<h", out, len(out) - 4)[0]
                        for _ in range(size):
                            u = (u + v) & 0xFFFF
                            out.extend(struct.pack("<H", u))
                    else:
                        # Byte difference: carry on the last step, in bytes.
                        size = (c & 15) + 3
                        u = out[-1]
                        v = u - out[-2]
                        for _ in range(size):
                            u = (u + v) & 0xFF
                            out.append(u)
            else:
                # String: c literal bytes.
                size = c & 63
                out.extend(data[src:src + size])
                src += size

    return bytes(out[:want])


class Block(object):
    __slots__ = ("width", "height", "offset", "pixels")

    def __init__(self, width, height, offset, pixels):
        self.width = width
        self.height = height
        self.offset = offset
        self.pixels = pixels


def read_blocks(raw):
    """The table at the front of an unpacked .bm, and the pixels it points at.

    How many blocks there are is not stored: the first block's data offset is
    where the table stops, which is the same thing the game relies on by
    indexing the table directly.
    """
    first = struct.unpack_from("<iii", raw, 0)[2]
    if first <= 0 or first % 12 or first > len(raw):
        raise ValueError("not a block file: first data offset %d" % first)

    blocks = []
    for i in range(first // 12):
        w, h, off = struct.unpack_from("<iii", raw, i * 12)
        if w <= 0 or h <= 0 or off <= 0 or off + w * h > len(raw):
            blocks.append(Block(0, 0, off, b""))
            continue
        blocks.append(Block(w, h, off, raw[off:off + w * h]))
    return blocks


def read_palette(path):
    """A .PAL is 256 six-bit RGB triples, as the VGA DAC took them."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 768:
        raise ValueError("%s is %d bytes, want 768" % (path, len(data)))
    return [tuple(min(255, c * 255 // 63) for c in data[i * 3:i * 3 + 3])
            for i in range(256)]


def write_png(path, width, height, pixels, palette, transparent=0):
    """An indexed PNG, so the art stays exactly the indices the game stored."""
    if width <= 0 or height <= 0:
        return False
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        rows.extend(pixels[y * width:(y + 1) * width])

    def chunk(tag, body):
        out = struct.pack(">I", len(body)) + tag + body
        return out + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    plte = b"".join(bytes(c) for c in palette)
    trns = bytes([0 if i == transparent else 255 for i in range(256)])
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
    png += chunk(b"PLTE", plte)
    png += chunk(b"tRNS", trns)
    png += chunk(b"IDAT", zlib.compress(bytes(rows), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return True


def load(path):
    with open(path, "rb") as f:
        return read_blocks(unmangle(f.read()))


if __name__ == "__main__":
    for name in sys.argv[1:]:
        blocks = load(name)
        print("%s: %d blocks" % (name, len(blocks)))
        for i, b in enumerate(blocks[:12]):
            print("   %3d  %3d x %-3d  @%d" % (i, b.width, b.height, b.offset))
