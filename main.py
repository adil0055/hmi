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
    --can BUS        bench mode: the cluster on an external CAN bus, driven by
                     whatever tester is on it (see backend/ecu.py)
    --restbus BUS    the panel sends its vehicle onto an external bus
    --frame-server N serve the cluster's framebuffer on port N, for testing
"""

from __future__ import annotations

import argparse
import os
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
    parser.add_argument("--can", nargs="?", const="udp_multicast", default="", metavar="BUS",
                        help="bench mode: the cluster listens on this bus, as a real one on "
                             "a tester does, and the panel does not drive it: "
                             "udp_multicast (virtual, no hardware), socketcan:vcan0, "
                             "pcan:PCAN_USBBUS1@500000, ...")
    parser.add_argument("--restbus", default="", metavar="BUS",
                        help="the panel sends the vehicle onto this bus (to drive a cluster "
                             "elsewhere, a real one included)")
    parser.add_argument("--direct", action="store_true",
                        help="no CAN at all: the panel sets the display directly (the old "
                             "way; also used when python-can is not installed)")
    parser.add_argument("--dbc", default="", metavar="FILE",
                        help="the CAN matrix (default can/cluster.dbc)")
    parser.add_argument("--frame-server", type=int, default=-1, metavar="PORT",
                        help="serve the cluster as drawn at http://127.0.0.1:PORT/frame.png "
                             "(0 picks a free port)")
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

    # Two models: the vehicle (the panel and the driving model, the cluster's
    # CAN partners) and the cluster's own display, which its ECU fills from
    # the bus and nothing else. --direct ties them into one.
    car = VehicleState()
    vehicle = VehicleState()
    if args.skin:
        car.skin = vehicle.skin = args.skin
    if args.calibration_export:
        canvas = (1920, 720) if vehicle.skin == "bmw" else (1790, 870)
        Path(args.calibration_export).write_text(
            calibration.exportJson(*canvas))
        print(f"wrote {args.calibration_export}")
    simulator = Simulator(car)
    ecu, restbuses, direct = None, [], args.direct
    if not direct:
        try:
            import can  # noqa: F401
            import cantools  # noqa: F401
        except ImportError as exc:
            print(f"note: no CAN ({exc}); the panel drives the display directly. "
                  "pip install -r requirements.txt for the cluster on CAN.", file=sys.stderr)
            direct = True
    if direct:
        vehicle = car
    else:
        from backend.bus import open_bus
        from backend.ecu import DEFAULT_DBC, ClusterEcu
        from backend.restbus import RestBus

        dbc = args.dbc or DEFAULT_DBC
        try:
            if args.can:
                cluster_bus = open_bus(args.can)
            else:
                import can
                channel = f"hmi-{os.getpid()}"
                cluster_bus = can.Bus(interface="virtual", channel=channel)
                restbuses.append(RestBus(car, can.Bus(interface="virtual", channel=channel), dbc))
            if args.restbus:
                restbuses.append(RestBus(car, open_bus(args.restbus), dbc))
            ecu = ClusterEcu(vehicle, cluster_bus, dbc, quick_boot=bool(args.screenshot))
        except Exception as exc:              # no adapter, bad DBC
            print(f"error: CAN: {exc}", file=sys.stderr)
            return 2
        # Settings of the cluster itself, not on the bus: which design it
        # draws (its coding), the bezel, and the units chosen in its menu.
        for prop in ("skin", "showBezel", "units", "consumptionUnits"):
            setattr(vehicle, prop, getattr(car, prop))
            getattr(car, prop + "Changed").connect(
                lambda prop=prop: setattr(vehicle, prop, getattr(car, prop)))

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))

    ctx = engine.rootContext()
    ctx.setContextProperty("Vehicle", vehicle)
    ctx.setContextProperty("Car", car)
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

    for rb in restbuses:
        rb.start()
    if ecu is not None:
        ecu.start()
        where = args.can or "an internal bus, driven by the panel"
        print(f"cluster: on {where}" + (f"; panel also sends on {args.restbus}"
                                        if args.restbus else ""), flush=True)

    frames = None
    if args.frame_server >= 0:
        from backend.frameserver import FrameServer
        root = engine.rootObjects()[0]
        frames = FrameServer(
            lambda: root.findChild(QQuickWindow, "clusterWindow") or root.property("cluster"),
            port=args.frame_server)
        frames.start()

    if args.screenshot:
        _schedule_screenshot(app, engine, args.screenshot, args.shot_delay)

    status = app.exec()
    for rb in restbuses:
        rb.stop(close=True)
    if ecu is not None:
        ecu.stop()
    if frames is not None:
        frames.stop()
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
