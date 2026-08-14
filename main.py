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
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from backend import Simulator, VehicleState

ROOT = Path(__file__).resolve().parent
QML_DIR = ROOT / "qml"
FONT_DIR = ROOT / "assets" / "fonts"


def load_fonts() -> str:
    """Register the bundled fonts; return the family to use for the cluster."""
    family = ""
    for path in sorted(FONT_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families and not family:
            family = families[0]
    if not family:
        # Bundled fonts missing: fall back to whatever the system offers.
        for candidate in ("Titillium Web", "Roboto", "Open Sans", "DejaVu Sans"):
            if candidate in QFontDatabase.families():
                return candidate
        return "sans-serif"
    return family


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Car HMI instrument cluster")
    parser.add_argument("--no-panel", action="store_true", help="hide the control panel")
    parser.add_argument("--fullscreen", action="store_true", help="cluster full screen")
    parser.add_argument("--scale", type=float, default=0.0, help="force render scale")
    parser.add_argument("--screenshot", default="", help="render one frame to a PNG and exit")
    parser.add_argument("--shot-delay", type=int, default=900, help="ms before --screenshot")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Car HMI Cluster")
    app.setOrganizationName("hmi")

    font_family = load_fonts()

    vehicle = VehicleState()
    simulator = Simulator(vehicle)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))

    ctx = engine.rootContext()
    ctx.setContextProperty("Vehicle", vehicle)
    ctx.setContextProperty("appFontFamily", font_family)
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

    return app.exec()


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
