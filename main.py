#!/usr/bin/env python3
"""Car HMI — digital instrument cluster with a separate test input panel.

Run with::

    python3 main.py

Options::

    --no-panel       start without the control panel window
    --size-panel     also open the text-size panel
    --fullscreen     open the cluster full screen
    --scale N        force the cluster render scale (default: fit the screen)
    --screenshot F   render one frame to F and exit (works headless)
    --layout-panel   open the layout-fault panel
    --layout-shift   draw an element out of place on purpose, for testing
    --layout-reset   put every element back before starting
    --calibration P  draw a test pattern instead of the cluster
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from backend import (CalibrationManager, FontManager, LayoutManager, Simulator,
                     TextSizeManager, VehicleState)
from backend.calibration import PATTERNS
from backend.layout import parse_shift

ROOT = Path(__file__).resolve().parent
QML_DIR = ROOT / "qml"
FONT_DIR = ROOT / "assets" / "fonts"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Car HMI instrument cluster")
    parser.add_argument("--no-panel", action="store_true", help="hide the control panel")
    parser.add_argument("--size-panel", action="store_true",
                        help="also open the text-size panel")
    parser.add_argument("--fullscreen", action="store_true", help="cluster full screen")
    parser.add_argument("--scale", type=float, default=0.0, help="force render scale")
    parser.add_argument("--screenshot", default="", help="render one frame to a PNG and exit")
    parser.add_argument("--shot-delay", type=int, default=900, help="ms before --screenshot")
    parser.add_argument("--font", nargs="*", default=None, metavar="FILE",
                        help="font file(s) or a directory to use instead of the bundled one")
    parser.add_argument("--font-family", default="", metavar="ID",
                        help="start on a catalogue typeface (see assets/fonts/catalog.json)")
    parser.add_argument("--skin", default="", choices=["", "classic", "bmw"],
                        help="which cluster to draw (default: whichever was last used)")
    parser.add_argument("--text-scale", type=float, default=0.0, metavar="N",
                        help="scale every run of text (0.6..1.8); remembered, like the panel")
    parser.add_argument("--layout-panel", action="store_true",
                        help="also open the layout-fault panel")
    parser.add_argument("--layout-shift", nargs="*", default=[], metavar="ID=dx,dy",
                        help="draw an element out of place, in design px; also "
                             "ID=dx,dy,scale,rot and ID=hidden "
                             "(ids are in qml/Hmi/LayoutRoles.qml)")
    parser.add_argument("--layout-reset", action="store_true",
                        help="clear every stored layout fault before starting")
    parser.add_argument("--layout-export", default="", metavar="FILE",
                        help="write the commanded faults to FILE as JSON and carry on")
    parser.add_argument("--calibration", default="", choices=PATTERNS, metavar="PATTERN",
                        help="draw a test pattern instead of the cluster: "
                             + ", ".join(p for p in PATTERNS if p))
    parser.add_argument("--calibration-square", type=int, default=0, metavar="N",
                        help="chessboard square size in display px")
    parser.add_argument("--calibration-export", default="", metavar="FILE",
                        help="write the pattern's corner coordinates to FILE as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Car HMI Cluster")
    app.setOrganizationName("hmi")

    fonts = FontManager(FONT_DIR)
    if args.font:
        if len(args.font) == 1:
            fonts.loadPath(args.font[0])
        else:
            fonts.loadFiles(args.font)
        if fonts.status:
            print(fonts.status)
    elif args.font_family:
        if not fonts.selectFamily(args.font_family):
            names = ", ".join(entry["id"] for entry in fonts.catalog)
            print(f"error: unknown typeface {args.font_family!r}; try one of: {names}",
                  file=sys.stderr)
            return 2

    sizes = TextSizeManager()
    if args.text_scale:
        sizes.scale = args.text_scale

    layout = LayoutManager()
    if args.layout_reset:
        layout.resetAll()
    if args.layout_shift:
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
        print(f"wrote {args.layout_export}")
    # Loud on purpose: a cluster quietly drawing three pixels out because
    # somebody left it that way last week is the kind of thing that gets
    # diagnosed for a fortnight as a camera fault.
    warning = layout.summary()
    if warning:
        print(warning, file=sys.stderr)

    calibration = CalibrationManager()
    if args.calibration_square:
        calibration.squarePx = args.calibration_square
    if args.calibration:
        calibration.pattern = args.calibration

    vehicle = VehicleState()
    if args.skin:
        vehicle.skin = args.skin
    if args.calibration_export:
        canvas = (1920, 720) if vehicle.skin == "bmw" else (1790, 870)
        Path(args.calibration_export).write_text(
            calibration.exportJson(*canvas))
        print(f"wrote {args.calibration_export}")
    simulator = Simulator(vehicle)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))

    ctx = engine.rootContext()
    ctx.setContextProperty("Vehicle", vehicle)
    ctx.setContextProperty("Fonts", fonts)
    ctx.setContextProperty("Sizes", sizes)
    # Not "Layout": QtQuick.Layouts already attaches that name, and the panel
    # imports it.
    ctx.setContextProperty("LayoutFaults", layout)
    ctx.setContextProperty("Calibration", calibration)
    ctx.setContextProperty("appAssetPath", QUrl.fromLocalFile(str(ROOT / "assets")).toString())
    ctx.setContextProperty("appShowPanel", not args.no_panel)
    ctx.setContextProperty("appShowSizePanel", args.size_panel)
    ctx.setContextProperty("appShowLayoutPanel", args.layout_panel)
    ctx.setContextProperty("appFullscreen", args.fullscreen)
    ctx.setContextProperty("appForcedScale", float(args.scale))

    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        print("error: failed to load qml/Main.qml", file=sys.stderr)
        return 1

    simulator.start()

    if args.screenshot:
        _schedule_screenshot(app, engine, args.screenshot, args.shot_delay)

    status = app.exec()
    # Tear the QML down first: its bindings reference the model objects, and
    # evaluating them after those are gone logs spurious errors on exit.
    del engine
    return status


def _schedule_screenshot(app, engine, target: str, delay_ms: int) -> None:
    """Grab the cluster window once it has settled, then quit."""

    def grab() -> None:
        # QGuiApplication.allWindows() hands back plain QWindow handles, which
        # have no grabWindow(); go through the QML object tree instead.
        try:
            root = engine.rootObjects()[0]
            cluster = root.findChild(QQuickWindow, "clusterWindow") or root.property("cluster")
            if cluster is None:
                print("error: could not find the cluster window", file=sys.stderr)
            else:
                image = cluster.grabWindow()
                image.save(target)
                print(f"saved {target} ({image.width()}x{image.height()})")
        finally:
            app.quit()

    QTimer.singleShot(delay_ms, grab)


if __name__ == "__main__":
    raise SystemExit(main())
