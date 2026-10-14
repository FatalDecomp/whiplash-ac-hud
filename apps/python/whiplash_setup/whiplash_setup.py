"""Whiplash HUD Setup -- the knobs, in their own AC window.

The HUD has no controls of its own: it is a transparent overlay with its
title bar and icon pushed out of the way, so there is nothing on it to
click. This app is where its settings live. It writes the HUD's config.ini
and the HUD re-reads that twice a second, so every change lands while the
game is running.

Keep this app's window ordinary -- title bar, pin, the lot. It is a panel
you open, change something on, and close again.

Assetto Corsa runs Python 3.3, so nothing here uses anything newer.
"""

import os
import traceback

import ac

APP_NAME = "Whiplash HUD Setup"
BUILD = "2026-10-14 21:10"
HERE = os.path.dirname(os.path.abspath(__file__))
HUD = os.path.join(os.path.dirname(HERE), "whiplash_hud")
CONFIG = os.path.join(HUD, "config.ini")
TEX = os.path.join(HUD, "tex")

# The HUD's panel anchors to the corners of its own window, so the window
# has to be the size of the screen for the panel to sit in the screen's
# corners. AC's Python API has no call that reports the screen size -- there
# is nothing about the display anywhere in it -- so the size is picked from
# this list instead, with whatever AC's own video.ini says added to it.
SCREENS = [(1280, 720), (1366, 768), (1600, 900), (1920, 1080),
           (1920, 1200), (2560, 1080), (2560, 1440), (3440, 1440),
           (3840, 2160)]

METERS = ("TYRES", "TEMP", "DAMAGE", "FUEL", "TURBO")
METER_SAYS = {"TYRES": "TYRE LIFE", "TEMP": "TYRE TEMP",
              "DAMAGE": "DAMAGE", "FUEL": "FUEL USED", "TURBO": "TURBO"}
UNITS = ("MPH", "KMH")

# Laid out in a column: a caption, then the control it drives.
ROW = 32
PAD = 8

_window = None
_labels = {}
_scales = [1]
_screens = list(SCREENS)
_config = {"scale": 0, "units": "MPH", "meter": "TYRES", "margin": 0,
           "width": 800, "height": 450}


def _log(msg):
    ac.log("%s: %s" % (APP_NAME, msg))
    ac.console("%s: %s" % (APP_NAME, msg))


def _find_scales():
    """The sizes the art has actually been baked at. Changing the HUD's size
    means drawing from a different one of these folders -- it cannot be
    scaled in the game without AC's filtering softening it, which is the
    whole reason the art is enlarged at bake time."""
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
    return found or [1]


def _ac_screen():
    """What AC has itself been set to, if it can be found.

    Its video.ini lives beside the rest of the user's AC config. The keys
    are picked by name out of whatever the file holds rather than assumed,
    and anything unrecognised just means the list below is the picker --
    the log says which it was.
    """
    path = os.path.join(os.path.expanduser("~"), "Documents",
                        "Assetto Corsa", "cfg", "video.ini")
    if not os.path.exists(path):
        _log("no video.ini at %s -- pick the size from the list" % path)
        return None
    values = {}
    try:
        handle = open(path, "r")
        try:
            for line in handle:
                line = line.split(";")[0].strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    try:
                        values[key.strip().upper()] = int(value.strip())
                    except ValueError:
                        pass
        finally:
            handle.close()
    except Exception:
        _log(traceback.format_exc())
        return None

    def pick(want):
        for key in values:
            if key == want or key.endswith("_" + want):
                return values[key]
        return None

    width, height = pick("WIDTH"), pick("HEIGHT")
    if width and height:
        _log("video.ini says the game runs at %dx%d" % (width, height))
        return (width, height)
    _log("video.ini has no size I recognise; it holds: %s"
         % ", ".join(sorted(values)))
    return None


def _read():
    """Whatever the HUD is set to now."""
    try:
        handle = open(CONFIG, "r")
    except Exception:
        _log("no config.ini at %s -- writing a fresh one" % CONFIG)
        return
    try:
        for line in handle:
            line = line.split(";")[0].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip().upper(), value.strip()
            try:
                if key in ("SCALE", "MARGIN", "WIDTH", "HEIGHT"):
                    _config[key.lower()] = int(value)
                elif key == "UNITS":
                    _config["units"] = "KMH" if value.upper().startswith("K") \
                        else "MPH"
                elif key == "METER" and value.upper() in METERS:
                    _config["meter"] = value.upper()
            except ValueError:
                pass
    finally:
        handle.close()


TEMPLATE = """; Whiplash HUD. Written by the setup app, and re-read by the HUD twice a
; second, so anything changed here lands while the game is running.

[HUD]
; How much screen the HUD spreads across. The panel anchors to the corners
; of this window, so at full screen the clusters sit in the screen's own
; corners. Dragging the window works too -- the panel follows it.
WIDTH = %(width)d
HEIGHT = %(height)d

; Which baked set of art to draw from, in screen pixels per panel pixel.
; Only the sizes tools/bake.py has actually baked can be used, because each
; sprite is drawn at exactly the size it was baked at -- that is what keeps
; it hard-edged, AC having no way to turn texture filtering off. 0 picks one
; to suit the window.
SCALE = %(scale)d

; MPH or KMH. Whiplash has art for both.
UNITS = %(units)s

; What the ring round the dial reads: TYRES, TEMP, DAMAGE, FUEL or TURBO.
; It was Whiplash's damage meter -- thirteen zones that colour up as things get
; worse -- so whatever it is pointed at fills it the same way.
METER = %(meter)s

; Extra panel pixels in from each edge. The game's own insets are already in
; the layout, so 0 is Whiplash's placement exactly.
MARGIN = %(margin)d
"""


def _write():
    try:
        handle = open(CONFIG, "w")
        try:
            handle.write(TEMPLATE % _config)
        finally:
            handle.close()
    except Exception:
        _log(traceback.format_exc())


def _show():
    ac.setText(_labels["screen"], "%dx%d" % (_config["width"],
                                             _config["height"]))
    scale = _config["scale"]
    ac.setText(_labels["scale"], "%dx" % scale if scale else "AUTO")
    ac.setText(_labels["meter"], METER_SAYS[_config["meter"]])
    ac.setText(_labels["units"], _config["units"])


def _step_scale(step):
    """Along the baked sizes, with AUTO sitting below the smallest."""
    order = [0] + _scales
    try:
        at = order.index(_config["scale"])
    except ValueError:
        at = 0
    _config["scale"] = order[max(0, min(len(order) - 1, at + step))]
    _write()
    _show()


def _scale_down(*args):
    _step_scale(-1)


def _scale_up(*args):
    _step_scale(1)


def _step_screen(step):
    """Along the sizes the HUD window can be set to."""
    here = (_config["width"], _config["height"])
    at = _screens.index(here) if here in _screens else 0
    _config["width"], _config["height"] = \
        _screens[max(0, min(len(_screens) - 1, at + step))]
    _write()
    _show()


def _screen_down(*args):
    _step_screen(-1)


def _screen_up(*args):
    _step_screen(1)


def _next_meter(*args):
    _config["meter"] = METERS[(METERS.index(_config["meter"]) + 1)
                              % len(METERS)]
    _write()
    _show()


def _next_units(*args):
    _config["units"] = UNITS[(UNITS.index(_config["units"]) + 1) % len(UNITS)]
    _write()
    _show()


def _row(title, y, value_w=120):
    """A caption on the left and the thing it says on the right."""
    caption = ac.addLabel(_window, title)
    ac.setPosition(caption, PAD, y)
    ac.setFontSize(caption, 14)
    value = ac.addLabel(_window, "")
    ac.setPosition(value, PAD + 80, y)
    ac.setFontSize(value, 14)
    ac.setFontColor(value, 1.0, 0.8, 0.2, 1.0)
    return value


def _button(text, x, y, w, h, on_click):
    button = ac.addButton(_window, text)
    ac.setPosition(button, x, y)
    ac.setSize(button, w, h)
    ac.setFontSize(button, 14)
    ac.setFontAlignment(button, "center")
    ac.addOnClickedListener(button, on_click)
    return button


def acMain(version):
    global _window, _scales, _screens
    try:
        _log("build %s starting, HUD at %s" % (BUILD, HUD))
        _window = ac.newApp(APP_NAME)
        ac.setSize(_window, 270, 225)
        ac.setTitle(_window, "WHIPLASH HUD")

        _scales = _find_scales()
        _read()
        if _config["scale"] and _config["scale"] not in _scales:
            _log("config asks for %dx but the art is baked at %s"
                 % (_config["scale"],
                    ", ".join("%dx" % s for s in _scales)))

        # Whatever the game is set to belongs in the list, and the size
        # already in config.ini has to be in it or stepping starts from the
        # wrong place.
        for size in (_ac_screen(), (_config["width"], _config["height"])):
            if size and size not in _screens:
                _screens.append(size)
        _screens.sort()

        y = 36
        _labels["screen"] = _row("SCREEN", y)
        _button("-", 190, y - 4, 28, 24, _screen_down)
        _button("+", 224, y - 4, 28, 24, _screen_up)

        y += ROW
        _labels["scale"] = _row("SIZE", y)
        _button("-", 190, y - 4, 28, 24, _scale_down)
        _button("+", 224, y - 4, 28, 24, _scale_up)

        y += ROW
        _labels["meter"] = _row("RING", y)
        _button(">", 224, y - 4, 28, 24, _next_meter)

        y += ROW
        _labels["units"] = _row("SPEED", y)
        _button(">", 224, y - 4, 28, 24, _next_units)

        y += ROW + 6
        note = ac.addLabel(_window, "baked at %s"
                           % ", ".join("%dx" % s for s in _scales))
        ac.setPosition(note, PAD, y)
        ac.setFontSize(note, 12)
        ac.setFontColor(note, 0.6, 0.6, 0.6, 1.0)

        _show()
        return APP_NAME
    except Exception:
        _log(traceback.format_exc())
        return APP_NAME


def acUpdate(deltaT):
    pass


def acShutdown():
    pass
