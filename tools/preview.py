"""Compose the HUD offline, so it can be looked at without Assetto Corsa.

The panel is anchored corner by corner, the way Whiplash anchors its own
(func2.c positions everything as winw - N and winh - N). Nothing is
stretched to fit: the sprites are drawn at an integer scale and the gaps
between the clusters take up the slack, so an ultrawide screen gets the same
panel as a 4:3 one with more road showing in between.

Usage: preview.py <FATDATA dir> <out.png> [WxH] [scale]
                  [rpm] [wear] [speed] [gear] [lap] [pos]
"""

import math
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bake
import whiplash_bm


def _layout():
    """The app's own LAYOUT block, so there is one copy of these numbers.

    whiplash_hud.py imports ac and acsys at the top, which only exist inside
    Assetto Corsa; standing in empty modules lets the constants be read here
    without the game. Nothing in the module runs at import time beyond that.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    app = os.path.join(os.path.dirname(here), "apps", "python",
                       "whiplash_hud")
    for name in ("ac", "acsys"):
        sys.modules.setdefault(name, types.ModuleType(name))
    # sim_info maps AC's shared memory the moment it is imported, which
    # cannot work outside the game; an empty one keeps the import quiet.
    sys.modules.setdefault("sim_info", types.ModuleType("sim_info"))
    sys.path.insert(0, app)
    import whiplash_hud
    return whiplash_hud


L = _layout()

# A mid grey to lay the panel on while looking at it. Over the game, index 0
# is see-through and index 112 -- which the art outlines with -- is black, so
# on a black test ground both vanish and the panel looks full of holes.
TEST_GROUND = 126

INK_BORDER = 112
INK_MAP = 0xF3
INK_BLIP = 0xED


class Canvas(object):
    def __init__(self, w, h, fill=TEST_GROUND):
        self.w = w
        self.h = h
        self.px = bytearray([fill]) * (w * h)

    def blit(self, block, x, y, pixels=None, scale=1):
        """A block, skipping index 0 the way every blitter in func2.c does."""
        src = pixels if pixels is not None else block.pixels
        for row in range(block.height * scale):
            ty = y + row
            if ty < 0 or ty >= self.h:
                continue
            base = (row // scale) * block.width
            for col in range(block.width * scale):
                tx = x + col
                if tx < 0 or tx >= self.w:
                    continue
                p = src[base + col // scale]
                if p:
                    self.px[ty * self.w + tx] = p

    def rect(self, x, y, w, h, ink):
        for ty in range(max(0, y), min(y + h, self.h)):
            for tx in range(max(0, x), min(x + w, self.w)):
                self.px[ty * self.w + tx] = ink

    def frame(self, x, y, w, h, ink, weight=1):
        self.rect(x, y, w, weight, ink)
        self.rect(x, y + h - weight, w, weight, ink)
        self.rect(x, y, weight, h, ink)
        self.rect(x + w - weight, y, weight, h, ink)


class Art(object):
    """Everything the panel draws, indexed the way func2.c indexes it."""

    SPACE = 4      # what prt_letter advances for an unmapped character

    def __init__(self, fat):
        here = os.path.dirname(os.path.abspath(__file__))
        self.chars = bake.read_charmap(os.path.join(here, "ascii_conv3.txt"))
        def path(name):
            for n in (name, name.upper(), name.lower()):
                p = os.path.join(fat, n)
                if os.path.exists(p):
                    return p
            raise SystemExit("%s not found in %s" % (name, fat))

        self.palette = whiplash_bm.read_palette(path("PALETTE.PAL"))
        self.panel = whiplash_bm.load(path("PANEL2.BM"))
        self.font = whiplash_bm.load(path("MINITEXT.BM"))
        self.dial = self.panel[bake.PANEL["dial"]]
        self.rev_pixels, self.dam_pixels = bake.split_dial(self.dial)

    def speed_digit(self, d):
        return self.panel[bake.PANEL["speed"][0] + d]

    def big_digit(self, d):
        return self.panel[bake.PANEL["big"][0] + d]

    def gear_block(self, gear):
        """gear: -1 reverse, 0 neutral, 1.. forward. R and N lead the row."""
        idx = 0 if gear < 0 else (1 if gear == 0 else min(gear, 6) + 1)
        return self.panel[bake.PANEL["gear"][0] + idx]

    def glyph(self, ch):
        """The font block for a character [ascii_conv3, func2.c]."""
        block = self.chars.get(ord(ch))
        if block is None and ch.isalpha():
            block = self.chars.get(ord(ch.upper()))
        return block

    def text(self, canvas, s, x, y, scale=1):
        """mini_prt_string: each glyph advances by its own width, and a
        character the table does not carry advances four and draws nothing
        [prt_letter, func2.c]."""
        for ch in s:
            block = self.glyph(ch)
            if block is None or block >= len(self.font):
                x += self.SPACE * scale
                continue
            canvas.blit(self.font[block], x, y, scale=scale)
            x += self.font[block].width * scale
        return x

    def text_width(self, s, scale=1):
        total = 0
        for ch in s:
            block = self.glyph(ch)
            if block is None or block >= len(self.font):
                total += self.SPACE * scale
            else:
                total += self.font[block].width * scale
        return total

    def number(self, canvas, s, x, y, big=False, scale=1):
        """A run of digit sprites, kerned a pixel the way the panel kerns."""
        for ch in s:
            if ch.isdigit():
                b = (self.big_digit(int(ch)) if big
                     else self.speed_digit(int(ch)))
                canvas.blit(b, x, y, scale=scale)
                x += (b.width - 1) * scale
        return x

    def number_width(self, s, big=False):
        """In panel pixels, the unit the layout is written in."""
        total = 0
        for ch in s:
            if ch.isdigit():
                b = (self.big_digit(int(ch)) if big
                     else self.speed_digit(int(ch)))
                total += b.width - 1
        return total


def ordinal(place):
    """1ST, 2ND, 3RD, 4TH -- what print_pos prints beside a driver's name."""
    if 10 <= place % 100 <= 20:
        return "%dTH" % place
    return "%d%s" % (place, {1: "ST", 2: "ND", 3: "RD"}.get(place % 10, "TH"))


def clock(seconds):
    """MM:SS:hh, the shape Whiplash prints its times in."""
    if not seconds or seconds <= 0:
        return "--:--:--"
    total = int(seconds * 100.0)
    return "%02d:%02d:%02d" % (total // 6000, (total // 100) % 60, total % 100)


def auto_scale(height):
    """How many screen pixels to a panel pixel.

    The art is 320x200-era, so on a 1080p screen it wants trebling and on a
    4K one doubling again. Whole numbers only: a half-scaled sprite is a
    blurred sprite, and the whole point of the art is that it is crisp.
    """
    return max(1, int(round(height / 360.0)))


def draw_hud(art, canvas, state, scale=2, margin=0):
    """The panel, placed the way test_panel() in func2.c places it.

    Every offset comes from the app's LAYOUT block, which is where they are
    documented; this just draws them with the raw blocks instead of the
    baked textures, so the baker and the layout can both be checked without
    starting the game.
    """
    s = scale
    m = margin * s
    left, top = m, m
    right, bottom = canvas.w - m, canvas.h - m

    # --- bottom right: the gauge -----------------------------------------
    dial_x = right + L.DIAL_X * s
    dial_y = bottom - (L.DIAL_H + L.DIAL_BOTTOM) * s
    step = int(round(max(0.0, min(1.0, state["rpm"])) * bake.REV_MAX))
    canvas.blit(art.dial, dial_x, dial_y,
                bake.rev_frame(art.rev_pixels, step), scale=s)
    canvas.blit(art.dial, dial_x, dial_y,
                bake.dam_frame(art.dam_pixels, state["ring"]), scale=s)

    art.number(canvas, "%d" % max(0, int(state["speed"])),
               dial_x + L.SPEED_X * s, dial_y + L.SPEED_Y * s, scale=s)
    canvas.blit(art.panel[bake.PANEL["mph" if state.get("mph", True)
                                     else "kmh"]],
                dial_x + L.UNIT_X * s, dial_y + L.UNIT_Y * s, scale=s)
    canvas.blit(art.gear_block(state["gear"]),
                dial_x + L.GEAR_X * s, dial_y + L.GEAR_Y * s, scale=s)

    # --- top left: the position plate, names on its own two bars ---------
    canvas.blit(art.panel[bake.PANEL["pos_label"]],
                left + L.POS_X * s, top + L.POS_Y * s, scale=s)
    place = max(1, min(99, state["pos"]))
    number = "%d" % place
    art.number(canvas, number,
               left + (L.POS_NUM_CX
                       - art.number_width(number, True) // 2) * s,
               top + L.POS_NUM_Y * s, big=True, scale=s)
    for name, who, row in ((state.get("ahead_name"), place - 1, L.AHEAD_Y),
                           (state.get("behind_name"), place + 1, L.BEHIND_Y)):
        if not name:
            continue
        art.text(canvas, ordinal(who), left + L.NAME_X * s, top + row * s,
                 scale=s)
        art.text(canvas, name[:12],
                 left + L.NAME_RIGHT * s - art.text_width(name[:12], s),
                 top + row * s, scale=s)

    # --- top right: the lap plate ----------------------------------------
    canvas.blit(art.panel[bake.PANEL["bar"]],
                right + L.LAP_BAR_X * s, top + L.LAP_BAR_Y * s, scale=s)
    lap = "%d" % max(1, min(99, state["lap"]))
    art.number(canvas, lap,
               right + (L.LAP_NUM_CX - art.number_width(lap, True) // 2) * s,
               top + L.LAP_NUM_Y * s, big=True, scale=s)
    canvas.blit(art.panel[bake.PANEL["lap_label"]],
                right + L.LAP_X * s, top + L.LAP_Y * s, scale=s)

    # --- top centre: the clock -------------------------------------------
    rows = [("TIME:", state["time"]), ("BEST:", state["best"]),
            ("INFRONT:", state.get("infront")),
            ("BEHIND:", state.get("behind"))]
    middle = canvas.w // 2
    y = top + L.CLOCK_Y * s
    for label, value in rows:
        art.text(canvas, label,
                 middle - L.CLOCK_PAD * s - art.text_width(label, s), y,
                 scale=s)
        art.text(canvas, clock(value), middle, y, scale=s)
        y += L.CLOCK_ROW * s

    # --- bottom left: the map --------------------------------------------
    mw, mh = L.MAP_W * s, L.MAP_H * s
    mx, my = left, bottom - mh
    canvas.frame(mx, my, mw, mh, INK_BORDER, weight=s)
    for i in range(96):
        t = i / 96.0 * 2.0 * math.pi
        canvas.rect(int(mx + mw / 2 + mw * 0.34 * math.cos(t)),
                    int(my + mh / 2 + mh * 0.32 * math.sin(t)),
                    s, s, INK_MAP)
    canvas.rect(int(mx + mw / 2 + mw * 0.34), int(my + mh / 2),
                2 * s, 2 * s, INK_BLIP)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    fat, out = argv[1], argv[2]
    size = argv[3] if len(argv) > 3 else "1920x1080"
    W, H = [int(v) for v in size.lower().split("x")]
    scale = int(argv[4]) if len(argv) > 4 and argv[4] != "auto" \
        else auto_scale(H)

    state = {
        "rpm": float(argv[5]) if len(argv) > 5 else 0.78,
        "ring": int(argv[6]) if len(argv) > 6 else 6,
        "speed": float(argv[7]) if len(argv) > 7 else 192,
        "gear": int(argv[8]) if len(argv) > 8 else 4,
        "lap": int(argv[9]) if len(argv) > 9 else 7,
        "pos": int(argv[10]) if len(argv) > 10 else 1,
        "time": 6.24, "best": 35.86, "infront": 1.87, "behind": 7.14,
        "ahead_name": "MARVIN", "behind_name": "KITA", "mph": True,
    }

    art = Art(fat)
    canvas = Canvas(W, H)
    draw_hud(art, canvas, state, scale=scale, margin=L.MARGIN)
    whiplash_bm.write_png(out, W, H, bytes(canvas.px), art.palette,
                          transparent=-1)
    print("%s  %dx%d  scale %d" % (out, W, H, scale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
