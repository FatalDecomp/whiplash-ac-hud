"""Run an app's entry points against a fake AC, and report what it does.

Nothing here tests the game. What it catches is the thing that keeps biting:
an exception part-way through acMain or onRender, which in AC shows up as a
window that ignores everything the app asked for -- because the calls after
the exception never happened.

Every button the app registers is clicked once as well, so a listener that
throws is caught here rather than in the game.

Usage: dryrun.py [app dir ...]
"""

import os
import shutil
import sys
import types


class Recorder(object):
    """Stands in for the ac module, remembering every call."""

    def __init__(self):
        self.calls = []
        self.next_id = 1
        self.listeners = []     # (control id, function) in registration order

    def _record(self, name, args):
        self.calls.append((name, args))
        if name in ("addOnClickedListener", "addOnValueChangeListener") \
                and len(args) == 2:
            self.listeners.append(args)

    def __getattr__(self, name):
        def call(*args):
            self._record(name, args)
            if name.startswith("add") or name in ("newApp", "newTexture"):
                self.next_id += 1
                return self.next_id
            if name == "getSize":
                return (800, 450)
            if name == "getPosition":
                return (0, 0)
            if name == "getCarState":
                return 0.0
            if name == "getCarsCount":
                return 2
            if name == "getCarLeaderboardPosition":
                return 1
            if name in ("getDriverName", "getTrackName",
                        "getTrackConfiguration"):
                return "TEST"
            return 1
        return call

    def args_for(self, name):
        return [call[1] for call in self.calls if call[0] == name]


def fake_acsys():
    mod = types.ModuleType("acsys")

    class CS(object):
        pass

    for field in ("RPM", "SpeedKMH", "SpeedMPH", "Gear", "LapCount",
                  "LapTime", "BestLap", "WorldPosition",
                  "NormalizedSplinePosition"):
        setattr(CS, field, field)
    mod.CS = CS
    return mod


def fake_sim_info():
    mod = types.ModuleType("sim_info")

    class Physics(object):
        tyreWear = [100.0, 100.0, 100.0, 100.0]
        tyreCoreTemperature = [26.0, 26.0, 26.0, 26.0]
        carDamage = [0.0] * 5
        fuel = 40.0
        turboBoost = 0.4

    class Static(object):
        maxRpm = 8000
        maxFuel = 60.0
        maxTurboBoost = 1.2

    class Info(object):
        physics = Physics()
        static = Static()

    mod.info = Info()
    return mod


INTERESTING = ("newApp", "setSize", "drawBackground", "drawBorder",
               "setBackgroundOpacity", "setTitle", "setIconPosition",
               "addRenderCallback", "addButton", "addLabel",
               "glQuadTextured")


def run(app_dir):
    """One app, start to finish, reporting what the window was told."""
    name = os.path.basename(os.path.abspath(app_dir.rstrip("/\\")))
    print("=== %s" % name)
    ac = Recorder()
    sys.modules["ac"] = ac
    sys.modules["acsys"] = fake_acsys()
    sys.modules["sim_info"] = fake_sim_info()
    sys.path.insert(0, app_dir)
    for loaded in [m for m in sys.modules if m.startswith("whiplash_")]:
        del sys.modules[loaded]
    app = __import__(name)

    failures = []

    def step(what, call):
        before = len(ac.calls)
        try:
            call()
        except Exception as exc:
            failures.append("%s: %r" % (what, exc))
        return len(ac.calls) - before

    print("acMain made %d calls" % step("acMain", lambda: app.acMain("1.0")))
    if hasattr(app, "acUpdate"):
        print("acUpdate made %d calls"
              % step("acUpdate", lambda: app.acUpdate(0.016)))
    if hasattr(app, "onRender"):
        print("onRender made %d calls"
              % step("onRender", lambda: app.onRender(0.016)))

    # Every button, clicked once. AC hands its click listeners the cursor
    # position, so they are called the way the game calls them.
    for control, listener in list(ac.listeners):
        step("listener on control %s" % control, lambda f=listener: f(0, 0))
    if ac.listeners:
        print("clicked %d listeners" % len(ac.listeners))
    print()

    for call in INTERESTING:
        args = ac.args_for(call)
        if args:
            print("%-22s x%-4d %s" % (call, len(args), args[0]))
    print()

    for call in ac.calls:
        if call[0] == "log":
            print("LOG %s" % call[1][0])

    if failures:
        print()
        for failure in failures:
            print("RAISED %s" % failure)
    print()
    return not failures


def main(argv):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    apps = argv[1:] or [os.path.join(here, "apps", "python", "whiplash_hud"),
                        os.path.join(here, "apps", "python",
                                     "whiplash_setup")]
    # The setup app writes the HUD's config.ini, and clicking its buttons
    # here would leave the settings somewhere the user did not put them.
    config = os.path.join(here, "apps", "python", "whiplash_hud",
                          "config.ini")
    saved = config + ".dryrun"
    if os.path.exists(config):
        shutil.copyfile(config, saved)
    try:
        ok = True
        for app in apps:
            ok = run(app) and ok
    finally:
        if os.path.exists(saved):
            shutil.copyfile(saved, config)
            os.remove(saved)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
