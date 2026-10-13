# Whiplash HUD for Assetto Corsa

Fatal Racing's dashboard, over AC. The gauge is the retail one: a single
79x70 sprite whose palette indices encode two instruments at once — indices
1..48 are the rev arc's steps, indices >= 0x31 are the ring's thirteen zones
— exactly as `print_damage` in ROLLER's `func2.c` reads it. Everything is
placed where `test_panel()` in the same file places it.

The art is retail game data, so none of it is in this repository and none of
it ever will be: `tools/bake.py` reads your own copy of Whiplash's FATDATA
and writes the textures beside the app, where `.gitignore` keeps them. What
is here is the code that reads the format and the index numbers it reads it
by.

The layout and the sprite format both come from
[ROLLER](https://github.com/FatalDecomp/ROLLER), the C reimplementation of
Whiplash; `func2.c` is cited throughout, and it is the authority for every
offset in this project.

Two apps:

| app | what it is |
| --- | --- |
| **Whiplash HUD** | the overlay. No window furniture, nothing to click. |
| **Whiplash HUD Setup** | an ordinary AC window with the knobs on it. |

> **Installing it?** [INSTALL.md](INSTALL.md) is the step-by-step guide,
> in Finnish and then English. What follows here is the short version.

## Install

1. Bake the art from your FATDATA:

   ```
   python3 tools/bake.py /path/to/FATDATA apps/python/whiplash_hud/tex 2 3 4 6
   ```

   The numbers at the end select the scales of HUD to generate. Each one is
   baked into its own folder — `tex/x2`, `tex/x3` and so on — and the HUD
   draws from one of them. 3 or 4 for 1080p, 6 or 8 for 4K screen.

   The art is enlarged here, with nearest neighbour, because AC has no way
   to turn texture filtering off for hud elements: the app then draws every sprite at exactly
   its own size, one texel to one screen pixel, and nothing gets
   interpolated. That is also why the size is changed by switching folders
   rather than by scaling a texture — scaling the hud ingame softens the image. Four scales is 145 PNGs each, about 2.5 MB in total.

2. Copy **both** `apps/python/whiplash_hud/` and
   `apps/python/whiplash_setup/` into your AC install's `apps/python/`
   folder. The setup app looks for the HUD beside itself.

3. Enable **Whiplash HUD** and **Whiplash HUD Setup** in AC's app bar.

## What it shows

| corner | reading |
| --- | --- |
| top left | the position plate: the car ahead, your position, the car behind |
| top centre | TIME, BEST, INFRONT, BEHIND |
| top right | the lap plate |
| bottom left | the track's own map.png, with every car on it |
| bottom right | the gauge: revs, the ring, speed, gear |

**The position plate** is `PANEL2.BM` block 21, the game's own: two black
bars with the POS legend between them. The names of the cars either side of
you in the standings are printed onto those bars, with their places beside
them, which is what `print_pos` does — not your own name, and not whoever
happens to be nearest on track. **INFRONT** and **BEHIND** are the splits to
those same two cars.

**Revs** stretch to the car's redline, so the arc always fills and the shift
point is always the top of it. The 40–90 painted around the dial is therefore
decoration — no AC car has Whiplash's rev range.

**The ring** was Whiplash's damage meter: thirteen zones that colour up as
the car gets worse. AC's damage is rarely enabled, so it can be pointed at
something else from the setup app:

| setting | what fills the ring |
| --- | --- |
| `TYRES` | tyre life, across the worst tyre's whole life |
| `DAMAGE` | AC's own `carDamage`, the worst of its five zones |
| `FUEL` | fuel used, so a full ring is an empty tank |
| `TURBO` | boost, as a fraction of the car's maximum |

**The skull** in `PANCAR1.BM` is Whiplash's kill counter and has no meaning
in AC, so it is not drawn.

## Moving things

The panel's layout lives in one commented block at the top of
`apps/python/whiplash_hud/whiplash_hud.py`, under `THE LAYOUT`. Every number
in it is in panel pixels and gets multiplied by the scale, and every one of
them is `func2.c`'s own, with the screen-edge arithmetic already resolved.
The ones most likely to want nudging:

| constant | what it moves |
| --- | --- |
| `SPEED_X`, `SPEED_Y` | the speed digits, from the dial's top-left corner |
| `GEAR_X`, `GEAR_Y` | the gear letter in its black slot |
| `UNIT_X`, `UNIT_Y` | the mph/kmh tag |
| `DIAL_X`, `DIAL_BOTTOM` | the whole gauge, against the bottom right |
| `POS_*`, `AHEAD_Y`, `BEHIND_Y`, `NAME_*` | the position plate |
| `LAP_*` | the lap plate |
| `CLOCK_Y`, `CLOCK_ROW` | the timing column |

`tools/preview.py` draws the same layout from the same constants without
starting the game, so a change can be looked at in a second.

## The setup app

Four rows, each written straight into the HUD's `config.ini`, which the HUD
re-reads twice a second — so every change lands while you are driving.

| row | does |
| --- | --- |
| `SCREEN` | the HUD window's size: set this to your display's resolution |
| `SIZE` | steps through the scales you baked, or AUTO to suit the window |
| `RING` | TYRE LIFE / DAMAGE / FUEL USED / TURBO |
| `SPEED` | MPH or KMH — Whiplash has art for both |

**SCREEN is the one that matters first.** The panel anchors to the corners
of the HUD's own window, so until that window is the size of your display,
the whole panel sits in a box in one corner of the screen. With the title
bar hidden there is nothing to drag it by, which is why it is a setting.

There is no "fit automatically": AC's Python API has no call that reports
the screen size — there is nothing about the display anywhere in it. The
setup app does read AC's own `cfg/video.ini` and add whatever that says to
the list, and the log line says whether it found it.

With `SIZE` on AUTO the art then follows: a 1080p window draws at 3x, a 4K
one at 6x.

`config.ini` is a plain file and can be edited by hand instead; it also
holds `MARGIN` for extra inset.

## The HUD window

Its background and border are turned off, and its title and icon are pushed
out of the way, every frame from the render callback:

    ac.drawBackground(CONTROL, 0)   0 transparent, 1 visible
    ac.drawBorder(CONTROL, 0)       0 no border, 1 draw border
    ac.setBackgroundOpacity(CONTROL, 0.0)

The documentation does not say these need repeating. In the game they do:
set once at startup, the background is back by the next frame. That leaves
nothing to drag the window by, which is what `WIDTH`/`HEIGHT` are for.

## Looking at it without AC

```
python3 tools/preview.py /path/to/FATDATA out.png 2560x1080 auto 0.78 6 192 4 7 1
```

Arguments after the size are scale (or `auto`), revs 0..1, ring 0..13, speed,
gear, lap, position. The preview draws on mid grey on purpose: over the game
index 0 is see-through and index 112 — which the art outlines with — is
black, so on a black test ground both vanish and the panel looks full of
holes.

```
python3 tools/dryrun.py
```

runs both apps against a fake `ac` module: every entry point, every button
clicked once, and a report of what the window was told. An exception
part-way through `acMain` or `onRender` shows up in AC as a window that
ignores everything the app asked for, because the calls after it never
happened — this is what catches that before the game does.

## Still to settle

- `map.ini` key names. The projection is `pixel = (world + OFFSET) / SCALE`,
  and the parser picks the keys by name out of whatever the file holds; one
  real `data/map.ini` would let it be pinned rather than sniffed.
- `WEAR_FRESH` / `WEAR_DEAD` / `DAMAGE_FULL`. The app logs the raw values
  behind each ring source the first time it reads one; set the constants
  from those lines.
- `TURBO` fills as a fraction of the car's own `maxTurboBoost`, which needs
  no unit. A readout in psi would need AC's unit for `turboBoost` pinned
  first.
- The timing column is in the mini font. Whiplash prints it in `FONT6.BM`,
  with its own character table, and `ShowATime` spaces the digits by hand
  (9 panel pixels apart, 3 for a colon). Baking that font would make the
  column retail-exact.
