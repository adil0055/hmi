"""Deliberate layout faults, for testing whatever is watching the cluster.

The companion to :mod:`backend.sizes`, and the same shape: this object owns the
state and the QSettings write, Main.qml pushes it into the ``LayoutRoles``
singleton, and the *catalogue* of elements lives beside the artwork in
qml/Hmi/LayoutRoles.qml rather than here.  This class never needs to know what
an id means, only what has been asked of it.

What it is for: a camera-based layout check can only be trusted once it has
been shown to report a displacement that was actually applied.  Teaching it on
a cluster that is already correct proves nothing — every element is where the
reference says, so a validator that always returned PASS would score full
marks.  So the cluster has to be able to render itself *wrong*, on purpose, by
a known amount:

* ``dx``/``dy`` -- move an element, in design-canvas pixels;
* ``scale``    -- draw it too large or too small about its own centre;
* ``rot``      -- rotate it;
* ``hidden``   -- do not draw it at all.

Those four cover the defect classes a layout check reports: wrong position,
wrong size, wrong orientation, missing.  The commanded values are exact and
can be exported (:meth:`exportJson`), which makes them ground truth to measure
a validator's answers against rather than another opinion about them.

Offsets are in *design* pixels, on the canvas the skin is authored at — the
same units as the coordinates in Theme.qml — so a commanded 3 px is 3 px of the
framebuffer regardless of what the window has been scaled to.

They survive a restart, like the typeface and the text sizes.  That is
convenient and it is a trap, so it is a loud one: :meth:`summary` gives the
line main.py prints to stderr on every start where anything is displaced, and
the panel says so across its header.  A cluster quietly running three pixels
out because somebody left it that way last week is exactly the sort of thing
that later gets diagnosed as a camera fault.
"""

from __future__ import annotations

import json

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

#: How far an element may be pushed, in design pixels.  Wide enough for a gross
#: fault, bounded so a fat-fingered entry cannot park an element off-canvas
#: where it looks like it was never drawn.
MAX_SHIFT = 400.0

#: Scale range.  Below and above this an element stops being recognisable as
#: itself, and the fault under test becomes "wrong content" rather than
#: "wrong size", which is a different check.
MIN_SCALE = 0.25
MAX_SCALE = 4.0

#: Rotation range, degrees.
MAX_ROT = 180.0

#: What an untouched element looks like.  Anything equal to this is not stored.
NEUTRAL = {"dx": 0.0, "dy": 0.0, "scale": 1.0, "rot": 0.0, "hidden": False}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clean(entry: dict) -> dict:
    """Coerce one entry to the neutral shape, clamped."""
    out = dict(NEUTRAL)
    for key, low, high in (
        ("dx", -MAX_SHIFT, MAX_SHIFT),
        ("dy", -MAX_SHIFT, MAX_SHIFT),
        ("scale", MIN_SCALE, MAX_SCALE),
        ("rot", -MAX_ROT, MAX_ROT),
    ):
        if key in entry:
            try:
                out[key] = round(_clamp(float(entry[key]), low, high), 3)
            except (TypeError, ValueError):
                pass
    if "hidden" in entry:
        out["hidden"] = bool(entry["hidden"])
    return out


def _is_neutral(entry: dict) -> bool:
    return all(entry.get(k) == v for k, v in NEUTRAL.items())


class LayoutManager(QObject):
    """Per-element layout faults, persisted, with the commanded values exact."""

    layoutChanged = Signal()

    def __init__(self, persist: bool = True, parent: QObject | None = None) -> None:
        """`persist` off keeps a run from touching the saved layout, which is
        what one-shot tools such as tools/shoot.py want."""
        super().__init__(parent)
        self._persist = persist
        self._enabled = True
        self._faults: dict[str, dict] = {}
        if persist:
            self._restore()

    # ------------------------------------------------------------- properties
    def _get_enabled(self) -> bool:
        return self._enabled

    def _set_enabled(self, value: bool) -> None:
        value = bool(value)
        if value != self._enabled:
            self._enabled = value
            self._save()
            self.layoutChanged.emit()

    def _get_faults(self) -> dict:
        return {key: dict(value) for key, value in self._faults.items()}

    def _get_count(self) -> int:
        return len(self._faults)

    def _get_modified(self) -> bool:
        return bool(self._faults)

    #: Master switch.  Lets a displaced set be taken out and put back without
    #: losing it, which is what an A/B against the same reference needs.
    enabled = Property(bool, _get_enabled, _set_enabled, notify=layoutChanged)
    #: Per-id {dx, dy, scale, rot, hidden}; absent means the element is correct.
    faults = Property("QVariantMap", _get_faults, notify=layoutChanged)
    #: How many elements are displaced, for the panel's header.
    faultCount = Property(int, _get_count, notify=layoutChanged)
    #: Whether anything at all differs from the artwork.
    modified = Property(bool, _get_modified, notify=layoutChanged)

    # ---------------------------------------------------------------- editing
    def _apply(self, role_id: str, entry: dict) -> None:
        cleaned = _clean(entry)
        if _is_neutral(cleaned):
            if self._faults.pop(role_id, None) is None:
                return
        elif self._faults.get(role_id) == cleaned:
            return
        else:
            self._faults[role_id] = cleaned
        self._save()
        self.layoutChanged.emit()

    @Slot(str, float, float)
    def setShift(self, role_id: str, dx: float, dy: float) -> None:
        """Move `role_id` by (`dx`, `dy`) design pixels, leaving the rest."""
        if not role_id:
            return
        entry = dict(self._faults.get(role_id, NEUTRAL))
        entry["dx"], entry["dy"] = dx, dy
        self._apply(role_id, entry)

    @Slot(str, float)
    def setScale(self, role_id: str, value: float) -> None:
        if not role_id:
            return
        entry = dict(self._faults.get(role_id, NEUTRAL))
        entry["scale"] = value
        self._apply(role_id, entry)

    @Slot(str, float)
    def setRotation(self, role_id: str, value: float) -> None:
        if not role_id:
            return
        entry = dict(self._faults.get(role_id, NEUTRAL))
        entry["rot"] = value
        self._apply(role_id, entry)

    @Slot(str, bool)
    def setHidden(self, role_id: str, value: bool) -> None:
        if not role_id:
            return
        entry = dict(self._faults.get(role_id, NEUTRAL))
        entry["hidden"] = value
        self._apply(role_id, entry)

    @Slot(str, "QVariantMap")
    def setFault(self, role_id: str, entry) -> None:
        """Replace everything about `role_id` at once."""
        if role_id:
            self._apply(role_id, dict(entry or {}))

    @Slot(str, float, float)
    def nudge(self, role_id: str, ddx: float, ddy: float) -> None:
        """Add to the current shift, for the panel's arrow buttons."""
        if not role_id:
            return
        entry = dict(self._faults.get(role_id, NEUTRAL))
        entry["dx"] = float(entry["dx"]) + float(ddx)
        entry["dy"] = float(entry["dy"]) + float(ddy)
        self._apply(role_id, entry)

    @Slot(str)
    def resetRole(self, role_id: str) -> None:
        """Put `role_id` back where the artwork draws it."""
        if self._faults.pop(role_id, None) is None:
            return
        self._save()
        self.layoutChanged.emit()

    @Slot()
    def resetAll(self) -> None:
        """Put every element back.  The button to reach for before a real run."""
        if not self._faults and self._enabled:
            return
        self._faults.clear()
        self._enabled = True
        self._save()
        self.layoutChanged.emit()

    @Slot("QVariantMap")
    def setFaults(self, values) -> None:
        """Replace the whole set, for --layout-shift and for tests."""
        cleaned: dict[str, dict] = {}
        for key, entry in dict(values or {}).items():
            if not isinstance(entry, dict):
                continue
            item = _clean(entry)
            if not _is_neutral(item):
                cleaned[str(key)] = item
        if cleaned == self._faults:
            return
        self._faults = cleaned
        self._save()
        self.layoutChanged.emit()

    # ---------------------------------------------------------------- reading
    @Slot(str, result="QVariantMap")
    def faultOf(self, role_id: str) -> dict:
        """What has been done to `role_id`; the neutral entry if nothing."""
        return dict(self._faults.get(role_id, NEUTRAL))

    @Slot(str, result=bool)
    def isFaulted(self, role_id: str) -> bool:
        return role_id in self._faults

    @Slot(result=str)
    def exportJson(self) -> str:
        """The commanded faults, as JSON.

        This is the ground truth a validator's answers are scored against, so
        it is the commanded value and not a measurement: exact, in design
        pixels, and written by the thing that applied it.
        """
        return json.dumps(
            {
                "units": "design_px",
                "enabled": self._enabled,
                "faults": self._get_faults(),
            },
            indent=2,
            sort_keys=True,
        )

    def summary(self) -> str:
        """One line for stderr when a run starts on a displaced cluster.

        Empty when nothing is displaced, so the caller can print it or not.
        """
        if not self._faults:
            return ""
        if not self._enabled:
            return (
                f"note: {len(self._faults)} layout fault(s) are stored but switched "
                "off; the cluster is drawing correctly"
            )
        names = ", ".join(sorted(self._faults)[:4])
        more = "" if len(self._faults) <= 4 else f", +{len(self._faults) - 4} more"
        return (
            f"WARNING: the cluster is deliberately drawing {len(self._faults)} "
            f"element(s) out of place ({names}{more}). "
            "Run with --layout-reset, or press Reset all in the layout panel, "
            "before trusting anything measured off this screen."
        )

    # ------------------------------------------------------------ persistence
    def _save(self) -> None:
        if not self._persist:
            return
        settings = QSettings("hmi", "cluster")
        settings.setValue("layoutEnabled", self._enabled)
        # JSON rather than a nested map, for the reason backend/sizes.py gives:
        # QSettings round-trips nested values differently per backend, and a
        # dx read back as the string "3" is a silent no-op.
        if self._faults:
            settings.setValue("layoutFaults", json.dumps(self._faults))
        else:
            settings.remove("layoutFaults")

    def _restore(self) -> None:
        settings = QSettings("hmi", "cluster")
        stored_enabled = settings.value("layoutEnabled", True)
        if isinstance(stored_enabled, str):
            self._enabled = stored_enabled.lower() not in ("false", "0", "")
        else:
            self._enabled = bool(stored_enabled)
        raw = settings.value("layoutFaults", "")
        if not raw:
            return
        try:
            stored = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(stored, dict):
            return
        for key, entry in stored.items():
            if not isinstance(entry, dict):
                continue
            item = _clean(entry)
            if not _is_neutral(item):
                self._faults[str(key)] = item


def parse_shift(text: str) -> tuple[str, dict]:
    """Parse one ``ID=dx,dy[,scale[,rot]]`` or ``ID=hidden`` command line term.

    Raises :class:`ValueError` with a usable message, because these are typed by
    hand into a shell and a silent misparse would displace nothing and look
    like the feature is broken.
    """
    role_id, sep, raw = text.partition("=")
    role_id = role_id.strip()
    if not sep or not role_id:
        raise ValueError(f"expected ID=dx,dy (or ID=hidden), got {text!r}")
    raw = raw.strip()
    if raw.lower() in ("hidden", "hide", "off"):
        return role_id, {"hidden": True}
    parts = [p.strip() for p in raw.split(",") if p.strip() != ""]
    if not 1 <= len(parts) <= 4:
        raise ValueError(f"expected ID=dx,dy[,scale[,rot]], got {text!r}")
    try:
        values = [float(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"non-numeric offset in {text!r}") from exc
    entry: dict = {"dx": values[0], "dy": values[1] if len(values) > 1 else 0.0}
    if len(values) > 2:
        entry["scale"] = values[2]
    if len(values) > 3:
        entry["rot"] = values[3]
    return role_id, entry
