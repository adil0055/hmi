"""Test patterns for working out where the display is, from a camera.

A camera-based check of the cluster has to map camera pixels onto display
pixels before any of its numbers mean anything, and how well it does that sets
the accuracy of everything downstream.  The most direct way to establish it is
for the cluster to draw the pattern itself: then the correspondence between
framebuffer coordinates and camera coordinates is exact and known, rather than
inferred from the bezel or from the artwork.

That costs the HMI one diagnostic screen and saves the rig owner the whole
problem, so it lives here.

Patterns:

``checker``
    A chessboard.  What ``cv2.findChessboardCornersSB`` and friends want.  The
    inner corners are the correspondence points, and this module is the one
    place their coordinates are worked out — QML draws from the same geometry,
    so the drawing and the exported coordinates cannot drift apart.
``white`` / ``black``
    Flat fields.  ``white`` is what an edge-fitting approach needs to find the
    active area; the pair together also give a flat-field and a dark frame for
    anyone characterising the camera.
``grid``
    A one-pixel rule every square, for eyeballing distortion and focus across
    the panel without measuring anything.
``crosshair``
    Four corner crosses and a centre cross, at exact coordinates.  A sanity
    check with far fewer points than the chessboard, and the one to reach for
    when the chessboard will not detect and you need to know why.

A note on the half pixel, because it is worth more than it looks.  Qt places an
item at x with its left edge on the boundary *before* pixel column x, so pixel
column x spans Qt coordinates [x, x+1) and its centre is at x+0.5.  Image
libraries index that same pixel as column x with its centre *at* x.  A board
boundary drawn at Qt coordinate X therefore sits at X-0.5 in the coordinates
the detector reports.  Both are exported, named, because quietly picking the
wrong one puts half a pixel of systematic error into the homography and from
there into every measurement taken through it.
"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

#: The patterns, in the order a panel should list them.
PATTERNS = ("", "checker", "white", "black", "grid", "crosshair")

#: Square size that lands a sensible number of corners on either canvas.  Big
#: squares detect more reliably and refine more accurately than many small
#: ones, which is the opposite of the instinct.
DEFAULT_SQUARE_PX = 100

MIN_SQUARE_PX = 20
MAX_SQUARE_PX = 400


def pattern_geometry(
    canvas_w: int, canvas_h: int, square_px: int = DEFAULT_SQUARE_PX
) -> dict[str, Any]:
    """Where the chessboard goes on a ``canvas_w`` x ``canvas_h`` framebuffer.

    One square of quiet zone is left on every side: a board running to the edge
    of the panel gives the detector nothing to separate the outer squares from
    whatever is beyond the glass, and it will refuse the frame rather than
    return worse corners.

    The board is centred, and the origin is rounded to a whole pixel so the
    squares land on pixel boundaries and the exported corners are exact rather
    than nearly exact.
    """
    square = int(max(MIN_SQUARE_PX, min(MAX_SQUARE_PX, square_px)))
    cols = max(3, (canvas_w - 2 * square) // square)
    rows = max(3, (canvas_h - 2 * square) // square)
    origin_x = int(round((canvas_w - cols * square) / 2.0))
    origin_y = int(round((canvas_h - rows * square) / 2.0))

    # Inner corners, row-major from the top-left, which is the order
    # findChessboardCornersSB reports them in.
    corners_qt = [
        [origin_x + i * square, origin_y + j * square]
        for j in range(1, rows)
        for i in range(1, cols)
    ]
    return {
        "square_px": square,
        "cols": cols,
        "rows": rows,
        "origin": [origin_x, origin_y],
        "canvas": [int(canvas_w), int(canvas_h)],
        # (inner corners per row, per column) — the pattern_size a detector takes.
        "pattern_size": [cols - 1, rows - 1],
        "corners_qt": corners_qt,
        "corners_pixel_centre": [[x - 0.5, y - 0.5] for x, y in corners_qt],
        "note": (
            "corners_pixel_centre is the one to feed a detector: it is in the "
            "convention where pixel column x has its centre at x, which is what "
            "OpenCV and NumPy use. corners_qt is the same points in Qt item "
            "coordinates, where a pixel spans [x, x+1)."
        ),
    }


class CalibrationManager(QObject):
    """Which test pattern the cluster is drawing, if any."""

    calibrationChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pattern = ""
        self._square = DEFAULT_SQUARE_PX

    # ------------------------------------------------------------- properties
    def _get_pattern(self) -> str:
        return self._pattern

    def _set_pattern(self, value: str) -> None:
        value = str(value or "")
        if value not in PATTERNS:
            return
        if value != self._pattern:
            self._pattern = value
            self.calibrationChanged.emit()

    def _get_square(self) -> int:
        return self._square

    def _set_square(self, value: int) -> None:
        value = int(max(MIN_SQUARE_PX, min(MAX_SQUARE_PX, int(value))))
        if value != self._square:
            self._square = value
            self.calibrationChanged.emit()

    def _get_active(self) -> bool:
        return bool(self._pattern)

    #: "" draws the cluster; anything else replaces it with that test pattern.
    pattern = Property(str, _get_pattern, _set_pattern, notify=calibrationChanged)
    squarePx = Property(int, _get_square, _set_square, notify=calibrationChanged)
    #: Whether the cluster is showing a pattern instead of itself.
    active = Property(bool, _get_active, notify=calibrationChanged)

    # ---------------------------------------------------------------- reading
    @Slot(int, int, result="QVariantMap")
    def geometry(self, canvas_w: int, canvas_h: int) -> dict:
        """Board geometry for a canvas.  QML draws from exactly this."""
        return pattern_geometry(canvas_w, canvas_h, self._square)

    @Slot(int, int, result=str)
    def exportJson(self, canvas_w: int, canvas_h: int) -> str:
        """The geometry, for the rig that is about to solve a homography."""
        data = pattern_geometry(canvas_w, canvas_h, self._square)
        data["pattern"] = self._pattern or "checker"
        return json.dumps(data, indent=2)
