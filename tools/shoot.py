#!/usr/bin/env python3
"""Render the cluster to a PNG without opening a window.

Useful for eyeballing changes over SSH and for capturing before/after shots::

    python3 tools/shoot.py out.png
    python3 tools/shoot.py driving.png --set speed=118 rpm=3450 gearMode=D \
        headlightMode=2 turnLeft=true fuelLevel=0.55 coolantTemp=92

Elements can be drawn deliberately out of place, which is how something
watching the cluster gets shown a displacement it can be scored against::

    python3 tools/shoot.py faulty.png --layout-shift classic.dial.speed=3,1.25 \
        --layout-export faulty.json

Values are parsed as bool / int / float / str in that order.  The simulator is
not started, so whatever you set is exactly what gets drawn.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSize, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402

from backend import (CalibrationManager, FontManager,  # noqa: E402
                     LayoutManager, TextSizeManager, VehicleState)
from backend.calibration import PATTERNS  # noqa: E402
from backend.layout import parse_shift  # noqa: E402


def coerce(text: str):
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="PNG path to write")
    parser.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE",
                        help="vehicle properties to apply before rendering")
    parser.add_argument("--width", type=int, default=1790)
    parser.add_argument("--delay", type=int, default=700, help="ms to let the scene settle")
    parser.add_argument("--font", nargs="*", default=None, metavar="FILE",
                        help="font file(s) or a directory to render with")
    parser.add_argument("--font-family", default="", metavar="ID",
                        help="render with a catalogue typeface (see assets/fonts/catalog.json)")
    parser.add_argument("--text-scale", type=float, default=1.0, metavar="N",
                        help="scale every run of text (0.6..1.8)")
    parser.add_argument("--text-size", nargs="*", default=[], metavar="ID=SIZE",
                        help="size one run of text (ids are in qml/Hmi/TextSizes.qml)")
    parser.add_argument("--layout-shift", nargs="*", default=[], metavar="ID=dx,dy",
                        help="draw an element out of place, in design px; also "
                             "ID=dx,dy,scale,rot and ID=hidden "
                             "(ids are in qml/Hmi/LayoutRoles.qml)")
    parser.add_argument("--layout-export", default="", metavar="FILE",
                        help="write the commanded faults beside the shot, as JSON")
    parser.add_argument("--calibration", default="", choices=PATTERNS, metavar="PATTERN",
                        help="shoot a test pattern instead of the cluster: "
                             + ", ".join(p for p in PATTERNS if p))
    parser.add_argument("--calibration-square", type=int, default=0, metavar="N",
                        help="chessboard square size in display px")
    parser.add_argument("--calibration-export", default="", metavar="FILE",
                        help="write the pattern's corner coordinates to FILE as JSON")
    args = parser.parse_args()

    app = QGuiApplication(sys.argv[:1])

    # persist=False: taking a screenshot must not change the app's saved font.
    fonts = FontManager(ROOT / "assets" / "fonts", persist=False)
    if args.font:
        ok = fonts.loadPath(args.font[0]) if len(args.font) == 1 else fonts.loadFiles(args.font)
        print(fonts.status)
        if not ok:
            return 2
    elif args.font_family:
        if not fonts.selectFamily(args.font_family):
            names = ", ".join(entry["id"] for entry in fonts.catalog)
            print(f"error: unknown typeface {args.font_family!r}; try: {names}", file=sys.stderr)
            return 2

    # persist=False here too: a screenshot must not rewrite the saved sizes.
    sizes = TextSizeManager(persist=False)
    sizes.scale = args.text_scale
    overrides = {}
    for pair in args.text_size:
        key, _, raw = pair.partition("=")
        try:
            overrides[key] = float(raw)
        except ValueError:
            print(f"error: expected ID=SIZE, got {pair!r}", file=sys.stderr)
            return 2
    sizes.setOverrides(overrides)

    # persist=False as above: a shot must not leave the app drawing crooked.
    layout = LayoutManager(persist=False)
    faults = {}
    for term in args.layout_shift:
        try:
            role_id, entry = parse_shift(term)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        faults[role_id] = entry
    layout.setFaults(faults)
    if args.layout_export:
        Path(args.layout_export).write_text(layout.exportJson())

    calibration = CalibrationManager()
    if args.calibration_square:
        calibration.squarePx = args.calibration_square
    if args.calibration:
        calibration.pattern = args.calibration

    vehicle = VehicleState()
    for pair in args.set:
        if "=" not in pair:
            print(f"error: expected KEY=VALUE, got {pair!r}", file=sys.stderr)
            return 2
        key, _, raw = pair.partition("=")
        if not vehicle.metaObject().property(vehicle.metaObject().indexOfProperty(key)).isValid():
            print(f"error: unknown vehicle property {key!r}", file=sys.stderr)
            return 2
        setattr(vehicle, key, coerce(raw))

    view = QQuickView()
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.engine().addImportPath(str(ROOT / "qml"))
    ctx = view.engine().rootContext()
    ctx.setContextProperty("Vehicle", vehicle)
    ctx.setContextProperty("Fonts", fonts)
    ctx.setContextProperty("Sizes", sizes)
    ctx.setContextProperty("LayoutFaults", layout)
    ctx.setContextProperty("Calibration", calibration)
    ctx.setContextProperty("appAssetPath", QUrl.fromLocalFile(str(ROOT / "assets")).toString())

    view.setSource(QUrl.fromLocalFile(str(ROOT / "qml" / "Hmi" / "ShootHarness.qml")))
    if view.status() != QQuickView.Ready:
        for err in view.errors():
            print(err.toString(), file=sys.stderr)
        return 1

    # The two skins are drawn on different canvases, so the view has to take
    # its aspect from whichever one is about to be rendered.
    canvas = (1920, 720) if vehicle.skin == "bmw" else (1790, 870)
    if args.calibration_export:
        Path(args.calibration_export).write_text(calibration.exportJson(*canvas))
    view.resize(QSize(args.width, round(args.width * canvas[1] / canvas[0])))
    view.show()

    def grab() -> None:
        image = view.grabWindow()
        image.save(args.output)
        print(f"saved {args.output} ({image.width()}x{image.height()})")
        app.quit()

    QTimer.singleShot(args.delay, grab)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
