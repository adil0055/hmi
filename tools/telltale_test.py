#!/usr/bin/env python3
"""Check the telltale bank: every lamp has a fixed slot of its own.

Renders the cluster headless, in both designs, with lamps lit alone, lit
together with others, flashing, and all lit for the bulb check, and checks::

    python3 tools/telltale_test.py

- a lamp is drawn at exactly the same pixels whether it is the only one lit,
  one of several, or in the bulb check with all of them;
- a flashing lamp changes nothing but its own slot between the flash's halves;
- with every lamp lit, the bank draws only on empty display: it never covers
  the gear letter, the range, a dial or the media tile.

The lamps once sat in a strip that only made room for the lit ones: a lamp
moved sideways whenever one before it came on, and the bulb check's third
row ran into the gear letter.
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
# Where the bank is, with room to spare, in rendered pixels (width 1790).
BANK_ROWS = range(0, 230)
EMPTY = 60          # brighter than this (max channel) is something drawn


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


class Frame:
    """A rendered image as rows of RGB32 pixels."""

    def __init__(self, path: Path) -> None:
        img = QImage(str(path)).convertToFormat(QImage.Format.Format_RGB32)
        self.w, self.h = img.width(), img.height()
        data = bytes(img.constBits())
        stride = img.bytesPerLine()
        self.rows = [data[y * stride:y * stride + self.w * 4] for y in range(self.h)]

    def px(self, x: int, y: int) -> tuple[int, int, int]:
        b, g, r = self.rows[y][4 * x:4 * x + 3]
        return r, g, b


def shoot(path: Path, *settings: str) -> Frame:
    env = dict(os.environ, QT_QPA_PLATFORM=os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    # Long enough for the BMW wake-up sweep (1.4 s) to finish.
    subprocess.run([sys.executable, str(ROOT / "tools" / "shoot.py"), str(path),
                    "--delay", "2000", "--set", *settings],
                   check=True, env=env, capture_output=True)
    return Frame(path)


def changed(a: Frame, b: Frame, rows=BANK_ROWS, box=None) -> list[tuple[int, int]]:
    x0, y0, x1, y1 = box or (0, rows.start, a.w, rows.stop)
    out = []
    for y in range(y0, y1):
        ra, rb = a.rows[y], b.rows[y]
        if ra[4 * x0:4 * x1] == rb[4 * x0:4 * x1]:
            continue
        for x in range(x0, x1):
            if ra[4 * x:4 * x + 3] != rb[4 * x:4 * x + 3]:
                out.append((x, y))
    return out


def bbox(points) -> tuple[int, int, int, int] | None:
    if not points:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def same(a: Frame, b: Frame, box) -> bool:
    return not changed(a, b, box=box)


def skin(name: str, tmp: Path) -> None:
    print(f"{name}")
    base = [f"skin={name}", "blinkOn=true"]
    rest = shoot(tmp / "rest.png", *base)
    alone = {
        "ABS": shoot(tmp / "abs.png", *base, "absFault=true"),
        "high beam": shoot(tmp / "hb.png", *base, "highBeam=true"),
        "lane departure": shoot(tmp / "ldw.png", *base, "ldwEnabled=true"),
    }
    many_set = ["beltDriver=false", "brakeSystem=true", "parkBrake=true", "absFault=true",
                "rearFog=true", "highBeam=true", "ldwEnabled=true", "cruiseEnabled=true",
                "checkEngine=true", "flashing=,seatbelt,"]
    many = shoot(tmp / "many.png", *base, *many_set)
    dark = shoot(tmp / "dark.png", *base, *many_set, "blinkOn=false")
    every = shoot(tmp / "check.png", *base, "power=check")
    belt = bbox(changed(rest, shoot(tmp / "belt.png", *base, "beltDriver=false")))

    for lamp, frame in alone.items():
        box = bbox(changed(rest, frame))
        if box is None:
            check(f"{lamp} lights", False)
            continue
        check(f"{lamp}: the same pixels alone, among others and in the bulb check",
              same(frame, many, box) and same(frame, every, box), f"slot {box}")

    flash = bbox(changed(many, dark))
    inside = (flash is not None and belt is not None and belt[0] <= flash[0]
              and belt[1] <= flash[1] and flash[2] <= belt[2] and flash[3] <= belt[3])
    check("a flashing lamp changes only its own slot", inside, f"{flash} within {belt}")

    lit = changed(rest, every)
    covered = [(x, y) for x, y in lit if max(rest.px(x, y)) > EMPTY]
    check("the bulb check draws only on empty display", not covered,
          f"{len(covered)} px over something, e.g. {covered[:3]}" if covered
          else f"bank {bbox(lit)}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("classic", "bmw"):
            skin(name, Path(tmp))
    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
