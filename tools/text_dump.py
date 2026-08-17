#!/usr/bin/env python3
"""Render one cluster frame and dump every piece of text it drew.

`tools/shoot.py` gives you the pixels.  This gives you the pixels *and* the
ground truth behind them: for every `Text` item the scene actually painted,
the string, where it landed in image coordinates, and which typeface Qt
resolved it to.

That pairing is what makes the display testable from the outside.  A camera
rig looking at the cluster has to answer two questions — "does it say the
right thing" and "is it in the right typeface" — and neither can be marked
without knowing what the renderer intended.

    python3 tools/text_dump.py frame.png --json frame.json \
        --set speed=118 rpm=3450 gearMode=D --font ~/fonts/Inter-Regular.ttf

The `resolvedFamily` field is worth a second look.  Qt does not fail when a
requested family is missing, it silently substitutes another one, so a frame
whose `requestedFamily` and `resolvedFamily` disagree is a cluster that is
lying about its own branding.  The corpus generator treats that as a first
class result rather than an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QSize, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QFontInfo, QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402

from backend import FontManager, VehicleState  # noqa: E402

#: Qt's class name for a QML `Text` item.  PySide does not export the type, so
#: the item tree is walked by metaobject name instead of isinstance.
#:
#: Matching has to follow the inheritance chain, not just the leaf name.  A
#: `Text` carrying its own bindings gets a generated subclass — the tick-ring
#: numerals come through as `QQuickText_QML_20` — and an exact-name test would
#: silently drop exactly the glyph-rich items this corpus exists to capture.
TEXT_BASE_CLASS = "QQuickText"

#: Below this an item contributes no readable ink, so it is not ground truth.
MIN_OPACITY = 0.05


def coerce(text: str):
    """Parse a --set value as bool / int / float / str, in that order."""
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def is_text_item(item) -> bool:
    """True when `item` is a QML Text, including generated subclasses."""
    meta = item.metaObject()
    while meta is not None:
        if meta.className() == TEXT_BASE_CLASS:
            return True
        meta = meta.superClass()
    return False


def effective_opacity(item) -> float:
    """Opacity including every ancestor's, which is what the eye actually sees."""
    value = 1.0
    node = item
    while node is not None:
        value *= float(node.opacity())
        node = node.parentItem()
    return value


def scene_rect(item) -> list[float]:
    """Item bounds in image pixels.

    All four corners are mapped rather than just the origin: the harness scales
    the design canvas to the view, and rotated tick numerals would otherwise
    report a box that does not contain their own ink.
    """
    w, h = float(item.width()), float(item.height())
    corners = [item.mapToScene(QPointF(x, y))
               for x, y in ((0, 0), (w, 0), (w, h), (0, h))]
    xs = [p.x() for p in corners]
    ys = [p.y() for p in corners]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def describe_text(item) -> dict:
    """Everything about one painted string that a checker downstream needs."""
    font = item.property("font")
    info = QFontInfo(font) if font is not None else None
    colour = item.property("color")

    return {
        "text": item.property("text") or "",
        "rect": [round(v, 2) for v in scene_rect(item)],
        "requestedFamily": font.family() if font is not None else "",
        # What Qt really used.  Differs from the above whenever the requested
        # family is missing and Qt quietly substituted something else.
        "resolvedFamily": info.family() if info is not None else "",
        "pixelSize": info.pixelSize() if info is not None else -1,
        "italic": bool(font.italic()) if font is not None else False,
        "weight": int(font.weight().value) if font is not None else -1,
        "letterSpacing": round(float(font.letterSpacing()), 3) if font is not None else 0.0,
        "colour": colour.name() if colour is not None else "",
        "opacity": round(effective_opacity(item), 3),
        "objectName": item.objectName() or "",
    }


def collect_texts(root) -> list[dict]:
    """Walk the item tree and describe every visible, non-empty Text item."""
    found: list[dict] = []

    def walk(item) -> None:
        for child in item.childItems():
            walk(child)
        if not is_text_item(item):
            return
        if not item.isVisible() or effective_opacity(item) < MIN_OPACITY:
            return
        if not (item.property("text") or "").strip():
            return
        if item.width() <= 0 or item.height() <= 0:
            return
        found.append(describe_text(item))

    walk(root)
    # Reading order, so a diff between two frames stays legible.
    found.sort(key=lambda d: (round(d["rect"][1], 1), round(d["rect"][0], 1)))
    return found


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", help="PNG path to write")
    parser.add_argument("--json", help="where to write the text inventory")
    parser.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE",
                        help="vehicle properties to apply before rendering")
    parser.add_argument("--width", type=int, default=1790)
    parser.add_argument("--delay", type=int, default=700, help="ms to let the scene settle")
    parser.add_argument("--font", nargs="*", default=None, metavar="FILE",
                        help="font file(s) or a directory to render with")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    app = QGuiApplication(sys.argv[:1])

    # persist=False: a capture run must not change the app's saved font.
    fonts = FontManager(ROOT / "assets" / "fonts", persist=False)
    font_ok = True
    if args.font:
        font_ok = fonts.loadPath(args.font[0]) if len(args.font) == 1 else fonts.loadFiles(args.font)
        print(fonts.status)
        if not font_ok:
            return 2

    vehicle = VehicleState()
    applied: dict[str, object] = {}
    for pair in args.set:
        if "=" not in pair:
            print(f"error: expected KEY=VALUE, got {pair!r}", file=sys.stderr)
            return 2
        key, _, raw = pair.partition("=")
        if not vehicle.metaObject().property(vehicle.metaObject().indexOfProperty(key)).isValid():
            print(f"error: unknown vehicle property {key!r}", file=sys.stderr)
            return 2
        value = coerce(raw)
        setattr(vehicle, key, value)
        applied[key] = value

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

    status = {"code": 0}

    def grab() -> None:
        image = view.grabWindow()
        image.save(args.output)

        if args.json:
            texts = collect_texts(view.rootObject())
            payload = {
                "image": Path(args.output).name,
                "size": [image.width(), image.height()],
                "scale": round(image.width() / 1790.0, 6),
                "font": {
                    "requested": list(args.font or []),
                    "family": fonts.family,
                    "status": fonts.status,
                    "isCustom": bool(fonts.isCustom),
                },
                "state": applied,
                "texts": texts,
            }
            Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"wrote {args.json} ({len(texts)} text items)")

        print(f"saved {args.output} ({image.width()}x{image.height()})")
        app.quit()

    QTimer.singleShot(args.delay, grab)
    app.exec()
    return status["code"]


if __name__ == "__main__":
    raise SystemExit(main())
