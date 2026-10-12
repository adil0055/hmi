#!/usr/bin/env python3
"""Check the telltale strip: a flashing lamp keeps its slot through the flash.

Renders the cluster twice, headless, with the flash on and off, and checks
that only the flashing lamp's own slot changes::

    python3 tools/telltale_test.py

A flashing lamp used to leave the strip on its dark half, and every lamp
after it moved a slot sideways and back with every flash.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from PySide6.QtGui import QImage  # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


def shoot(path: Path, *settings: str) -> QImage:
    env = dict(os.environ, QT_QPA_PLATFORM=os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    subprocess.run([sys.executable, str(ROOT / "tools" / "shoot.py"), str(path),
                    "--set", *settings], check=True, env=env, capture_output=True)
    return QImage(str(path))


def changed_columns(a: QImage, b: QImage, rows: range) -> list[int]:
    cols = []
    for x in range(a.width()):
        if any(a.pixel(x, y) != b.pixel(x, y) for y in rows):
            cols.append(x)
    return cols


def main() -> int:
    lit = ["beltDriver=false", "brakeSystem=true", "absFault=true", "rearFog=true"]
    with tempfile.TemporaryDirectory() as tmp:
        on = shoot(Path(tmp) / "on.png", *lit, "blinkOn=true")
        off = shoot(Path(tmp) / "off.png", *lit, "blinkOn=false")
        rest = shoot(Path(tmp) / "rest.png", "blinkOn=false")
    print("a flashing lamp in a strip of four")
    strip = range(60, 160)
    cols = changed_columns(on, off, strip)
    width = (cols[-1] - cols[0] + 1) if cols else 0
    lamp = len(changed_columns(rest, off, strip))
    check("the flash changes something", bool(cols))
    check("only one lamp's width changes between the flash's halves", 0 < width <= 50,
          f"{width} px wide")
    check("the other three lamps are lit both times", lamp > 2 * width, f"{lamp} px of lamps")

    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
