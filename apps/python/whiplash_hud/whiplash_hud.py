"""Whiplash HUD for Assetto Corsa.

Fatal Racing's own dashboard over AC: the dial that is a rev counter and a
wear meter at once, its speed and gear, lap and position on the game's own
plates, the clock in the mini font, and the track map.

The art is not shipped with this app. Run tools/bake.py against your own copy
of Whiplash's FATDATA to produce the tex/ folder beside this file.

Everything is placed the way test_panel() in ROLLER's func2.c places it, in
panel pixels off the corner each cluster belongs to -- see THE LAYOUT below.
That is also how the panel survives a widescreen: the clusters sit in the
screen's corners and the extra width shows road, rather than stretching
320x200 across it.

Assetto Corsa runs Python 3.3, so nothing here uses anything newer.
"""

import os
import sys
import traceback

import ac
import acsys

APP_NAME = "Whiplash HUD"
BUILD = "2026-10-14 22:30"      # bumped every build, so the log says which copy is live
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")

sys.path.insert(0, os.path.join(HERE, "third_party"))
try:
    from sim_info import info
except Exception:
    info = None


# =========================================================================
#  THE LAYOUT -- nudge the panel from here
#
#  Every number below is in PANEL pixels (Whiplash's own 320x200 ones), and
#  gets multiplied by the scale the art was baked at. They come straight out
#  of test_panel() in func2.c, with the screen-edge arithmetic resolved:
#  where the game writes `winw - 44` for a dial drawn at `winw - 80`, this
#  says 36, i.e. 36 across from the dial's own left edge.
#
#  Positive X counts right from the cluster's left anchor, negative X counts
#  left from its right anchor. Y always counts down from the top of the
#  cluster. Change a number here and nothing else needs to know.
# =========================================================================

# The gauge, bottom right. Everything is measured from the dial's top-left
# corner, so moving DIAL_* moves the whole cluster together.
DIAL_W, DIAL_H = 79, 70        # the sprite's own size -- not a position
DIAL_X = -80                   # func2.c: winw - 80
DIAL_BOTTOM = 2                # ...and 2 panel pixels of floor under it
SPEED_X, SPEED_Y = 36, 27      # func2.c: winw - 44, y 155. Grows rightwards.
UNIT_X, UNIT_Y = 55, 44        # func2.c: winw - 25, y 172 -- the mph/kmh tag
GEAR_X, GEAR_Y = 66, 53        # func2.c: winw - 14, y 181 -- in the black slot

# The position plate, top left. The plate (block 21) carries its own two
# black bars; the names are printed onto them and the chrome number sits in
# the gap between them.
POS_X, POS_Y = 0, 8            # func2.c: x 0, y 8
POS_NUM_CX, POS_NUM_Y = 59, 12 # number centred on x 59, top at y 12
AHEAD_Y, BEHIND_Y = 9, 42      # the two name bars (print_pos(4, 9) / (4, 42))
NAME_X, NAME_RIGHT = 4, 74     # place on the left, driver ending at 74

# The lap plate, top right.
LAP_X, LAP_Y = -52, 5          # func2.c: winw - 52, y 5 -- the LAP tag
LAP_BAR_X, LAP_BAR_Y = -67, 21 # the dark bar the number sits on
LAP_NUM_CX, LAP_NUM_Y = -36, 25

# The clock, top centre. Whiplash puts this at a fixed x in its own font;
# here the values start at the middle of the window and the labels are
# right-aligned just left of them.
CLOCK_Y = 4
CLOCK_ROW = 10                 # func2.c prints its rows 10 apart
CLOCK_PAD = 2                  # gap between a label and its time

# The map, bottom left.
MAP_W, MAP_H = 96, 68

# =========================================================================


# The dial's own numbering [print_damage, func2.c].
REV_STEPS = 48
RING_LEVELS = 13

# What the ring can be made to read. It was Whiplash's damage meter; AC has
# damage but hardly anyone runs it, so it reads tyre life by default. Each
# source is turned into one 0..1 fraction, because the ring is thirteen
# zones that coloured up as the car got worse -- it has no numbers on it.
METERS = ("TYRES", "TEMP", "PRESSURE", "DAMAGE", "FUEL", "TURBO")

# The ends of each scale. The app logs the raw values the first time it
# reads a source, so these can be pinned from a real session rather than
# assumed.
#
# tyreWear is not a percentage of tread left. It is the grip the tyre has
# left off its WEAR_CURVE in tyres.ini: 100 when new, and a tyre is done by
# the low nineties. Read across 100..0 a whole stint moves the ring by a
# few percent, which rounds to no zones at all -- so the ring sat grey.
WEAR_FRESH = 100.0
WEAR_DEAD = 94.0
# The ring is a traffic light, and the sprite says where its colours change:
# zones 1-4 are green (palette 255, 254, 253, 252), 5-8 amber (203, 171, 170,
# 169) and 9-13 red (231, 230, 229, 228, 227).
#
# Wear, damage and fuel all mean "worse as it fills", so they run straight up
# it and the colours come out right on their own. Temperature does not: a
# tyre in its working window is *good*, and good has to read green. A plain
# cold-to-hot line cannot do that -- green is only the first third of the
# ring, so a working tyre lands in the amber or the red -- so temperature is
# bent to the bands instead, a stop at the top of each.
GREEN_TOP = 4          # zones, read off the dial's own palette indices
AMBER_TOP = 8
TEMP_COLD = 50.0       # under this the ring is empty
TEMP_GOOD = 95.0       # top of the green: the tyre is in its window
TEMP_WARM = 110.0      # top of the amber: getting hot
TEMP_HOT = 130.0       # full red: cooking

# Pressure is the other source with a good state that is not zero, and it is
# two-sided: under and over are both wrong. So the ring reads how far from
# ideal the worst tyre is, in either direction, against the same bands --
# green while it is close, amber drifting, red a long way off.
#
# "Ideal" is the car's own, out of its tyres.ini, so green means the pressure
# that car was built around rather than a number chosen here. These are the
# widths of the bands around it, in whatever unit the two agree on.
PRESSURE_GOOD = 1.0    # within this of ideal, the ring stays green
PRESSURE_WARN = 3.0    # ...and this is the top of the amber
PRESSURE_BAD = 8.0     # this far out is a full red ring
PRESSURE_IDEAL = 26.0  # only used when the car's tyres.ini cannot be read
DAMAGE_FULL = 100.0            # what counts as a wrecked panel in carDamage

MARGIN = 0             # extra panel pixels in from the window's edges; the
# game's own insets are already in the layout above, so 0 is Whiplash's
# placement exactly and anything more pulls the whole panel inward.

# Opens small on purpose. The panel anchors to the window's corners, so it
# works at any size, and a window that opens the size of the screen puts its
# own title bar and controls off the edge of it -- with no way back if it is
# pinned. Grow it by dragging, or by WIDTH/HEIGHT in config.ini.
WINDOW = (800, 450)
CONFIG_POLL = 0.5      # seconds between re-reads of config.ini

_config = {"scale": 0, "units": "MPH", "margin": MARGIN, "meter": "TYRES",
           "width": WINDOW[0], "height": WINDOW[1]}
_config_age = 0.0


def _read_config():
    """config.ini beside the app, re-read as it is edited so the panel can
    be changed without restarting the game. The setup app writes this file;
    editing it by hand does the same job.

    SCALE  0 follows the window, otherwise the baked set to draw from
    UNITS  MPH or KMH
    METER  what the ring reads: TYRES, TEMP, PRESSURE, DAMAGE, FUEL,
           or TURBO
    MARGIN extra panel pixels in from each edge
    """
    path = os.path.join(HERE, "config.ini")
    try:
        handle = open(path, "r")
    except Exception:
        return
    try:
        for line in handle:
            line = line.split(";")[0].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().upper()
            value = value.strip()
            if key == "SCALE":
                try:
                    _config["scale"] = max(0, min(12, int(value)))
                except ValueError:
                    pass
            elif key == "UNITS":
                _config["units"] = "KMH" if value.upper().startswith("K") \
                    else "MPH"
            elif key == "METER":
                if value.upper() in METERS:
                    _config["meter"] = value.upper()
            elif key == "MARGIN":
                try:
                    _config["margin"] = max(0, int(value))
                except ValueError:
                    pass
            elif key in ("WIDTH", "HEIGHT"):
                try:
                    _config[key.lower()] = max(64, int(value))
                except ValueError:
                    pass
    finally:
        handle.close()


# The sprites are not uniform -- the chrome 1 is 14 panel pixels wide against
# 21 for the rest, the speed 1 is 7 against 12, and the mini font runs 3 to 7
# -- so every size comes out of the sizes.txt the baker writes beside the
# art. Drawing them all at one width stretches them.
_sizes = {}      # baked scale -> {texture name: (w, h) in screen pixels}
_chars = {}      # character code -> font block
_space = 4       # what prt_letter advances for an unmapped character
_scales = []     # the scales tex/ actually holds, smallest first

_tex = {}
_state = {}
_window = None
_scale = 1
_size = WINDOW
_asked_size = [WINDOW]   # the last size asked for, so a drag is not fought


def _clear_window():
    """Background and border off, per the AC Python documentation:

      ac.drawBackground(CONTROL, 0)  -- 0 (transparent) or 1 (visible)
      ac.drawBorder(CONTROL, 0)      -- 0 (no border) or 1 (draw border)
      ac.setBackgroundOpacity(CONTROL, 0..1)

    Called every frame, from the render callback. The documentation does not
    say these need repeating, but in the game they do: set once at startup
    the background is back by the next frame and the window covers the road.
    (ac_dashboard.py sets its own opacity inside render_app for the same
    reason.) Evidence from the running game beats the manual here.

    The title and the icon go too: the title is emptied and the icon is put
    far outside the window, which is the only lever the API gives for either
    (setIconPosition places the icon inside the app; there is no hide call).
    That leaves nothing to drag the window by -- WIDTH/HEIGHT in config.ini
    move and resize it instead, re-read while the game runs.
    """
    ac.drawBackground(_window, 0)
    ac.drawBorder(_window, 0)
    ac.setBackgroundOpacity(_window, 0.0)
    ac.setTitle(_window, "")
    ac.setIconPosition(_window, 0, -10000)


def _log(msg):
    ac.log("%s: %s" % (APP_NAME, msg))
    ac.console("%s: %s" % (APP_NAME, msg))


def _texture(name):
    """One texture out of the current scale's folder, loaded once. Missing
    art draws nothing rather than taking the app down."""
    key = "%d/%s" % (_scale, name)
    if key not in _tex:
        path = os.path.join(TEX, "x%d" % _scale, name + ".png")
        if os.path.exists(path):
            _tex[key] = ac.newTexture(path)
        else:
            _tex[key] = -1
            _log("missing texture %s" % path)
    return _tex[key]


def _size_of(name):
    return _sizes.get(_scale, {}).get(name)


def _find_scales():
    """Which baked sets tex/ holds. Each is a folder of art enlarged to one
    size, and the HUD draws from one of them: that is what lets the size be
    changed in the game without handing a texture to AC's filtering."""
    found = []
    try:
        for entry in os.listdir(TEX):
            if not entry.startswith("x"):
                continue
            try:
                scale = int(entry[1:])
            except ValueError:
                continue
            if os.path.exists(os.path.join(TEX, entry, "sizes.txt")):
                found.append(scale)
    except Exception:
        pass
    found.sort()
    return found


def _load_tables(scale):
    """Sprite sizes and the character table, both written by the baker."""
    if scale in _sizes:
        return
    sizes = {}
    try:
        handle = open(os.path.join(TEX, "x%d" % scale, "sizes.txt"), "r")
        try:
            for line in handle:
                parts = line.split()
                if len(parts) == 3 and parts[0] != "#":
                    sizes[parts[0]] = (int(parts[1]), int(parts[2]))
        finally:
            handle.close()
    except Exception:
        _log("no sizes.txt for scale %d -- run tools/bake.py" % scale)
    _sizes[scale] = sizes

    if _chars:
        return
    global _space
    try:
        handle = open(os.path.join(TEX, "x%d" % scale, "charmap.txt"), "r")
        try:
            for line in handle:
                parts = line.split()
                if len(parts) != 2:
                    continue
                if parts[0] == "space":
                    _space = int(parts[1])
                else:
                    _chars[int(parts[0])] = int(parts[1])
        finally:
            handle.close()
    except Exception:
        _log("no charmap.txt for scale %d -- run tools/bake.py" % scale)


def _pick_scale(height):
    """The baked set to draw from: the one asked for in config.ini, or the
    one that suits the window if it asks for nothing. The art is 320x200-era,
    so a 1080p window wants about trebling. Only whole numbers exist, which
    is the point -- a half-scaled sprite is a blurred sprite."""
    if not _scales:
        return 1
    want = _config["scale"] or max(1, int(round(height / 360.0)))
    best = _scales[0]
    for scale in _scales:
        if abs(scale - want) < abs(best - want):
            best = scale
    return best


def _blit(name, x, y):
    """One sprite, drawn at exactly the size it was baked at.

    AC gives no way to turn texture filtering off, so the only thing that
    keeps the art hard-edged is handing it a quad the same size as the
    texture: one texel to one screen pixel, nothing to interpolate. The
    enlarging happens in tools/bake.py, with nearest neighbour.
    """
    size = _size_of(name)
    tex = _texture(name)
    if tex < 0 or not size:
        return 0
    ac.glQuadTextured(x, y, size[0], size[1], tex)
    return size[0]


def _glyph(ch):
    """The font block for a character, or None for one the table skips."""
    block = _chars.get(ord(ch))
    if block is None and ch.isalpha():
        block = _chars.get(ord(ch.upper()))
    return block


def _text(s, x, y):
    """mini_prt_string: each glyph advances by its own width, and anything
    the table does not carry advances four and draws nothing."""
    for ch in s:
        block = _glyph(ch)
        if block is None:
            x += _space * _scale
            continue
        x += _blit("font_%02d" % block, x, y) or (_space * _scale)
    return x


def _text_width(s):
    total = 0
    for ch in s:
        block = _glyph(ch)
        if block is None:
            total += _space * _scale
        else:
            size = _size_of("font_%02d" % block)
            total += size[0] if size else _space * _scale
    return total


def _text_right(s, x, y):
    """mini_prt_right: the string ends at x instead of starting there."""
    return _text(s, x - _text_width(s), y)


def _number(s, x, y, big=False):
    """A run of digit sprites, overlapped a pixel the way the panel kerns
    them [iTotalDigitWidth in func2.c]."""
    prefix = "big" if big else "speed"
    for ch in s:
        if ch.isdigit():
            name = "%s_%s" % (prefix, ch)
            size = _size_of(name)
            _blit(name, x, y)
            x += (size[0] - _scale) if size else 0
    return x


def _number_width(s, big=False):
    """In panel pixels, the unit the layout above is written in."""
    prefix = "big" if big else "speed"
    total = 0
    for ch in s:
        if ch.isdigit():
            size = _size_of("%s_%s" % (prefix, ch))
            total += (size[0] // _scale - 1) if size else 0
    return total


def _clock(seconds):
    """MM:SS:hh, the shape Whiplash prints its times in."""
    if not seconds or seconds <= 0:
        return "--:--:--"
    total = int(seconds * 100.0)
    return "%02d:%02d:%02d" % (total // 6000, (total // 100) % 60, total % 100)


def _ordinal(place):
    """1ST, 2ND, 3RD, 4TH -- what print_pos prints beside a driver's name."""
    if 10 <= place % 100 <= 20:
        return "%dTH" % place
    return "%d%s" % (place, {1: "ST", 2: "ND", 3: "RD"}.get(place % 10, "TH"))


# --- the ring ------------------------------------------------------------

def _meter():
    """Whatever the ring has been pointed at, as one 0..1 fraction: 0 leaves
    it grey, 1 colours every zone. Each source fills as things get worse,
    which is the direction Whiplash's damage meter ran."""
    if info is None:
        return None
    source = _config["meter"]
    try:
        if source == "TYRES":
            wear = [float(w) for w in info.physics.tyreWear]
            _log_once("tyreWear", wear)
            span = WEAR_FRESH - WEAR_DEAD
            if not wear or not span:
                return None
            return (WEAR_FRESH - min(wear)) / span
        if source == "TEMP":
            temps = [float(t) for t in info.physics.tyreCoreTemperature]
            _log_once("tyreCoreTemperature", temps)
            if not temps:
                return None
            _log_peak(max(temps))
            return _temp_fill(max(temps))
        if source == "PRESSURE":
            psi = [float(p) for p in info.physics.wheelsPressure]
            if not psi:
                return None
            ideal = _tyres.pick(getattr(info.graphics, "tyreCompound", ""))
            _log_once("wheelsPressure", (psi, "ideal %.2f" % ideal))
            worst = max(psi, key=lambda p: abs(p - ideal))
            return _pressure_fill(worst, ideal)
        if source == "DAMAGE":
            damage = [float(d) for d in info.physics.carDamage]
            _log_once("carDamage", damage)
            if not damage or not DAMAGE_FULL:
                return None
            return max(damage) / DAMAGE_FULL
        if source == "FUEL":
            full = float(info.static.maxFuel)
            _log_once("fuel", (float(info.physics.fuel), full))
            return (1.0 - float(info.physics.fuel) / full) if full > 0 else None
        if source == "TURBO":
            full = float(info.static.maxTurboBoost)
            _log_once("turboBoost", (float(info.physics.turboBoost), full))
            return (float(info.physics.turboBoost) / full) if full > 0 else None
    except Exception:
        _log(traceback.format_exc())
    return None


def _ramp(value, low, high, at_low, at_high):
    """`value` across `low`..`high`, as a fill between two stops."""
    if high <= low:
        return at_low
    return at_low + (value - low) / (high - low) * (at_high - at_low)


def _temp_fill(temp):
    """Tyre temperature onto the ring, bent so its colours mean something.

    Three straight runs joined at the band edges: empty to the top of the
    green by TEMP_GOOD, through the amber by TEMP_WARM, and into the red
    from there. So a tyre in its window shows green however wide that window
    is, and only overheating gets near the top.
    """
    green = float(GREEN_TOP) / RING_LEVELS
    amber = float(AMBER_TOP) / RING_LEVELS
    if temp <= TEMP_COLD:
        return 0.0
    if temp <= TEMP_GOOD:
        return _ramp(temp, TEMP_COLD, TEMP_GOOD, 0.0, green)
    if temp <= TEMP_WARM:
        return _ramp(temp, TEMP_GOOD, TEMP_WARM, green, amber)
    return _ramp(temp, TEMP_WARM, TEMP_HOT, amber, 1.0)


def _log_peak(temp):
    """The hottest the tyres have got, each time that climbs another ten
    degrees. The reading logged at startup is a cold tyre, which says
    nothing about where this car's working window actually sits -- these
    lines are what the stops above can be set from.
    """
    step = int(temp // 10) * 10
    if step > _state.get("peak_temp", 0):
        _state["peak_temp"] = step
        _log("tyres reached %.0f C -- ring at %d of %d zones"
             % (temp, int(round(_temp_fill(temp) * RING_LEVELS)), RING_LEVELS))


def _log_once(what, values):
    """The raw numbers behind a source, once, so its ends can be pinned from
    a real session instead of assumed."""
    seen = _state.setdefault("logged", {})
    if what not in seen:
        seen[what] = True
        _log("%s reads %s" % (what, values))


# --- the car's own tyre data ---------------------------------------------

class TyreData(object):
    """The ideal pressure for what is fitted, out of the car's tyres.ini.

    `content/cars/<car>/data/tyres.ini` holds a section per compound with a
    NAME and a PRESSURE_IDEAL, so the one matching `tyreCompound` is the
    car's answer. As with map.ini the key is picked by name out of whatever
    the file holds rather than assumed, and if nothing recognisable is there
    the log says what was.

    Most Kunos cars ship that folder packed into `data.acd` instead. That is
    obfuscated and this does not touch it: the ring falls back to
    PRESSURE_IDEAL and says so, so a car with unpacked data gets its own
    number and the rest get a sensible one.
    """

    def __init__(self):
        self.ideal = PRESSURE_IDEAL
        self.ok = False
        self.sections = {}

    def load(self, car):
        if not car:
            return
        root = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        path = os.path.join(root, "content", "cars", car, "data", "tyres.ini")
        if not os.path.exists(path):
            _log("no tyres.ini at %s (packed in data.acd?) -- pressure reads "
                 "against %.1f" % (path, PRESSURE_IDEAL))
            return
        section = ""
        try:
            handle = open(path, "r")
            try:
                for line in handle:
                    line = line.split(";")[0].strip()
                    if line.startswith("[") and line.endswith("]"):
                        section = line[1:-1].upper()
                    elif "=" in line and section:
                        key, value = line.split("=", 1)
                        self.sections.setdefault(section, {})[
                            key.strip().upper()] = value.strip()
            finally:
                handle.close()
        except Exception:
            _log(traceback.format_exc())
            return

        found = [(name, body) for name, body in self.sections.items()
                 if any("PRESSURE_IDEAL" in key for key in body)]
        if not found:
            _log("tyres.ini has no PRESSURE_IDEAL; its sections are: %s"
                 % ", ".join(sorted(self.sections)))
            return
        self.ok = True
        self.pick("")      # a sensible default until a compound is known

    def pick(self, compound):
        """The fitted compound's ideal, or the first front tyre's."""
        if not self.ok:
            return self.ideal

        def ideal_of(body):
            for key in body:
                if "PRESSURE_IDEAL" in key:
                    try:
                        return float(body[key])
                    except ValueError:
                        return None
            return None

        best = None
        for name in sorted(self.sections):
            body = self.sections[name]
            value = ideal_of(body)
            if value is None:
                continue
            if best is None and name.startswith("FRONT"):
                best = value
            if compound and body.get("NAME", "").strip().lower() \
                    == compound.strip().lower():
                best = value
                break
        if best is not None:
            self.ideal = best
        return self.ideal


_tyres = TyreData()


def _pressure_fill(psi, ideal):
    """How far from ideal, either way, onto the ring's colour bands."""
    green = float(GREEN_TOP) / RING_LEVELS
    amber = float(AMBER_TOP) / RING_LEVELS
    off = abs(psi - ideal)
    if off <= PRESSURE_GOOD:
        return green
    if off <= PRESSURE_WARN:
        return _ramp(off, PRESSURE_GOOD, PRESSURE_WARN, green, amber)
    return min(1.0, _ramp(off, PRESSURE_WARN, PRESSURE_BAD, amber, 1.0))


# --- the track map -------------------------------------------------------

class TrackMap(object):
    """AC ships a map.png per track and a data/map.ini saying where the world
    sits on it: pixel = (world + OFFSET) / SCALE_FACTOR.

    The key names are read out of the file rather than assumed. If the ones
    holding the offsets and the scale are not recognised, the map draws
    without car blips and the log says what the file did contain.
    """

    def __init__(self):
        self.texture = -1
        self.ok = False
        self.x_offset = 0.0
        self.z_offset = 0.0
        self.scale = 1.0
        self.width = 0.0
        self.height = 0.0

    def load(self, track, config):
        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(HERE))), "content", "tracks", track)
        if config:
            root = os.path.join(root, config)
        png = os.path.join(root, "map.png")
        ini = os.path.join(root, "data", "map.ini")
        if not os.path.exists(png):
            _log("no map.png at %s" % png)
            return
        self.texture = ac.newTexture(png)

        values = {}
        try:
            handle = open(ini, "r")
        except Exception:
            _log("no map.ini at %s -- map drawn without car positions" % ini)
            return
        try:
            for line in handle:
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("["):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    try:
                        values[key.strip().upper()] = float(val.split(";")[0])
                    except ValueError:
                        pass
        finally:
            handle.close()

        def pick(*wanted):
            for key in values:
                for want in wanted:
                    if want in key:
                        return values[key]
            return None

        x_off = pick("X_OFFSET")
        z_off = pick("Z_OFFSET")
        scale = pick("SCALE_FACTOR", "SCALE")
        self.width = pick("WIDTH") or 0.0
        self.height = pick("HEIGHT") or 0.0
        if x_off is None or z_off is None or not scale:
            _log("map.ini has no offset/scale I recognise; it holds: %s"
                 % ", ".join(sorted(values)))
            return
        self.x_offset, self.z_offset, self.scale = x_off, z_off, scale
        self.ok = True

    def project(self, world_x, world_z, box):
        """World metres to a pixel inside the panel's map box."""
        if not self.ok or not self.width or not self.height:
            return None
        px = (world_x + self.x_offset) / self.scale
        pz = (world_z + self.z_offset) / self.scale
        x, y, w, h = box
        return (x + px / self.width * w, y + pz / self.height * h)


_map = TrackMap()


# --- the app -------------------------------------------------------------

def acMain(version):
    global _window, _scale, _scales
    try:
        _log("build %s starting, running from %s" % (BUILD, HERE))
        _window = ac.newApp(APP_NAME)
        ac.setSize(_window, _config["width"], _config["height"])

        ac.addRenderCallback(_window, onRender)
        _clear_window()

        _state.update({"rpm": 0.0, "speed": 0.0, "gear": 0, "ring": 0,
                       "lap": 1, "pos": 1, "time": 0.0, "best": 0.0,
                       "infront": None, "behind": None, "cars": [],
                       "ahead_name": "", "behind_name": "",
                       "ahead_idx": -1, "behind_idx": -1, "logged": {}})
        _read_config()
        _scales = _find_scales()
        if not _scales:
            _log("no art in %s -- run tools/bake.py" % TEX)
        else:
            _log("art baked at %s" % ", ".join("%dx" % s for s in _scales))
        _scale = _pick_scale(_config["height"])
        _load_tables(_scale)
        _map.load(ac.getTrackName(0), ac.getTrackConfiguration(0))
        _tyres.load(info.static.carModel if info is not None else "")
        if info is None:
            _log("shared memory unavailable -- the ring will stay grey")
        return APP_NAME
    except Exception:
        _log(traceback.format_exc())
        return APP_NAME


def acUpdate(deltaT):
    global _scale, _size
    try:
        global _config_age
        _config_age += deltaT
        if _config_age >= CONFIG_POLL:
            _config_age = 0.0
            _read_config()

        # The panel anchors to the corners of this window, so the window
        # wants to be the size of the screen. With the title bar hidden
        # there is nothing to drag it by, so WIDTH/HEIGHT in config.ini --
        # the setup app's SCREEN row -- are what move it.
        size = ac.getSize(_window)
        if size and len(size) >= 2 and size[1] > 0:
            _size = (int(size[0]), int(size[1]))
            want = (_config["width"], _config["height"])
            if want != _asked_size[0]:
                _asked_size[0] = want
                ac.setSize(_window, want[0], want[1])
                _size = want
                _state["check_size"] = want
            elif _state.get("check_size"):
                # A frame after asking: did the window actually take it?
                # If AC clamped or ignored the size the panel anchors to
                # the wrong corners, and that is worth saying out loud
                # rather than looking like the HUD cannot count.
                asked = _state.pop("check_size")
                if _size != asked:
                    _log("asked for a %dx%d window, AC made it %dx%d"
                         % (asked[0], asked[1], _size[0], _size[1]))

        # Switching baked sets is how the HUD changes size: each set is art
        # enlarged to one scale and drawn at exactly that size.
        want_scale = _pick_scale(_size[1])
        if want_scale != _scale:
            _load_tables(want_scale)
            _scale = want_scale
            _log("drawing at %dx" % _scale)

        # Revs stretch to the car's own redline, so the arc always fills and
        # the shift point is always the top of it. That makes the 40-90
        # painted round the dial decoration rather than a scale -- no AC car
        # has Whiplash's rev range.
        rpm = ac.getCarState(0, acsys.CS.RPM)
        maxrpm = float(info.static.maxRpm) if info is not None else 0.0
        _state["rpm"] = (rpm / maxrpm) if maxrpm > 0 else 0.0

        _state["speed"] = ac.getCarState(
            0, acsys.CS.SpeedKMH if _config["units"] == "KMH"
            else acsys.CS.SpeedMPH)
        _state["gear"] = ac.getCarState(0, acsys.CS.Gear) - 1
        _state["lap"] = ac.getCarState(0, acsys.CS.LapCount) + 1
        _state["time"] = ac.getCarState(0, acsys.CS.LapTime) / 1000.0
        _state["best"] = ac.getCarState(0, acsys.CS.BestLap) / 1000.0
        # Our place, and the cars either side of us, all out of one order --
        # so the number on the plate and the two names on its bars can never
        # disagree. INFRONT/BEHIND are the splits to those same two.
        order = _standings()
        _state["pos"], _state["ahead_idx"], _state["behind_idx"] = \
            _place_in(order)
        _state["ahead_name"] = _driver(_state["ahead_idx"])
        _state["behind_name"] = _driver(_state["behind_idx"])

        fill = _meter()
        _state["ring"] = 0 if fill is None else max(
            0, min(RING_LEVELS, int(round(fill * RING_LEVELS))))

        cars = []
        for i in order:
            at = ac.getCarState(i, acsys.CS.WorldPosition)
            spline = ac.getCarState(i, acsys.CS.NormalizedSplinePosition)
            if at:
                cars.append((i, at[0], at[2], spline))
        _state["cars"] = cars
        _state["infront"], _state["behind"] = _gaps(cars)
    except Exception:
        _log(traceback.format_exc())


def _standings():
    """Every car in the session, in the order they are in right now.

    The order comes from `getCarRealTimeLeaderboardPosition`, which the AC
    documentation calls the car's position "in real-time".
    `getCarLeaderboardPosition` is the official standing instead, and in a
    race that only settles as cars cross the line -- overtake someone
    mid-lap and the number does not move until the lap does. Whiplash's own
    byRacePosition is live, so this is the one that matches it.

    `getCarsCount` is the session's maximum number of cars, not how many are
    in it, so the empty slots go: left in, they sit in the order and push
    everyone below them down a place. If that filter leaves us out of our
    own session it is telling us nothing, so then nothing is filtered.
    """
    count = ac.getCarsCount()
    cars = [car for car in range(count) if ac.isConnected(car)]
    if 0 not in cars:
        cars = list(range(count))

    field = []
    for car in cars:
        place = ac.getCarRealTimeLeaderboardPosition(car)
        if place is None or place < 0:
            place = ac.getCarLeaderboardPosition(car)
        field.append((place, car))
    field.sort()
    return [car for _place, car in field]


def _place_in(order):
    """Our place, and the cars either side of us, read off the order itself.

    Counting along the order rather than trusting the number AC hands back
    means it does not matter whether AC counts positions from 0 or from 1:
    first in the list is first, and the entries either side are the car we
    are chasing and the one chasing us.
    """
    try:
        at = order.index(0)
    except ValueError:
        return 1, -1, -1
    ahead = order[at - 1] if at > 0 else -1
    behind = order[at + 1] if at + 1 < len(order) else -1
    return at + 1, ahead, behind


def _driver(car):
    return (ac.getDriverName(car) or "") if car >= 0 else ""


def _gaps(cars):
    """Time to the car ahead of us and the car behind us in the standings.

    AC hands out positions on the track, not gaps, so this is a lap time
    times the distance round the lap between us and that car: right on a
    steady lap and optimistic under braking, which is what a gap readout
    always is.
    """
    spline = {}
    for idx, _wx, _wz, at in cars:
        spline[idx] = at
    mine = spline.get(0)
    lap = _state.get("best") or _state.get("time") or 0.0
    if mine is None or lap <= 0:
        return None, None

    def gap_to(idx):
        at = spline.get(idx)
        if idx < 0 or at is None:
            return None
        delta = at - mine
        if delta > 0.5:
            delta -= 1.0
        elif delta < -0.5:
            delta += 1.0
        return abs(delta) * lap

    return gap_to(_state["ahead_idx"]), gap_to(_state["behind_idx"])


def onRender(deltaT):
    try:
        # Every frame, before anything else: AC has just put its own window
        # background back, and it has to go again or it covers the screen.
        _clear_window()
        ac.glColor4f(1.0, 1.0, 1.0, 1.0)
        width, height = _size
        s = _scale
        m = _config["margin"] * s
        left, top = m, m
        right, bottom = width - m, height - m

        # --- bottom right: the gauge. Its tick numbers, x1000rpm, MAX, min
        # and GEAR are painted into the sprite, so all that changes here is
        # which arc steps are lit and how much of the ring has coloured up.
        dial_x = right + DIAL_X * s
        dial_y = bottom - (DIAL_H + DIAL_BOTTOM) * s
        step = int(round(max(0.0, min(1.0, _state["rpm"])) * REV_STEPS))
        _blit("rev_%02d" % step, dial_x, dial_y)
        _blit("dam_%02d" % _state["ring"], dial_x, dial_y)

        _number("%d" % max(0, int(_state["speed"])),
                dial_x + SPEED_X * s, dial_y + SPEED_Y * s)
        _blit(_config["units"].lower(),
              dial_x + UNIT_X * s, dial_y + UNIT_Y * s)

        gear = _state["gear"]
        name = "R" if gear < 0 else ("N" if gear == 0 else "%d" % min(gear, 6))
        _blit("gear_%s" % name, dial_x + GEAR_X * s, dial_y + GEAR_Y * s)

        # --- top left: the position plate, with the cars either side of us
        # printed on its own two bars [print_pos, func2.c].
        _blit("pos", left + POS_X * s, top + POS_Y * s)
        place = max(1, min(99, _state["pos"]))
        number = "%d" % place
        _number(number,
                left + (POS_NUM_CX - _number_width(number, True) // 2) * s,
                top + POS_NUM_Y * s, big=True)
        if _state["ahead_name"]:
            _text(_ordinal(place - 1), left + NAME_X * s, top + AHEAD_Y * s)
            _text_right(_state["ahead_name"][:12],
                        left + NAME_RIGHT * s, top + AHEAD_Y * s)
        if _state["behind_name"]:
            _text(_ordinal(place + 1), left + NAME_X * s, top + BEHIND_Y * s)
            _text_right(_state["behind_name"][:12],
                        left + NAME_RIGHT * s, top + BEHIND_Y * s)

        # --- top right: the lap plate. The bar goes down first, then the
        # number on it, then the LAP tag over the top of both -- which is
        # the order func2.c draws them in, and the reason the tag is legible
        # where it crosses the bar.
        _blit("bar", right + LAP_BAR_X * s, top + LAP_BAR_Y * s)
        lap = "%d" % max(1, min(99, _state["lap"]))
        _number(lap,
                right + (LAP_NUM_CX - _number_width(lap, True) // 2) * s,
                top + LAP_NUM_Y * s, big=True)
        _blit("lap", right + LAP_X * s, top + LAP_Y * s)

        # --- top centre: the clock
        rows = [("TIME:", _state["time"]), ("BEST:", _state["best"]),
                ("INFRONT:", _state["infront"]),
                ("BEHIND:", _state["behind"])]
        middle = width // 2
        y = top + CLOCK_Y * s
        for label, value in rows:
            _text_right(label, middle - CLOCK_PAD * s, y)
            _text(_clock(value), middle, y)
            y += CLOCK_ROW * s

        # --- bottom left: the map, with everyone on it
        mw, mh = MAP_W * s, MAP_H * s
        mx, my = left, bottom - mh
        if _map.texture >= 0:
            ac.glQuadTextured(mx, my, mw, mh, _map.texture)
            mine = None
            for idx, wx, wz, _spline in _state["cars"]:
                at = _map.project(wx, wz, (mx, my, mw, mh))
                if at is None:
                    continue
                if idx == 0:
                    mine = at
                else:
                    ac.glColor4f(0.55, 0.55, 0.55, 1.0)
                    ac.glQuad(at[0], at[1], 2 * s, 2 * s)
            if mine is not None:
                ac.glColor4f(0.2, 0.4, 1.0, 1.0)
                ac.glQuad(mine[0], mine[1], 3 * s, 3 * s)
            ac.glColor4f(1.0, 1.0, 1.0, 1.0)
    except Exception:
        _log(traceback.format_exc())


def acShutdown():
    pass
