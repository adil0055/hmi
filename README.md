# Car HMI — digital instrument cluster

A working recreation of a modern car's digital instrument cluster, built with
**Qt Quick / QML** and **PySide6**, plus a separate **test panel** window that
feeds it input so every state can be exercised without a car.

Two cluster designs ship, switchable at runtime: **Classic dials**, a
conventional twin-dial cluster, and **BMW chevrons**, a letterboxed
curved-display layout in the style of BMW's Operating System 8. Fourteen
typefaces ship with it, and the artwork re-measures and re-aligns itself
around whichever one is loaded.

![cluster at rest](docs/cluster.png)

![cluster while driving](docs/driving.png)

---

## Running it

Requires Python 3.9+ on Linux (also runs on macOS and Windows).

```bash
git clone <this repo>
cd hmi
./run.sh
```

`run.sh` creates a local `.venv`, installs PySide6 into it, and launches both
windows. To do it by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

The typefaces are committed, so nothing has to be downloaded first. Run
`python3 tools/fetch_fonts.py` only after adding a family to
`assets/fonts/catalog.json`.

On Windows, `run.sh` does not apply — the virtualenv puts its interpreter
somewhere else and Qt Quick Controls defaults to a native style that discards
the panel's styling:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:QT_QUICK_CONTROLS_STYLE = 'Basic'
.\.venv\Scripts\python.exe main.py
```

### If Qt complains about missing libraries

PySide6 ships Qt itself but still needs a few system libraries. On
Debian/Ubuntu:

```bash
sudo apt install libegl1 libgl1 libxkbcommon-x11-0 libfontconfig1 \
     libdbus-1-3 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 \
     libxcb-shape0 libxcb-xkb1 libxcb-render-util0 libxcb-image0
```

On Fedora: `sudo dnf install mesa-libEGL mesa-libGL libxkbcommon-x11 fontconfig`.

### Command line

| Flag | Effect |
| --- | --- |
| `--no-panel` | cluster only, no control panel |
| `--size-panel` | also open the text-size panel |
| `--fullscreen` | open the cluster full screen |
| `--scale N` | force the render scale instead of fitting the window |
| `--screenshot FILE` | render one frame to a PNG and exit (works headless) |
| `--font FILE...` | start with your own typeface (files, or a folder of them) |
| `--font-family ID` | start on a bundled typeface (`inter`, `teko`, `rajdhani`, …) |
| `--text-scale N` | scale every run of text at once (0.6–1.8) |
| `--skin NAME` | which cluster to draw: `classic` or `bmw` |
| `--layout-panel` | also open the layout-fault panel |
| `--layout-shift ID=dx,dy` | draw an element out of place on purpose |
| `--layout-reset` | clear every stored layout fault before starting |
| `--layout-export FILE` | write the commanded faults as JSON |
| `--calibration P` | draw a test pattern instead of the cluster |
| `--calibration-square N` | chessboard square size, in display pixels |
| `--calibration-export FILE` | write the pattern's corner coordinates as JSON |
| `--can [BUS]` | take every signal from a CAN bus; see [Driving it over CAN](#driving-it-over-can) |
| `--dbc FILE` | the CAN database to decode with (default `can/hmi.dbc`) |
| `--frame-server PORT` | serve the cluster as drawn at `http://127.0.0.1:PORT/frame.png` |

Keys in the cluster window: **F11** full screen, **Esc** leave full screen,
**B** show/hide the bezel.

---

## The two cluster designs

Switch between them with **Cluster design** at the top of the test panel, or
`--skin` on the command line. Each is drawn on its own fixed canvas and scaled
uniformly to the window, so the window re-proportions itself when you swap.

**Classic dials** (1790x870) — twin round dials with needles, segmented fuel
and coolant arcs, a centre drive-info column and a perspective lane graphic.

**BMW chevrons** (1920x720) — the letterbox layout: two chevron bands facing
each other across the centre, speed and gear pushed out to the far edges, a
media tile between them and a status strip along the bottom. It reads as an
electric car, so the rev counter is replaced by an ePower gauge running from
full recuperation to full power, and the fuel gauge by a state of charge.

Its animation is part of the design, not decoration on top of it:

- a **wake-up sweep** on power-up — both bands run to full scale and back while
  the furniture fades in behind them, the way a real cluster proves its
  instruments;
- gauges **chase** their value with easing rather than snapping, and the scale
  lights up tick by tick as it passes;
- the speed **counts** rather than cuts, so a digit change is legible;
- the gear letter **lifts and settles** when the selection changes;
- drive mode **cross-fades** the accent through the bands, the cover art and
  the mode caption at once — Sport splits it, cold blue on the speed side and
  red on the power side;
- the power band **pulses** near the stop, and recuperation takes its own
  colour below zero;
- indicators, telltales and the charging lamp **blink or breathe**.

The ePower band is a second reading of the same physics rather than a separate
powertrain: demand comes from the throttle, weighted by how much of the motor's
output is going into pushing through drag rather than into acceleration, so the
same pedal reads higher further up the speed range. The negative half is
recuperation — strong under braking, a gentle one-pedal drag on a lift-off, and
fading to nothing as the car stops, because a stationary car recovers nothing.
State of charge follows it, draining under power and recovering under
recuperation, so the percentage in the status strip means something. In
**Manual** the panel's *ePower* and *Charge* sliders drive both directly.

---

## The windows

**Cluster** — the display itself, scaled uniformly to whatever size the window
is, so proportions never shift.

**Test panel** — the input side. Two ways to drive it:

- **Simulate** (default) runs a small vehicle model. Move the throttle, and
  engine torque goes through the gearbox to the wheels; the car accelerates
  against drag and rolling resistance, the automatic shifts, fuel burns,
  coolant warms up, and the trip computer fills in. The shift interlock is
  modelled too — you cannot leave `P` without the brake and a running engine.
- **Manual** pins `speed` and `rpm` to exact values so you can park the needles
  anywhere for a screenshot or an edge case.

Everything else — fuel, temperatures, lighting, doors, belts, every warning
lamp, cruise control, units — is settable at any time in either mode.

**Size panel** — opened from **Text sizes…** in the test panel, or with
`--size-panel`. Lists every run of text in both clusters with the size it is
currently set at and a slider each; see [Text sizes](#text-sizes).

**Layout panel** — opened from **Layout faults…** in the test panel, or with
`--layout-panel`. Moves, resizes, turns and hides elements on command, and
switches the cluster to a calibration pattern; see
[Testing what watches the cluster](#testing-what-watches-the-cluster).

---

## What the cluster shows

**Gauges** — speedometer 0–220 km/h, tachometer 0–8000 rpm with a red band from
6500, segmented fuel and coolant arcs with reserve and overheat zones marked.

**Drive info** — gear (P/R/N/D, plus the held ratio in Sport), distance to
empty, trip distance, trip timer, average and instantaneous economy, odometer,
outside temperature.

**Telltales** — 30 lamps on the conventional severity order (red stop lamps
first, then amber cautions, then blue/green status): brake, park brake, oil
pressure, charging, coolant temperature, airbag, seatbelts, doors ajar, forward
collision, check engine, ABS, ESC and ESC off, traction off, EPS, TPMS, low
fuel, washer fluid, glow plug, immobiliser, lane departure, rear fog, high and
low beam, position lights, front fog, cruise control set and ready. Unlit lamps
take up no space, so an idle cluster shows an empty strip.

**Units** — metric or imperial throughout, and km/L, L/100km or mpg for economy.

**Drive modes** — Comfort, Eco, Sport and Smart, each with its own accent
colour; Eco and Sport also change the shift points and fuel burn.

---

## Typefaces

The **Typeface** dropdown in the test panel switches the cluster between the
fourteen families in `assets/fonts/catalog.json`, each row set in itself so the
list shows what it is offering rather than describing it. The whole cluster
restyles immediately — numerals, gauge labels, drive info, odometer, everything.

### What ships, and why

Instrument clusters are a specialist typographic problem: they are read at a
glance, backlit, at an angle, by a driver who should be looking at the road.
Research by [MIT AgeLab with Monotype][mit] found the square grotesques the
industry reached for by reflex cost 12% in glance time against humanist
designs — around 50 feet of braking distance at speed — which is why several
of the faces below are humanist rather than the obvious "tech" choice.

The faces the manufacturers actually ship are proprietary and cannot be
redistributed: Monotype's [Burlingame][mono] (drawn against that research),
Tipperary and Daytona, Frutiger, BMW Type Next, Hyundai Sans. Everything here
is instead SIL OFL 1.1 or Apache 2.0, chosen either because a manufacturer
genuinely uses it or because it is the closest open stand-in for one that
cannot be shipped — and the catalogue's `note` field says which.

| Family | Style | Why it is here |
| --- | --- | --- |
| Titillium Web | Humanist | The face the artwork was drawn against; the reference for everything below |
| **Inter** | Neo-grotesque | **TATA.ev's brand typeface** — Tata chose this open family outright for the EV identity |
| Roboto | Neo-grotesque | Android Automotive OS default, so it is under a lot of real clusters |
| **Rajdhani** | Squarish | Indian Type Foundry; squared technical face, Devanagari + Latin |
| **Khand** | Condensed | Indian Type Foundry; condensed, tall figures, Devanagari + Latin |
| **Teko** | Condensed | Indian Type Foundry; very narrow — big numbers in little space |
| IBM Plex Sans | Neo-grotesque | Closest open stand-in for BMW Type Next |
| Archivo | Grotesque | Wide apertures at small sizes — the Frutiger/Burlingame school |
| Barlow | Grotesque | Low-contrast, slightly rounded; reads well backlit |
| Saira | Technical | Width axis, suits wide gauge faces |
| Chakra Petch | Squarish | Cut corners and square bowls — the sport-cluster look |
| Exo 2 | Technical | Contemporary technical sans |
| Orbitron | Display | Geometric display face; the EV/concept cliche |
| Oxanium | Display | Angular, chamfered — echoes the BMW chevrons |

On the Indian manufacturers specifically: Tata Motors' own wordmark is set in a
Helvetica-style grotesque, but **TATA.ev** moved to Inter, an open variable
family, explicitly for accessibility and file size — so that one is not an
approximation, it is the real thing. Maruti Suzuki's wordmark is an extended
geometric grotesque (Helvetica/Swiss 721 Black Extended territory) and
Mahindra's is a condensed geometric custom; Rajdhani, Khand and Teko are all
from the Indian Type Foundry and cover that idiom, with Devanagari as a bonus.

[mit]: https://www.ai-online.com/2015/04/the-science-behind-display-fonts-for-in-car-screens/
[mono]: https://www.monotype.com/resources/fonts-cars

### The layout re-aligns itself

Swapping a typeface is not just a family name. Across the catalogue, cap height
spans 0.63–0.73 em, ascent 0.79–1.14 em, and the advance of a digit 0.39–0.83
em — Orbitron's figures are more than **twice** the width of Teko's at the same
nominal size. Dropped into artwork with hard-coded coordinates, that would look
broken three separate ways, so three separate things happen:

- **Optical size.** `FontManager` measures the active face and publishes a
  `capScale`; `Theme.px()` multiplies by it, so every face draws capitals at
  the same height rather than the same nominal pixel size.
- **Vertical position.** Qt centres text on its line box, which is ascent plus
  descent — and faces reserve wildly different room for accents they may never
  draw. `Theme.capDy()` returns the nudge that puts the middle of the *capital
  band* back where the reference face had it. Where one run has to sit on
  another's baseline, it anchors to `baseline` so Qt does the arithmetic from
  the real metrics instead of a guessed fraction.
- **Width.** Readouts with a hard limit on their slot carry a `fitWidth` and
  shrink rather than overrun it, and figures are set with tabular numerals so a
  changing readout does not shuffle sideways.

The net effect: `--font-family orbitron` and `--font-family teko` put every
numeral, label and unit in the same place and at the same apparent size as the
default, despite a 2.1x difference in figure width between them.

### Loading your own

- **Load font…** opens a file picker. Select a family's several styles at once
  (regular, italic, bold) — the cluster asks for italic numerals and a
  demi-bold range, so Qt otherwise has to synthesise them from the regular.
- Or type a path into the field and press **Apply**. A folder works too: every
  font file in it is loaded.
- **Use bundled** goes back to Titillium Web.

A face loaded from disk is measured and aligned exactly like a bundled one.

`.ttf`, `.otf`, `.ttc`, `.woff` and `.woff2` all work. The panel shows the
family name it resolved, a live preview in that font, and an explanatory
message if a file could not be read.

Your choice is remembered, so the cluster comes back up in your font next
time. If that file later moves or is deleted, the cluster falls back to the
bundled typeface and says so rather than failing to start.

You can also set it from the command line, which is handy for screenshots:

```bash
python3 main.py --font-family rajdhani
python3 main.py --font ~/fonts/Inter-Regular.ttf ~/fonts/Inter-Italic.ttf
python3 main.py --font ~/fonts/my-brand-family/
python3 tools/shoot.py shot.png --font-family teko --set skin=bmw speed=120
```

To add a family, put an entry in `assets/fonts/catalog.json` and run
`python3 tools/fetch_fonts.py` — it pulls the files from the upstream
`google/fonts` repository and refuses anything that is not really a font.

The control panel deliberately keeps the bundled font for its own labels. If
a loaded font turned out to be a symbol or display face, a panel rendered in
it would leave you no way to read the button that undoes the change.

---

## Testing what watches the cluster

A camera pointed at the cluster, checking that everything is where the design
says it should be, cannot be trusted until it has been shown to report a
displacement that was really applied. On a cluster that is already correct,
a validator that always answered PASS would score full marks.

So the cluster can draw itself **wrong**, on purpose, by an exact amount — and
it can draw a **calibration pattern** so the camera can work out where the
display is in the first place.

### Layout faults

**Layout faults…** in the test panel lists every element either cluster draws,
with four numbers and a switch each:

| | |
| --- | --- |
| **dx**, **dy** | move it, in design pixels |
| **scale** | draw it too large or too small, about its own centre |
| **rot** | turn it, in degrees |
| **Hide** | do not draw it at all |

Between them those cover what a layout check reports: wrong position, wrong
size, wrong orientation, missing. Typed fields rather than sliders, because the
whole value of this is that the number is *known* — a slider gives you 2.7 when
you meant 3.

Offsets are in **design pixels**, the units `Theme.qml` and `BmwTheme.qml` are
written in, so a commanded 3 px is 3 px of the framebuffer whatever the window
has been scaled to. The panel also shows what that comes to at the current
render scale, which is the number a camera would be measuring.

From the command line, and on a screenshot:

```bash
python3 main.py --layout-panel --layout-shift classic.dial.speed=3,1.25
python3 main.py --layout-shift bmw.gear=0,0,1,12 bmw.media=hidden
python3 tools/shoot.py faulty.png --layout-shift classic.gauge.fuel=-30,0 \
    --layout-export faulty.json
```

`ID=dx,dy`, `ID=dx,dy,scale,rot` and `ID=hidden` all work. The ids are listed
in `qml/Hmi/LayoutRoles.qml`, and `--layout-export` writes the commanded values
as JSON — that file is the ground truth a validator's answers get scored
against, not another opinion about where things ended up.

Faults **persist between runs**, like the typeface and the text sizes. That is
convenient and it is a trap, so it is a loud one: a run that starts on a
displaced cluster says so on stderr, the test panel's button carries the count,
and the layout panel says it across its header. A cluster quietly drawing three
pixels out because somebody left it that way last week is exactly the sort of
thing that gets diagnosed for a fortnight as a camera fault. `--layout-reset`,
or **Reset all**, puts everything back.

Measured straight off the framebuffer, a commanded shift comes back within
0.03 px on whole pixels and 0.17 px sub-pixel.

### Adding an element

One row in `qml/Hmi/LayoutRoles.qml`, and the element wrapped in a
`LayoutShift` carrying that id:

```qml
LayoutShift {
    role: "classic.dial.speed"
    pivotX: Theme.dialCxLeft; pivotY: Theme.dialCy
    Dial { centreX: Theme.dialCxLeft; ... }
}
```

The wrapper fills its parent and passes design-canvas coordinates through
unchanged, so the element inside keeps positioning itself exactly as it did —
wrapping one costs a line and changes nothing until a fault is commanded.
`pivotX`/`pivotY` are the element's own centre and only matter for `scale` and
`rot`; without them an element would grow about the middle of the canvas, which
moves it as well as resizing it and makes the commanded number untestable.

`python3 tools/layout_test.py` checks the catalogue and the artwork still
agree in both directions — a row without a wrapper is a control in the panel
that moves nothing, which reads as "the validator missed it".

### Calibration patterns

Mapping camera pixels onto display pixels is what sets the accuracy of
everything downstream, and the most direct way to establish it is for the
cluster to draw the pattern itself: then the correspondence is exact and known
rather than inferred from the bezel or the artwork.

| Pattern | For |
| --- | --- |
| `checker` | a chessboard, for `findChessboardCornersSB` and a homography |
| `white` | finding the active area by fitting its edges; also a flat field |
| `black` | a dark frame |
| `grid` | eyeballing distortion and focus, with the canvas size captioned |
| `crosshair` | five exact points, for when the chessboard will not detect |

```bash
python3 main.py --calibration checker --calibration-export board.json
python3 tools/shoot.py board.png --calibration checker --calibration-square 120
```

`board.json` carries the board geometry and the inner-corner coordinates. It
gives them **twice**, and which one you use matters:

- `corners_pixel_centre` — pixel column *x* has its centre at *x*. This is what
  OpenCV, NumPy and every detector mean, and it is the list to feed them.
- `corners_qt` — the same points in Qt item coordinates, where a pixel spans
  `[x, x+1)`.

They differ by exactly half a pixel in both axes. Rendering the board and
detecting it back agrees with `corners_pixel_centre` to 0.02 px and with
`corners_qt` to 0.49 px — so quietly picking the wrong one puts half a pixel of
systematic error into the homography and from there into every measurement
taken through it.

The geometry is computed once, in `backend/calibration.py`; the QML draws from
that same result, so what is on the glass and what the rig is told cannot drift
apart.

### Driving it over CAN

A real cluster gets its signals off the vehicle's CAN bus, and a checker that
switches lamps on to find them needs to do it the same way. With `--can` the
cluster listens on a bus and every signal comes from there:

```bash
pip install -r requirements.txt           # python-can, cantools, msgpack
python3 main.py --can                     # virtual bus, no hardware
python3 main.py --can socketcan:vcan0     # Linux virtual CAN
python3 main.py --can pcan:PCAN_USBBUS1@500000   # a real adapter
```

The default, `udp_multicast`, is python-can's virtual bus over the network:
any program on the same computer, or on the same network segment, that opens
the same bus talks to the cluster, with no CAN hardware at all. Some Wi-Fi
networks drop multicast; a cable, or one computer, always works. Any adapter
python-can supports works by naming it: `INTERFACE[:CHANNEL][@BITRATE]`.

**`can/hmi.dbc`** is the CAN database: 9 messages, 68 signals, every lamp,
light, door and belt, the gauges, the trip computer and the media tile. Each
signal is named after the `VehicleState` property it sets, so adding a signal
to the DBC is all it takes to drive it. Gear, drive mode, lane departure and
units are value tables whose names are the strings the property holds (`"D"`,
`"Sport"`, `"left"`). Start values are the cluster's power-up state, so a
tester that sends the defaults changes nothing on the screen.

While the bus drives, the driving model stands still (it would otherwise
overwrite the speed and count kilometres while a tester sweeps it). Only a
signal whose value changed is applied, so the test panel can still move what
the tester leaves alone.

**`can/teach_plan.json`** says what a checker should switch on to find and
name everything this cluster draws: every lamp one at a time, which ones
flash, and each gauge or readout driven through a few values. layoutval's
CAN teach-in reads it (`layoutval go --webcam --can --teach-plan
can/teach_plan.json`).

**`--frame-server PORT`** serves the window as drawn, at
`/frame.png`, so a camera-based checker can be run end to end against the
framebuffer itself with no camera. On a machine with no display, give Qt a
screen as large as the cluster, or the window is scaled down to fit:

```bash
echo '{"screens":[{"name":"s","x":0,"y":0,"width":2560,"height":1440,"logicalDpi":96,"logicalBaseDpi":96,"dpr":1}]}' > screen.json
QT_QPA_PLATFORM="offscreen:configfile=screen.json" python3 main.py --no-panel --can --frame-server 8799
```

Two things found by switching every lamp on over CAN, and fixed:

- **Flashing lamps never showed on their own.** The seat-belt, collision,
  ESC, immobiliser and lane-departure lamps show only in the flash's "on"
  half, and the flash only ran while an indicator was on. It now runs while
  anything that flashes is lit.
- **A flashing lamp made the strip jump.** On the flash's "off" half the lamp
  was hidden, and a hidden lamp takes no space in the strip, so every lamp
  after it moved a slot sideways and back every 380 ms. A lit lamp now keeps
  its slot and only fades out.

One that is a design matter rather than a bug: with most lamps lit at once
the strip wraps into a third row, which runs over the gear letter and the
speedometer.

---

## Text sizes

Switching typeface changes what a size *means*. A face chosen for its numerals
often wants its captions a little smaller; a condensed face can take a couple
of points more before it fills the same slot. So the sizes the artwork was
drawn at are defaults rather than constants, and both the whole set and each
run on its own can be moved.

**All text** in the test panel scales every run at once, between 0.6x and 1.8x.
That is the knob for "this face reads small, bring the cluster up a bit".

**Text sizes…** opens a second panel listing all 36 runs of text in the two
clusters — speed digits, scale numerals, trip labels, status bar, each of them
— grouped by where they appear, with a slider each and the size each one is
currently set at. Filter it to the skin you are looking at, or show both.

### Three numbers per row

"Font size" means three different things once the typeface is switchable, so
each row shows all three:

| Column | What it is |
| --- | --- |
| **design** | what the artwork asks for, and the number the slider edits |
| **→ N px** | what actually reaches `font.pixelSize`, after `Theme.px()` scales the design size by how tall the loaded face draws its capitals |
| **on screen** | that again times the cluster window's render scale — what you could measure on the glass |

The gap between the first two is the point: a face with small capitals is
*set* larger to look the same size. The header shows that correction as a
single figure (`×1.000` for the reference face), which is usually the answer to
"why did swapping face not change anything".

Each row also carries a specimen in the face that run is really drawn in, at
the size it is really drawn at, so the number and the thing it describes are in
the same place.

Rows moved off their drawn size are outlined and marked **drawn at N**;
**Reset** on the row puts one back, **Reset all** puts everything back
including the scale. Sliders run from half to double the drawn size — enough to
rebalance a face, not enough to lose a run off the canvas and wonder where it
went.

Sizes are remembered between runs, exactly like the typeface, and can be set
from the command line for screenshots:

```bash
python3 main.py --text-scale 1.2 --font-family teko
python3 tools/shoot.py shot.png --text-scale 1.15
python3 tools/shoot.py shot.png --text-size classic.dial.speed=110 classic.info.unit=18
```

### Where they live

Every run of text is one entry in `qml/Hmi/TextSizes.qml`, with a stable id,
the size the artwork was drawn at, and the label and description the panel
lists it under. `Theme` and `BmwTheme` expose those as the size properties they
always had — `Theme.gearSize`, `BmwTheme.statusSize` — so the drawing code is
unchanged and still reads a name rather than a number. The difference is that
those properties are now bindings, so a nudge in the panel reflows the cluster
immediately.

Adding a run of text therefore means adding a row to `TextSizes.qml` and a
one-line binding to the theme, rather than writing a literal into the artwork.
A literal still works, but the panel cannot see it and the user cannot adjust
it.

The state itself — the scale and the per-run overrides — belongs to
`backend/sizes.py`, which owns the `QSettings` write; `Main.qml` pushes it into
the singleton the same way it pushes the typeface into `Theme`.

---

## Layout

```
main.py                 entry point: registers fonts, model and QML
backend/
  vehicle.py            VehicleState — every cluster signal as a Qt property
  simulator.py          engine, gearbox, road load, fuel, trip computer
  fonts.py              FontManager — the catalogue, custom faces, and metrics
  sizes.py              TextSizeManager — the text scale and per-run overrides
  layout.py             LayoutManager — deliberate layout faults, and the warning
  canbus.py             CanInput — every signal from a CAN bus, decoded with the DBC
  frameserver.py        the window as drawn, over HTTP, for testing
  calibration.py        the test patterns, and where their corners really are
qml/
  Main.qml              the three windows
  Hmi/
    Theme.qml           classic geometry and colour, plus the font adaptation
    BmwTheme.qml        BMW geometry and colour, and the chevron polygon
    TextSizes.qml       every run of text, with the size it was drawn at
    LayoutRoles.qml     every element a fault can be commanded on
    LayoutShift.qml     applies one element's fault, and nothing else
    CalibrationScene.qml  a test pattern at exact framebuffer coordinates
    Fmt.qml             unit conversion and display formatting
    ClusterText.qml     text that holds its size and place across typefaces
    ClusterWindow.qml   hosts whichever skin is selected, and scales it
    ClusterScene.qml    composes the classic display
    Dial.qml            face, rim, ticks, needle, readout
    TickRing.qml        tick marks and numerals
    MiniArcGauge.qml    the fuel / coolant arcs
    CenterPanel.qml     gear, range, drive info, eco bar
    LaneGraphic.qml     perspective lane markings
    BottomBar.qml       outside temperature and odometer
    BmwScene.qml        composes the BMW display, and its animation
    BmwGauge.qml        one chevron gauge: band, scale, bloom, caption
    BmwChevron.qml      the lit band, drawn twice so it can glow and stay crisp
    BmwMediaTile.qml    cover art, track, progress
    BmwStatusBar.qml    charge, clock, mode, temperature, range
    TelltaleBar.qml     the warning lamp strip, shared by both skins
    ControlWindow.qml   the test panel, including the typeface dropdown
    TextSizeWindow.qml  the size panel: every run of text, and a slider each
    LayoutWindow.qml    the layout panel: faults, and the calibration patterns
assets/
  fonts/
    catalog.json        the fourteen families, with licence and provenance
    <Family>/           the font files themselves, plus each one's licence
  icons/                generated telltale symbols
tools/
  fetch_fonts.py        downloads everything in catalog.json
  make_icons.py         regenerates assets/icons
  shoot.py              headless screenshot of any cluster state
  smoke_test.py         drives the simulator and checks it behaves
  layout_test.py        checks the fault catalogue, the artwork and the board
```

### Adjusting the artwork

`qml/Hmi/Theme.qml` and `qml/Hmi/BmwTheme.qml` hold every coordinate, radius,
font size and colour their cluster draws with, in design-canvas pixels. Nothing
else contains a magic number, so moving an element is a one-line change there.
Text sizes are the one thing declared elsewhere — in `qml/Hmi/TextSizes.qml`,
so the size panel can list and adjust them — but they still reach the artwork
as a named property on the theme.

Sizes in those files are *design* sizes, quoted against the reference face. Set
text with `ClusterText`'s `designSize` rather than `font.pixelSize`, and where
the artwork centres text on a coordinate add `Theme.capDy(designSize)` to the
`y`, so it keeps working when the typeface changes underneath it.

---

## Development

Render any state to a PNG without a display:

```bash
python3 tools/shoot.py shot.png --set speed=118 rpm=3450 gearMode=D \
    headlightMode=2 turnLeft=true blinkOn=true fuelLevel=0.55 coolantTemp=92
```

Check the simulation still behaves:

```bash
python3 tools/smoke_test.py
```

Check the layout-fault machinery and the calibration board:

```bash
python3 tools/layout_test.py
```

Check the CAN input: the DBC against the cluster's properties, decoding,
and what reaches the cluster (no hardware: python-can's in-process bus):

```bash
python3 tools/can_test.py
```

Check a flashing lamp keeps its place in the telltale strip (renders headless):

```bash
python3 tools/telltale_test.py
```

Regenerate the telltale icons after editing `tools/make_icons.py`:

```bash
python3 tools/make_icons.py
```

---

## Notes on fidelity

The cluster is modelled on a Hyundai-style twin-dial display. Two details in
the source photograph are internally inconsistent — it shows 550 km of range
next to an almost-empty fuel arc, and a cold engine next to a marked red zone
on the coolant arc. Both are resolved here in favour of a cluster that
behaves correctly: the coloured band at the `H` end is the fixed overheat
zone, the fuel arc shows the live level, and range is computed from the fuel
remaining once the engine has run. At rest the display reproduces the
reference frame — `P`, 550 km, 0 km/h, 0.0 rpm, 28 °C, 25 km.

## Licence

Code is yours to use. Titillium Web is under the SIL Open Font License; see
`assets/fonts/OFL.txt`.
