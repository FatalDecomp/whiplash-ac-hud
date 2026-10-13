# How it works

Notes on the Python, for anyone changing it. [INSTALL.md](INSTALL.md) is the
guide for using it; this is the one for taking it apart.

Two apps, one shared file:

```
apps/python/whiplash_hud/     the overlay. No window furniture, nothing to click.
apps/python/whiplash_setup/   an ordinary AC window with the knobs on it.
apps/python/whiplash_hud/config.ini    what one writes and the other reads.
tools/                        the baker, an offline previewer, a fake AC.
```

---

## 1. What an Assetto Corsa app is

AC embeds **Python 3.3**. Nothing in this project may use anything newer —
no f-strings, no `pathlib`. It is why the code is all `%` formatting and
`os.path`.

A module in `apps/python/<name>/<name>.py` becomes an app when it defines:

| function | when AC calls it |
| --- | --- |
| `acMain(version)` | once, at load. Must return the app's name. |
| `acUpdate(deltaT)` | regularly, with seconds since the last call. |
| `acShutdown()` | at unload. |

Drawing is separate. `ac.glQuad`, `ac.glQuadTextured` and `ac.glColor4f` only
work inside a render callback, registered in `acMain`:

```python
ac.addRenderCallback(_window, onRender)
```

So `acUpdate` reads the car and stores it in `_state`, and `onRender` draws
`_state`. The two never swap jobs. `onRender` does no file I/O and asks AC
nothing — it is on the frame path.

**Every entry point is wrapped in `try/except` that logs the traceback.** An
uncaught exception part-way through `acMain` or `onRender` does not announce
itself in AC: the calls *after* it simply never happen, and what you see is a
window that ignores half of what the app asked for. That failure cost a lot
of time early on, so the traceback now always reaches the log.

`_log` writes to both:

```python
ac.log(msg)        # Documents\Assetto Corsa\logs\py_log.txt
ac.console(msg)    # the in-game console
```

`BUILD` is stamped at the top of each app and logged on startup, so the log
says which copy of the file is actually running. That is worth keeping: when
AC appears to ignore a change, the usual cause is that it is loading a
different copy.

---

## 2. The window

The HUD has to be an invisible rectangle, which AC does not really offer.
What works:

```python
def _clear_window():
    ac.drawBackground(_window, 0)
    ac.drawBorder(_window, 0)
    ac.setBackgroundOpacity(_window, 0.0)
    ac.setTitle(_window, "")
    ac.setIconPosition(_window, 0, -10000)
```

Two things about this are not in the documentation.

**It must run every frame, from the render callback.** The documentation
describes these as settings. In the running game they are not: set once in
`acMain`, the background is back by the next frame and the window covers the
road. AC repaints its own chrome per frame, so the app has to un-paint it per
frame. (`ac_dashboard.py`, a shipped example, sets its opacity inside its own
render callback for the same reason.)

**The title and icon have no hide call.** Emptying the title and putting the
icon at `y = -10000` is the whole of it — `ac.setIconPosition` places the icon
*inside* the app, so a large negative offset is the only way out.

The consequence is that the HUD window has nothing to drag, which is why its
size is a setting rather than a gesture, and why the setup app exists at all.

**There is no screen-size call anywhere in AC's Python API.** The panel
anchors to the corners of its own window, so the window has to be told how
big the screen is. `WIDTH`/`HEIGHT` in `config.ini` do that; the setup app's
SCREEN row writes them, and also reads AC's own `cfg/video.ini` so the real
resolution usually appears in the list. If a requested size does not take,
`acUpdate` notices a frame later and logs what AC made it instead.

---

## 3. Where the art comes from

Nothing is drawn by hand. Everything is Whiplash's own sprites, read out of
the retail data by `tools/whiplash_bm.py`.

A `.BM` is a "compacted" file: four bytes of uncompressed length, then a
byte-opcode LZ stream. `unmangle()` is `loadcompactedfilepart` from ROLLER's
`sound.c`, branch for branch — short, medium and long back-references plus
literal runs. What comes out is

```c
tBlockHeader { int iWidth, iHeight, iDataOffset; }
```

repeated, then 8-bit palette indices, rows unpadded, offsets measured from
the start of the table. The block count is not stored: it is
`blocks[0].iDataOffset / 12`, because the first block's pixels begin where
the header table ends. **Index 0 is transparent** — every blitter in
`func2.c` skips it.

`PALETTE.PAL` is 6-bit VGA, so each channel is scaled to 8 bits on read.

### The dial is two instruments in one sprite

`PANEL2.BM` block 0 is 79×70 and carries both the rev counter and the damage
ring. `print_damage` in `func2.c` reads each pixel's *index* as data:

| index | meaning |
| --- | --- |
| `0` | transparent |
| `1 … 48` | the rev arc. The index **is** the step number. |
| `>= 0x31` | the ring. `dam_remap[index]` gives its zone, 1–13. |

An arc step is drawn `0xF3` (blue) when the step is at or below
`fRPMRatio * 48`, and `0xED` (dark blue) when it is not. A ring zone keeps
its own colour once damage has reached its level and is `0x7B` (grey) before.

Doing that per pixel per frame is fine in C on a 320×200 framebuffer and
silly in Python at 60 Hz, so `tools/bake.py` does it once: **49 rev frames**
(0–48) and **14 ring frames** (0–13), stacked at draw time with two
`_blit` calls.

Other blocks come out whole: gear letters, speed digits, chrome digits, the
POS and LAP plates, the dark bar, the mph/kmh tags, the mini font, the cars.
145 PNGs per scale.

---

## 4. Why the art is baked instead of scaled

**AC's Python API has no texture-filtering control.** It gives
`ac.newTexture(path)` and `ac.glQuadTextured(x, y, w, h, id)` and nothing
about sampling. Draw a texture at any size other than its own and AC's
filtering softens it — which is exactly what pixel art must not do.

So the enlarging happens at bake time, with nearest neighbour, and the app
draws every sprite at exactly its own size:

```python
ac.glQuadTextured(x, y, size[0], size[1], tex)
```

One texel to one screen pixel. Nothing to interpolate.

That makes "size" a property of the art, not of the drawing, so the baker
writes several:

```
tex/x2/  tex/x3/  tex/x4/  tex/x6/
```

each with its own `sizes.txt`. `_find_scales()` discovers them by listing
`tex/` for `x<number>` folders that contain a `sizes.txt`. Changing size in
the game means switching folders — `_texture()` keys its cache on
`"<scale>/<name>"` and loads out of `tex/x<scale>/`. Textures already loaded
for another scale stay loaded (AC has no unload call), so switching back is
free.

`_pick_scale(height)` chooses: whatever `SCALE` asks for, or `height / 360`
rounded if it asks for nothing, snapped to the nearest scale that was
actually baked. Only whole numbers exist, which is the point.

### sizes.txt

Sprite widths are not uniform — the chrome `1` is 14 panel pixels against 21
for the other digits, the speed `1` is 7 against 12, the mini font runs 3 to
7 — so the baker writes every texture's real size and the app lays out from
that. Assuming one width stretches them.

---

## 5. Drawing text and numbers

`MINITEXT.BM` is one block per glyph, and which block is which comes from
`ascii_conv3` in `func2.c`, extracted into `tools/ascii_conv3.txt`. It is not
in alphabetical order: block 37 is an accented É with no ASCII mapping, so
guessing the order puts it over the letter E.

Two advance rules, both `prt_letter`'s:

- **Text** advances by each glyph's own width. A character the table does not
  carry advances 4 pixels and draws nothing — the table's `0xFF` sentinel,
  which is how space works.
- **Digit runs overlap by one panel pixel**: `iTotalDigitWidth += width - 1`.
  `_number` does the same, in screen pixels, by subtracting `_scale`.

`_text_right` is `mini_prt_right`: the string *ends* at the given x rather
than starting there.

`_number_width` answers in **panel** pixels, because the layout block is
written in panel pixels and the centred numbers are centred there.

---

## 6. The layout

One commented block at the top of `whiplash_hud.py`, every number in panel
pixels, multiplied by the scale at draw time. They are `func2.c`'s own
values with the screen-edge arithmetic resolved: where the game writes
`winw - 44` for a dial drawn at `winw - 80`, the block says `36`.

The convention:

- **positive X** counts right from the cluster's left anchor
- **negative X** counts left from its right anchor
- **Y** always counts down from the top of the cluster

so `DIAL_X = -80` is 80 in from the right edge and `POS_X = 0` is flush left.
Each cluster is placed against the corner it belongs to and nothing is
stretched: a widescreen gets the same panel with more road between the
clusters, which is how `test_panel()` itself works (`winw - N`, `winh - N`).

Draw order matters in two places, and both are the game's:

- the position plate, then the number, then the two names on its bars
- the lap bar, then the number, then the LAP tag **over the top of both**

Get the second backwards and the bar cuts through the tag.

`tools/preview.py` imports these same constants — with empty `ac`, `acsys`
and `sim_info` modules standing in, since importing the app otherwise needs
the game — so there is exactly one copy of them, and a layout change can be
looked at without starting AC.

---

## 7. Reading the car

Two sources, because neither is enough alone.

**`ac.getCarState(car, acsys.CS.*)`** gives revs, speed, gear, lap count, lap
times, world position and normalised spline position.

**Shared memory**, via `third_party/sim_info.py` (Rombik's, `mmap` +
`ctypes`), gives everything AC's Python API does not: `maxRpm`, `tyreWear`,
`carDamage`, `fuel`/`maxFuel`, `turboBoost`/`maxTurboBoost`. It is imported
in a `try`, and if it is missing the HUD still runs — the ring just stays
grey.

### Revs

`rpm / info.static.maxRpm`, so the arc always fills to the car's own redline
and the shift point is always the top of it. The 40–90 painted around the
dial is therefore decoration: no AC car has Whiplash's rev range.

### The ring

`_meter()` turns whatever it is pointed at into one 0..1 fraction, because
the ring is thirteen zones with no numbers on it. Every source fills as
things get worse, which is the direction the damage meter ran:

| `METER` | fraction |
| --- | --- |
| `TYRES` | worst tyre, across `WEAR_FRESH … WEAR_DEAD` |
| `DAMAGE` | worst of the five `carDamage` zones over `DAMAGE_FULL` |
| `FUEL` | `1 - fuel / maxFuel`, so a full ring is an empty tank |
| `TURBO` | `turboBoost / maxTurboBoost` |

`_log_once` prints the raw numbers behind a source the first time it is read,
so the constants can be pinned from a real session instead of assumed.

### Position

This one has a trap in it. AC has two calls:

- `getCarLeaderboardPosition` — the **official standing**, which in a race
  only settles as cars cross the line. Pass someone mid-lap and it does not
  move until the lap does.
- `getCarRealTimeLeaderboardPosition` — the **live order**, which is how
  Whiplash's own `byRacePosition` behaves.

`_standings()` uses the live one, falls back to the standing if it has no
answer, and **sorts the field** rather than trusting the number. `_place_in`
then counts along that order. Two reasons:

- the place and the two names come from one order, so the plate's number and
  the names on its bars can never disagree;
- the documentation does not say whether AC counts positions from 0 or from
  1, and counting along a sorted list does not care.

`getCarsCount()` is the session's **maximum** number of cars, not how many
are in it, so empty slots are dropped on `ac.isConnected`. Left in they sit
in the standings and push everyone below them down a place, and they draw as
cars on the map. If that filter leaves car 0 out of its own session it is
telling us nothing, so then nothing is filtered.

### Gaps

AC hands out positions, not gaps. `_gaps` takes the normalised spline
distance between two cars and multiplies by a lap time: right on a steady
lap, optimistic under braking, which is what a gap readout always is.

### The map

AC ships a `map.png` per track and a `data/map.ini` giving
`pixel = (world + OFFSET) / SCALE`. The key names are picked by substring out
of whatever the file holds rather than assumed; if nothing recognisable is
there the map still draws and the log says what the file did contain.

---

## 8. The two apps talking

`config.ini` is the whole channel. The setup app writes the file from one
template; the HUD re-reads it every `CONFIG_POLL` (0.5 s) and applies what
changed. No shared state, no import between them, nothing to keep in sync —
and the file stays hand-editable, which is useful when something is wrong
with the setup app itself.

The setup app looks for the HUD beside itself (`../whiplash_hud`), which is
why both folders have to be installed.

Its button callbacks take `*args`: AC passes click coordinates to a clicked
listener, and the documentation does not pin the arity.

---

## 9. The tools

| tool | what it does |
| --- | --- |
| `bake.py` | retail data → `tex/x<N>/`, one folder per scale |
| `whiplash_bm.py` | the decompressor, block reader, palette and PNG writer |
| `preview.py` | the whole panel, drawn offline from the raw blocks |
| `dryrun.py` | both apps against a fake `ac` |
| `dump_bm.py`, `sheet.py` | contact sheets, for looking at a file's blocks |

`dryrun.py` is the one worth knowing. It stands an empty recorder in for
`ac`, `acsys` and `sim_info`, runs `acMain`, `acUpdate` and `onRender`,
**clicks every listener the app registered**, and reports what the window was
told plus anything that raised. It restores `config.ini` afterwards, since
clicking the setup app's buttons really does write it.

It does not test the game, and it cannot. What it catches is the failure
described in §1 — the silent half-run — before AC does.

---

## 10. What is still unpinned

- `WEAR_FRESH` / `WEAR_DEAD` / `DAMAGE_FULL`. Set them from the `_log_once`
  lines in a real session.
- `TURBO` fills as a fraction of `maxTurboBoost`, which needs no unit. A
  readout in psi would need AC's unit for `turboBoost` pinned first.
- `map.ini` key names are sniffed, not known. One real file would settle it.
- The timing column is in the mini font. Whiplash prints it in `FONT6.BM`,
  with its own character table (`font6_ascii`), and `ShowATime` spaces the
  digits by hand — 9 panel pixels apart, 3 for a colon. Baking that font
  would make the column retail-exact.

Everything else in here is `func2.c`'s, and `func2.c` is the authority. When
something looks wrong, read it there first — most of what went wrong in this
project went wrong by assuming instead.
