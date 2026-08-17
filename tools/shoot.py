#!/usr/bin/env python3
"""Render the cluster to a PNG without opening a window.

Useful for eyeballing changes over SSH and for capturing before/after shots::

    python3 tools/shoot.py out.png
    python3 tools/shoot.py driving.png --set speed=118 rpm=3450 gearMode=D \
        headlightMode=2 turnLeft=true fuelLevel=0.55 coolantTemp=92

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

from backend import FontManager, VehicleState  # noqa: E402


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
    args = parser.parse_args()

    app = QGuiApplication(sys.argv[:1])

    # persist=False: taking a screenshot must not change the app's saved font.
    fonts = FontManager(ROOT / "assets" / "fonts", persist=False)
    if args.font:
        ok = fonts.loadPath(args.font[0]) if len(args.font) == 1 else fonts.loadFiles(args.font)
        print(fonts.status)
        if not ok:
            return 2

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
    ctx.setContextProperty("appAssetPath", QUrl.fromLocalFile(str(ROOT / "assets")).toString())

    view.setSource(QUrl.fromLocalFile(str(ROOT / "qml" / "Hmi" / "ShootHarness.qml")))
    if view.status() != QQuickView.Ready:
        for err in view.errors():
            print(err.toString(), file=sys.stderr)
        return 1

    height = round(args.width * 870 / 1790)
    view.resize(QSize(args.width, height))
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
