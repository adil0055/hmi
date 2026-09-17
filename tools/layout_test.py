#!/usr/bin/env python3
"""Check the layout-fault machinery, headlessly.

No display needed::

    python3 tools/layout_test.py

Three things get checked, and the first is the one that will actually break.

**The catalogue and the artwork agree.**  A fault only does anything if the
element is wrapped in a \\c LayoutShift carrying that id.  Adding a row to
qml/Hmi/LayoutRoles.qml and forgetting the wrapper leaves a control in the
panel that moves nothing — which reads as "the validator missed it" rather
than as "nothing was displaced", and that is an expensive afternoon.  So the
ids in the catalogue and the ids in the scenes are compared both ways.

**The command line parses what it looks like it parses.**  These terms are
typed by hand into a shell; a silent misparse displaces nothing and looks like
the feature is broken.

**The manager stores what it was told.**  Clamping, neutral entries not being
kept, and the export being the commanded value.

**The calibration board's corners are in the convention they claim to be.**
Qt puts pixel column x's centre at x+0.5; image libraries put it at x.  Export
the wrong one and every measurement taken through the resulting homography
carries half a pixel of error.  Checked here as an invariant; checked for real
by rendering the board and detecting it, which needs OpenCV and so lives with
the rig rather than in this repo — that run agrees with the exported
coordinates to 0.02 px and with the Qt ones to 0.49 px.

Exits non-zero on the first failed expectation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.calibration import (  # noqa: E402
    DEFAULT_SQUARE_PX,
    PATTERNS,
    CalibrationManager,
    pattern_geometry,
)
from backend.layout import (  # noqa: E402
    MAX_SHIFT,
    LayoutManager,
    parse_shift,
)

QML = ROOT / "qml" / "Hmi"
SCENES = ["ClusterScene.qml", "BmwScene.qml"]

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


def catalogue_ids() -> list[str]:
    text = (QML / "LayoutRoles.qml").read_text()
    body = text[text.index("property var items"):]
    return re.findall(r"\{\s*id:\s*\"([^\"]+)\"", body)


def wrapped_ids() -> list[str]:
    found: list[str] = []
    for name in SCENES:
        text = (QML / name).read_text()
        for match in re.finditer(r"LayoutShift\s*\{\s*\n\s*role:\s*\"([^\"]+)\"", text):
            found.append(match.group(1))
    return found


def main() -> int:
    print("catalogue and artwork")
    cat, wrapped = catalogue_ids(), wrapped_ids()
    check("catalogue is not empty", bool(cat), f"{len(cat)} elements")
    check("every id is unique", len(set(cat)) == len(cat))
    check("every wrapper is unique", len(set(wrapped)) == len(wrapped))

    missing = sorted(set(cat) - set(wrapped))
    check("every catalogued element is wrapped", not missing,
          "not wrapped: " + ", ".join(missing) if missing else f"{len(cat)} wrapped")
    stray = sorted(set(wrapped) - set(cat))
    check("every wrapper is catalogued", not stray,
          "not in the catalogue: " + ", ".join(stray) if stray else "")

    print("\ncommand line")
    check("ID=dx,dy", parse_shift("classic.dial.speed=3,1.25")
          == ("classic.dial.speed", {"dx": 3.0, "dy": 1.25}))
    check("ID=dx", parse_shift("a=2") == ("a", {"dx": 2.0, "dy": 0.0}))
    check("ID=dx,dy,scale,rot", parse_shift("a=1,2,1.5,10")
          == ("a", {"dx": 1.0, "dy": 2.0, "scale": 1.5, "rot": 10.0}))
    check("ID=hidden", parse_shift("bmw.gear=hidden") == ("bmw.gear", {"hidden": True}))
    for bad in ("nonsense", "a=", "a=x,y", "=1,2"):
        try:
            parse_shift(bad)
            check(f"rejects {bad!r}", False, "parsed without complaint")
        except ValueError:
            check(f"rejects {bad!r}", True)

    print("\nmanager")
    m = LayoutManager(persist=False)
    check("starts clean", not m.modified and m.faultCount == 0)

    m.setShift("a", 3.0, 1.25)
    check("stores a shift", m.faultOf("a")["dx"] == 3.0 and m.faultOf("a")["dy"] == 1.25)
    check("counts it", m.faultCount == 1 and m.isFaulted("a"))

    m.setShift("a", 0.0, 0.0)
    check("a neutral entry is dropped, not stored", m.faultCount == 0,
          "otherwise 'reset' would leave a row behind that reads as faulted")

    m.setShift("b", 10 * MAX_SHIFT, 0.0)
    check("clamps an absurd shift", m.faultOf("b")["dx"] == MAX_SHIFT)
    m.setScale("b", 99.0)
    check("clamps an absurd scale", m.faultOf("b")["scale"] < 99.0)

    m.resetAll()
    m.setShift("c", 2.0, 0.0)
    m.setHidden("d", True)
    m.enabled = False
    check("faults survive the master switch", m.faultCount == 2,
          "an A/B against one reference needs the set kept, not cleared")
    check("summary says the faults are off", "switched off" in m.summary())
    m.enabled = True
    check("summary warns when they are on", "deliberately" in m.summary())

    exported = json.loads(m.exportJson())
    check("export carries the commanded values",
          exported["faults"]["c"]["dx"] == 2.0 and exported["faults"]["d"]["hidden"] is True)
    check("export names its units", exported.get("units") == "design_px")

    m.nudge("c", 0.25, -1.0)
    check("nudge adds to what is there",
          m.faultOf("c")["dx"] == 2.25 and m.faultOf("c")["dy"] == -1.0)

    m.resetAll()
    check("reset all clears everything", not m.modified and m.enabled)
    check("summary is empty when nothing is displaced", m.summary() == "")

    print("\ncalibration board")
    for w, h, name in ((1790, 870, "classic"), (1920, 720, "bmw")):
        g = pattern_geometry(w, h)
        cols, rows = g["cols"], g["rows"]
        check(f"{name}: board fits the canvas",
              cols * g["square_px"] <= w and rows * g["square_px"] <= h,
              f"{cols}x{rows} of {g['square_px']} px")
        check(f"{name}: a quiet zone is left on every side",
              g["origin"][0] >= g["square_px"] and g["origin"][1] >= g["square_px"],
              f"origin {g['origin']}")
        check(f"{name}: enough inner corners to solve on",
              min(g["pattern_size"]) >= 3,
              f"{g['pattern_size'][0]}x{g['pattern_size'][1]}")
        check(f"{name}: corner count matches the board",
              len(g["corners_qt"]) == (cols - 1) * (rows - 1))
        check(f"{name}: origin is a whole pixel",
              g["origin"] == [int(g["origin"][0]), int(g["origin"][1])],
              "so the squares land on pixel boundaries")

        qt = g["corners_qt"]
        centre = g["corners_pixel_centre"]
        offsets = {(round(a[0] - b[0], 6), round(a[1] - b[1], 6))
                   for a, b in zip(qt, centre)}
        check(f"{name}: pixel-centre corners are exactly half a pixel in",
              offsets == {(0.5, 0.5)},
              "Qt spans [x, x+1); a detector calls that pixel's centre x")
        check(f"{name}: corners are row-major from the top-left",
              qt[0][0] < qt[1][0] and qt[0][1] == qt[1][1]
              and qt[cols - 1][1] > qt[0][1],
              "the order findChessboardCornersSB reports them in")

    c = CalibrationManager()
    check("starts with the cluster drawn", not c.active and c.pattern == "")
    c.pattern = "checker"
    check("a pattern switches the cluster out", c.active)
    c.pattern = "not-a-pattern"
    check("an unknown pattern is refused", c.pattern == "checker")
    c.pattern = ""
    check("off puts the cluster back", not c.active)
    c.squarePx = 1
    check("clamps an absurd square", c.squarePx > 1)
    c.squarePx = DEFAULT_SQUARE_PX
    check("every listed pattern is a real one", "" in PATTERNS and "checker" in PATTERNS)

    exported = json.loads(c.exportJson(1790, 870))
    check("export carries the canvas it is for", exported["canvas"] == [1790, 870])
    check("export names the convention", "pixel-centre" in exported["note"]
          or "pixel column" in exported["note"])

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
