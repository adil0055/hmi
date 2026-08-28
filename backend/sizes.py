"""How big the cluster sets its text, and remembering that between runs.

The companion to :mod:`backend.fonts`.  Once the typeface became switchable
its size had to follow: the catalogue spans faces whose figures differ by half
again in width and by a sixth in apparent size, and no single set of sizes
suits all of them.  So the artwork's sizes became defaults rather than
constants.

Two knobs, deliberately kept apart:

``scale``
    one multiplier over every run of text at once, for "this face is
    small — bring the whole cluster up a bit";
``overrides``
    a design size for one named run, for "the trip figures specifically are
    too heavy now".

Both are stored here rather than in QML for the same reason the font choice
is: this object owns the QSettings write, and Main.qml pushes the result into
the ``TextSizes`` singleton.  The *catalogue* of runs is not here — it lives in
qml/Hmi/TextSizes.qml beside the artwork it describes, and this class never
needs to know what the ids mean, only what the user has said about them.
"""

from __future__ import annotations

import json

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

#: Range the scale is clamped to.  Below the low end the cluster is unreadable
#: and above the high end the readouts overrun their slots, and neither is a
#: state worth persisting into the next run.
MIN_SCALE = 0.6
MAX_SCALE = 1.8

#: Range a single override is clamped to, in design pixels.
MIN_SIZE = 6.0
MAX_SIZE = 320.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class TextSizeManager(QObject):
    """Global text scale plus per-run size overrides, persisted."""

    sizesChanged = Signal()

    def __init__(self, persist: bool = True, parent: QObject | None = None) -> None:
        """`persist` off keeps a run from touching the saved sizes, which is
        what one-shot tools such as tools/shoot.py want."""
        super().__init__(parent)
        self._persist = persist
        self._scale = 1.0
        self._overrides: dict[str, float] = {}
        if persist:
            self._restore()

    # ------------------------------------------------------------- properties
    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, value: float) -> None:
        value = round(_clamp(float(value), MIN_SCALE, MAX_SCALE), 3)
        if value != self._scale:
            self._scale = value
            self._save()
            self.sizesChanged.emit()

    def _get_overrides(self) -> dict:
        return dict(self._overrides)

    def _get_count(self) -> int:
        return len(self._overrides)

    def _get_modified(self) -> bool:
        return bool(self._overrides) or self._scale != 1.0

    scale = Property(float, _get_scale, _set_scale, notify=sizesChanged)
    overrides = Property("QVariantMap", _get_overrides, notify=sizesChanged)
    #: How many runs have been moved off the size they were drawn at.
    overrideCount = Property(int, _get_count, notify=sizesChanged)
    #: Whether anything at all differs from the artwork, for a "Reset" button.
    modified = Property(bool, _get_modified, notify=sizesChanged)

    # ---------------------------------------------------------------- editing
    @Slot(str, float)
    def setSize(self, role_id: str, value: float) -> None:
        """Pin `role_id` to `value` design pixels, before the global scale."""
        if not role_id:
            return
        value = round(_clamp(float(value), MIN_SIZE, MAX_SIZE), 2)
        if self._overrides.get(role_id) == value:
            return
        self._overrides[role_id] = value
        self._save()
        self.sizesChanged.emit()

    @Slot(str)
    def resetSize(self, role_id: str) -> None:
        """Put `role_id` back to the size the artwork was drawn at."""
        if self._overrides.pop(role_id, None) is None:
            return
        self._save()
        self.sizesChanged.emit()

    @Slot(str, result=float)
    def sizeOf(self, role_id: str) -> float:
        """The override on `role_id`, or 0 if it is still on its drawn size."""
        return float(self._overrides.get(role_id, 0.0))

    @Slot(str, result=bool)
    def isOverridden(self, role_id: str) -> bool:
        return role_id in self._overrides

    @Slot()
    def resetAll(self) -> None:
        """Drop every override and put the scale back to 1."""
        if not self._overrides and self._scale == 1.0:
            return
        self._overrides.clear()
        self._scale = 1.0
        self._save()
        self.sizesChanged.emit()

    @Slot("QVariantMap")
    def setOverrides(self, values) -> None:
        """Replace the whole override set, for --text-size and tests."""
        cleaned = {}
        for key, value in dict(values or {}).items():
            try:
                cleaned[str(key)] = round(_clamp(float(value), MIN_SIZE, MAX_SIZE), 2)
            except (TypeError, ValueError):
                continue
        if cleaned == self._overrides:
            return
        self._overrides = cleaned
        self._save()
        self.sizesChanged.emit()

    # ------------------------------------------------------------ persistence
    def _save(self) -> None:
        if not self._persist:
            return
        settings = QSettings("hmi", "cluster")
        settings.setValue("textScale", self._scale)
        # Stored as JSON rather than as a map: QSettings round-trips nested
        # values differently per backend, and reading a size back as the string
        # "36" would silently give every face a 36-pixel-wide surprise.
        if self._overrides:
            settings.setValue("textSizes", json.dumps(self._overrides))
        else:
            settings.remove("textSizes")

    def _restore(self) -> None:
        settings = QSettings("hmi", "cluster")
        try:
            self._scale = _clamp(float(settings.value("textScale", 1.0)), MIN_SCALE, MAX_SCALE)
        except (TypeError, ValueError):
            self._scale = 1.0
        raw = settings.value("textSizes", "")
        if not raw:
            return
        try:
            stored = json.loads(raw)
        except (TypeError, ValueError):
            return
        if isinstance(stored, dict):
            for key, value in stored.items():
                try:
                    self._overrides[str(key)] = _clamp(float(value), MIN_SIZE, MAX_SIZE)
                except (TypeError, ValueError):
                    continue
