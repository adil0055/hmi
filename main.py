#!/usr/bin/env python3
"""Car HMI — digital instrument cluster with a separate test input panel.

Run with::

    python3 main.py

Options::

    --no-panel       start without the control panel window
    --fullscreen     open the cluster full screen
    --scale N        force the cluster render scale (default: fit the screen)
    --screenshot F   render one frame to F and exit (works headless)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from backend import FontManager, Simulator, VehicleState

ROOT = Path(__file__).resolve().parent
QML_DIR = ROOT / "qml"
FONT_DIR = ROOT / "assets" / "fonts"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Car HMI instrument cluster")
    parser.add_argument("--no-panel", action="store_true", help="hide the control panel")
    parser.add_argument("--fullscreen", action="store_true", help="cluster full screen")
    parser.add_argument("--scale", type=float, default=0.0, help="force render scale")
    parser.add_argument("--screenshot", default="", help="render one frame to a PNG and exit")
    parser.add_argument("--shot-delay", type=int, default=900, help="ms before --screenshot")
    parser.add_argument("--font", nargs="*", default=None, metavar="FILE",
                        help="font file(s) or a directory to use instead of the bundled one")
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

    vehicle = VehicleState()
    simulator = Simulator(vehicle)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))

    ctx = engine.rootContext()
    ctx.setContextProperty("Vehicle", vehicle)
    ctx.setContextProperty("Fonts", fonts)
    ctx.setContextProperty("appAssetPath", QUrl.fromLocalFile(str(ROOT / "assets")).toString())
    ctx.setContextProperty("appShowPanel", not args.no_panel)
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
