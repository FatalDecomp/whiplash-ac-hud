# Asennusohje / Install guide

Suomeksi ensin. English below.

---

# SUOMEKSI

Hei Tunari. Tässä on ohje. Lue se järjestyksessä.

Kuvat eivät tule mukana. Sinun pitää tehdä ne itse omasta Whiplash-pelistäsi.
Se on vaihe 2. Se tehdään vain kerran.

## Mitä tarvitset

1. **Assetto Corsa.**
2. **Whiplash (Fatal Racing) -pelin tiedostot.** Tarvitset kansion **FATDATA**.
3. **Python 3.** Lataa se osoitteesta python.org. Kun asennat sen, laita
   rasti kohtaan **"Add Python to PATH"**.

FATDATA-kansiossa pitää olla nämä neljä tiedostoa:

- `PANEL2.BM`
- `MINITEXT.BM`
- `PANCAR1.BM`
- `PALETTE.PAL`

Jos ne löytyvät, kaikki on hyvin.

## Vaihe 1: Lataa tämä projekti

Mene GitHubiin. Paina vihreää **Code**-nappia. Valitse **Download ZIP**.

Pura ZIP-tiedosto johonkin kansioon. Esimerkiksi työpöydälle.

## Vaihe 2: Tee kuvat pelistä

Avaa kansio, johon purit ZIP-tiedoston. Siellä pitää olla kansiot `apps` ja
`tools`.

Kirjoita Resurssienhallinnan osoiteriville `cmd` ja paina Enteriä.
Komentorivi aukeaa.

Kirjoita tämä **yhdelle riville**:

```
python tools\bake.py "C:\polku\FATDATA" apps\python\whiplash_hud\tex 2 3 4 6
```

Laita oman FATDATA-kansiosi polku lainausmerkkien väliin.

Numerot `2 3 4 6` ovat kokoja. Ohjelma tekee neljä eri kokoa. Voit vaihtaa
kokoa myöhemmin pelin sisällä. Älä poista numeroita.

Kun ohjelma on valmis, se sanoo näin:

```
145 textures at 2x in apps\python\whiplash_hud\tex\x2
145 textures at 3x in apps\python\whiplash_hud\tex\x3
145 textures at 4x in apps\python\whiplash_hud\tex\x4
145 textures at 6x in apps\python\whiplash_hud\tex\x6
```

Nyt kuvat ovat valmiit.

> Jos komento `python` ei toimi, kokeile komentoa `py`.

## Vaihe 3: Kopioi kansiot peliin

Etsi Assetto Corsan kansio. Se on yleensä täällä:

```
C:\Program Files (x86)\Steam\steamapps\common\assettocorsa
```

Kopioi **kaksi** kansiota:

- `apps\python\whiplash_hud`
- `apps\python\whiplash_setup`

Kopioi ne tänne:

```
assettocorsa\apps\python\
```

**Molemmat kansiot pitää kopioida.** Setup-ohjelma etsii HUD-ohjelmaa
vierestään. Jos kopioit vain toisen, se ei toimi.

## Vaihe 4: Laita ohjelmat päälle

1. Käynnistä Assetto Corsa.
2. Mene kohtaan **Settings → General**. Etsi lista **UI Modules**.
3. Laita rasti kohtiin **Whiplash HUD** ja **Whiplash HUD Setup**.
4. Mene radalle.
5. Vie hiiri näytön **oikeaan reunaan**. Palkki tulee näkyviin.
6. Paina molempien ohjelmien kuvakkeita.

> Jos käytät Content Manageria, ohjelmat laitetaan päälle kohdassa
> **Settings → Assetto Corsa → Apps**.

## Vaihe 5: Säädä koko

HUD-ikkunassa ei ole nappeja. Kaikki säädöt ovat **Whiplash HUD Setup**
-ikkunassa. Siinä on neljä riviä:

| Rivi | Mitä se tekee |
| --- | --- |
| **SCREEN** | HUD-ikkunan koko. **Laita tähän näyttösi tarkkuus.** |
| **SIZE** | Kuvien koko. Jätä tähän `AUTO`. |
| **RING** | Mitä mittari näyttää: renkaat, vauriot, bensa tai turbo. |
| **SPEED** | `MPH` tai `KMH`. |

**SCREEN on tärkein rivi.** Paina `-` ja `+` -nappeja, kunnes SCREEN on sama
kuin näyttösi tarkkuus. Esimerkiksi `1920x1080`.

Jos SCREEN on väärin, HUD on pienessä laatikossa näytön nurkassa.

Muutokset näkyvät heti. Peliä ei tarvitse käynnistää uudelleen.

## Jos jokin ei toimi

**HUD ei näy ollenkaan.**
Avaa tiedosto `Documents\Assetto Corsa\logs\py_log.txt`. Etsi sieltä sanaa
`Whiplash`. Siellä lukee, mikä meni vikaan.

**HUD näkyy, mutta kuvia ei ole.**
Vaihe 2 ei onnistunut. Katso, että kansiossa
`assettocorsa\apps\python\whiplash_hud\tex` on kansiot `x2`, `x3`, `x4` ja
`x6`.

**HUD on pienessä laatikossa nurkassa.**
SCREEN on väärin. Katso vaihe 5.

**Teksti ja mittarit ovat sumeita.**
SIZE on eri kuin mikään tehty koko. Laita SIZE takaisin `AUTO`-asentoon.

---

# IN ENGLISH

The art does not come with this. You bake it from your own copy of Whiplash
— that is step 2, and you only do it once.

## What you need

1. **Assetto Corsa.**
2. **Whiplash (Fatal Racing) game files** — specifically its **FATDATA**
   folder.
3. **Python 3**, from python.org. Tick **"Add Python to PATH"** when you
   install it.

FATDATA must contain these four files:

- `PANEL2.BM`
- `MINITEXT.BM`
- `PANCAR1.BM`
- `PALETTE.PAL`

## Step 1: Download this project

On GitHub, press the green **Code** button and choose **Download ZIP**.
Unzip it anywhere.

## Step 2: Bake the art out of the game

Open the folder you unzipped. It should contain `apps` and `tools`.

Type `cmd` into Explorer's address bar and press Enter. A command prompt
opens in that folder.

Type this **on one line**:

```
python tools\bake.py "C:\path\to\FATDATA" apps\python\whiplash_hud\tex 2 3 4 6
```

Put the path to your own FATDATA folder between the quotes.

`2 3 4 6` are sizes, in screen pixels per panel pixel. The baker writes all
four, and you switch between them in the game. Don't drop them: the art is
enlarged here rather than in AC, because AC has no way to turn texture
filtering off, so each size has to exist as its own set of textures.

When it finishes it prints:

```
145 textures at 2x in apps\python\whiplash_hud\tex\x2
145 textures at 3x in apps\python\whiplash_hud\tex\x3
145 textures at 4x in apps\python\whiplash_hud\tex\x4
145 textures at 6x in apps\python\whiplash_hud\tex\x6
```

> If `python` isn't recognised, try `py` instead.

## Step 3: Copy the folders into the game

Find your Assetto Corsa folder, usually:

```
C:\Program Files (x86)\Steam\steamapps\common\assettocorsa
```

Copy **both** of these:

- `apps\python\whiplash_hud`
- `apps\python\whiplash_setup`

into:

```
assettocorsa\apps\python\
```

Both are needed. The setup app looks for the HUD beside itself.

## Step 4: Turn the apps on

1. Start Assetto Corsa.
2. **Settings → General**, find the **UI Modules** list.
3. Tick **Whiplash HUD** and **Whiplash HUD Setup**.
4. Go out on track.
5. Move the mouse to the **right edge** of the screen to open the app bar.
6. Click both apps' icons.

> With Content Manager, apps are enabled under
> **Settings → Assetto Corsa → Apps**.

## Step 5: Set the size

The HUD has no buttons on it — it is a transparent overlay with its title
bar hidden. Everything is set from **Whiplash HUD Setup**:

| Row | What it does |
| --- | --- |
| **SCREEN** | the HUD window's size. **Set this to your display's resolution.** |
| **SIZE** | which baked set to draw. Leave it on `AUTO`. |
| **RING** | what the ring reads: tyres, damage, fuel or turbo. |
| **SPEED** | `MPH` or `KMH`. |

**SCREEN first.** The panel anchors to the corners of the HUD's own window,
so until that window matches your display, the whole panel sits in a small
box in one corner. Press `-` and `+` until it reads your resolution.

There is no automatic fit: AC's Python API has no call that reports the
screen size. The setup app does read AC's own `cfg\video.ini` and add what
it finds to the list, so your resolution is usually already there.

Changes apply immediately — the HUD re-reads its settings twice a second.
No restart.

## If something is wrong

**Nothing appears at all.**
Open `Documents\Assetto Corsa\logs\py_log.txt` and search for `Whiplash`.
The app logs its build and what it could not find.

**The HUD is there but there is no art.**
Step 2 did not finish. Check that
`assettocorsa\apps\python\whiplash_hud\tex` contains `x2`, `x3`, `x4` and
`x6` folders.

**The panel sits in a small box in a corner.**
SCREEN is wrong. See step 5.

**Text and gauges look blurry.**
SIZE is set to a scale you did not bake. Put it back to `AUTO`.

---

Taking it apart rather than using it? [TECHNICAL.md](TECHNICAL.md)
explains how the Python works.
