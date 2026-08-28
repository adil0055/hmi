"""Typeface loading, cataloguing and metrics for the cluster.

Three jobs:

* register the typefaces shipped in ``assets/fonts`` (see ``catalog.json``) so
  the control panel can offer them in a dropdown;
* let the user load a face of their own from disk, as before;
* measure whichever face is active and publish the numbers the QML layout
  needs to *re-align itself* around it.

That last part is the interesting one.  The cluster is drawn on a fixed design
canvas with hard-coded coordinates, which only works while every glyph keeps
the proportions of the face the artwork was drawn against.  Across the
catalogue those proportions vary a lot — cap height spans 0.63..0.73 em,
ascent 0.79..1.14 em, and the advance of a digit 0.39..0.83 em, so Orbitron's
figures are more than twice the width of Teko's at the same nominal size.

Left alone that would make a swap look broken: text set to the same pixel size
would change apparent size, text centred on its bounding box would sit at a
different height, and long readouts would overrun their slot.  So we publish

    capScale     multiply a pixel size by this and every face draws capitals
                 at the same height as the reference face
    capCentre    where the cap-height band sits inside the line box, as a
                 fraction of that box, so callers can centre on the glyphs
                 rather than on the ascent/descent
    digitRatio   advance width of a figure, for predicting how wide a readout
                 will get before it is laid out

and Theme.qml turns them into sizes and offsets.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, QSettings, QUrl, Signal, Slot
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF

#: Extensions QFontDatabase can register.
FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc", ".pfb", ".woff", ".woff2"}

#: Used when neither a catalogue face nor a custom one is available.
SYSTEM_FALLBACKS = ("Titillium Web", "Roboto", "Open Sans", "Noto Sans", "DejaVu Sans")

#: Size the metrics are probed at.  High enough that rounding in the rasteriser
#: does not show up in the ratios, and it divides out again immediately.
_PROBE_PX = 200.0


def _measure(family: str) -> dict:
    """Proportions of `family`, all as fractions of the em."""
    font = QFont(family)
    font.setPixelSize(int(_PROBE_PX))
    fm = QFontMetricsF(font)
    ascent = fm.ascent() / _PROBE_PX
    descent = fm.descent() / _PROBE_PX
    cap = fm.capHeight() / _PROBE_PX
    line = ascent + descent
    # Where the middle of the capital band falls inside the line box, 0 at the
    # top and 1 at the bottom.  Centring on this instead of on the box keeps a
    # row of figures optically still when the face changes.
    cap_centre = (ascent - cap / 2.0) / line if line > 0 else 0.5
    return {
        "family": family,
        "capRatio": cap,
        "xRatio": fm.xHeight() / _PROBE_PX,
        "ascentRatio": ascent,
        "descentRatio": descent,
        "lineRatio": line,
        "capCentre": cap_centre,
        "digitRatio": fm.horizontalAdvance("0") / _PROBE_PX,
    }


class FontManager(QObject):
    """Registers font files and publishes the family the cluster should use."""

    familyChanged = Signal()
    uiFamilyChanged = Signal()
    sourceChanged = Signal()
    statusChanged = Signal()
    catalogChanged = Signal()

    def __init__(self, bundled_dir: Path, persist: bool = True,
                 parent: QObject | None = None) -> None:
        """`persist` off keeps a run from touching the saved preference, which
        is what one-shot tools such as tools/shoot.py want."""
        super().__init__(parent)
        self._persist = persist
        self._bundled_dir = Path(bundled_dir)
        self._catalog: list[dict] = []
        self._reference = "Titillium Web"
        self._selected = ""          # catalogue id, "" while a custom face is on
        self._bundled_family = ""
        self._custom_family = ""
        self._custom_ids: list[int] = []
        self._source = ""
        self._status = ""
        self._metrics_cache: dict[str, dict] = {}

        self._load_catalog()
        if persist:
            self._restore_saved()

    # ------------------------------------------------------------- properties
    def _get_family(self) -> str:
        """Family the cluster draws with."""
        return self._custom_family or self._selected_family() or self._first_system()

    def _get_ui_family(self) -> str:
        """Family the control panel draws with.

        Deliberately never the cluster's face: a symbol or display face would
        make the panel unreadable, and you would have no way to undo the change.
        """
        return self._bundled_family or self._first_system()

    def _selected_family(self) -> str:
        for entry in self._catalog:
            if entry["id"] == self._selected:
                return entry["family"]
        return self._bundled_family

    def _get_source(self) -> str:
        return self._source

    def _get_status(self) -> str:
        return self._status

    def _get_custom(self) -> bool:
        return bool(self._custom_family)

    def _get_catalog(self) -> list:
        return self._catalog

    def _get_selected(self) -> str:
        return self._selected

    def _get_index(self) -> int:
        # -1 while a font loaded from disk is in use: no catalogue row is the
        # active one, and a dropdown should show that rather than claim one is.
        if self._custom_family:
            return -1
        for i, entry in enumerate(self._catalog):
            if entry["id"] == self._selected:
                return i
        return -1

    def _get_metrics(self) -> dict:
        """Proportions of the active face, plus the scale that normalises it."""
        family = self._get_family()
        data = dict(self._metrics_for(family))
        reference = self._metrics_for(self._reference)
        cap = data.get("capRatio", 0)
        data["capScale"] = (reference["capRatio"] / cap) if cap > 0 else 1.0
        data["digitScale"] = (data["digitRatio"] / reference["digitRatio"]
                              if reference["digitRatio"] > 0 else 1.0)
        # The reference's own proportions travel with the payload: the QML has
        # to know where the artwork *was* aligned to work out how far to move.
        data["refCapCentre"] = reference["capCentre"]
        data["refLineRatio"] = reference["lineRatio"]
        return data

    family = Property(str, _get_family, notify=familyChanged)
    uiFamily = Property(str, _get_ui_family, notify=uiFamilyChanged)
    source = Property(str, _get_source, notify=sourceChanged)
    status = Property(str, _get_status, notify=statusChanged)
    isCustom = Property(bool, _get_custom, notify=familyChanged)
    catalog = Property("QVariantList", _get_catalog, notify=catalogChanged)
    selectedId = Property(str, _get_selected, notify=familyChanged)
    selectedIndex = Property(int, _get_index, notify=familyChanged)
    metrics = Property("QVariantMap", _get_metrics, notify=familyChanged)

    # ---------------------------------------------------------------- loading
    def _first_system(self) -> str:
        available = set(QFontDatabase.families())
        for name in SYSTEM_FALLBACKS:
            if name in available:
                return name
        return "sans-serif"

    def _metrics_for(self, family: str) -> dict:
        if family not in self._metrics_cache:
            self._metrics_cache[family] = _measure(family)
        return self._metrics_cache[family]

    @Slot(str, result="QVariantMap")
    def metricsFor(self, family: str) -> dict:
        """Proportions of any registered family, for previews."""
        return self._metrics_for(family or self._get_family())

    @staticmethod
    def _primary_family(names: list[str]) -> str:
        """Pick the real family name out of what a font file registers.

        A variable font reports one entry per named instance — 'Inter',
        'Inter Thin', 'Inter SemiBold' and so on — with the base name repeated
        for every instance Qt maps onto a standard weight.  The most frequent
        name is therefore the family; ties go to the shortest, which drops the
        style suffix.
        """
        if not names:
            return ""
        return min(set(names), key=lambda n: (-names.count(n), len(n)))

    def _register(self, paths: list[Path]) -> tuple[list[int], str]:
        """Register font files, returning their ids and the family they define."""
        ids: list[int] = []
        names: list[str] = []
        for path in paths:
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                continue
            ids.append(font_id)
            names += QFontDatabase.applicationFontFamilies(font_id)
        return ids, self._primary_family(names)

    def _load_catalog(self) -> None:
        """Register every face listed in catalog.json.

        All of them are loaded up front rather than on demand: it costs a few
        hundred milliseconds once, and in exchange switching face is instant
        and the dropdown can render each entry in its own typeface.
        """
        manifest = self._bundled_dir / "catalog.json"
        entries: list[dict] = []
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                entries = data.get("families", [])
                self._reference = data.get("reference", self._reference)
            except (OSError, ValueError) as exc:
                self._set_status(f"Could not read the font catalogue: {exc}")

        for entry in entries:
            directory = self._bundled_dir / entry.get("dir", entry["id"])
            paths = [directory / name for name in entry.get("files", [])]
            paths = [p for p in paths if p.is_file()]
            if not paths:
                continue
            _ids, family = self._register(paths)
            if not family:
                continue
            self._catalog.append({
                "id": entry["id"],
                "name": entry.get("name", family),
                "family": family,
                "style": entry.get("style", ""),
                "note": entry.get("note", ""),
                "licence": entry.get("licence", ""),
                "files": len(paths),
            })

        if not self._catalog:
            # Nobody has run tools/fetch_fonts.py; fall back to loose files.
            _ids, family = self._register(sorted(self._bundled_dir.glob("*.ttf")))
            self._bundled_family = family
            self._set_status("No font catalogue — run tools/fetch_fonts.py")
            return

        for entry in self._catalog:
            if entry["family"] == self._reference:
                self._bundled_family = entry["family"]
                self._selected = entry["id"]
                break
        else:
            self._bundled_family = self._catalog[0]["family"]
            self._selected = self._catalog[0]["id"]
        self.catalogChanged.emit()

    def _set_status(self, text: str) -> None:
        if self._status != text:
            self._status = text
            self.statusChanged.emit()

    def _clear_custom(self) -> None:
        for font_id in self._custom_ids:
            QFontDatabase.removeApplicationFont(font_id)
        self._custom_ids.clear()
        self._custom_family = ""

    # -------------------------------------------------------------- selecting
    @Slot(str, result=bool)
    def selectFamily(self, family_id: str) -> bool:
        """Switch the cluster to a catalogue face."""
        for entry in self._catalog:
            if entry["id"] != family_id:
                continue
            self._clear_custom()
            self._selected = family_id
            self._source = ""
            self._set_status(f"{entry['name']} — {entry['style'].lower()}, {entry['licence']}")
            if self._persist:
                settings = QSettings("hmi", "cluster")
                settings.setValue("fontFamilyId", family_id)
                settings.remove("fontPaths")
            self.sourceChanged.emit()
            self.familyChanged.emit()
            return True
        self._set_status(f"No catalogue entry called {family_id!r}")
        return False

    @Slot(int, result=bool)
    def selectIndex(self, index: int) -> bool:
        """Switch by position, which is what a ComboBox hands back."""
        if 0 <= index < len(self._catalog):
            return self.selectFamily(self._catalog[index]["id"])
        return False

    @Slot("QVariantList", result=bool)
    def loadFiles(self, items) -> bool:
        """Register the given font files and switch the cluster to them.

        Accepts file URLs or plain paths.  Passing a family's several styles at
        once (regular, italic, bold) is worth doing: the cluster asks for italic
        numerals and a demi-bold range, and Qt otherwise has to synthesise them.
        """
        paths: list[Path] = []
        for item in items or []:
            text = item.toLocalFile() if isinstance(item, QUrl) else str(item)
            if text.startswith("file://"):
                text = QUrl(text).toLocalFile()
            text = text.strip()
            if text:
                paths.append(Path(text).expanduser())
        return self._apply(paths, remember=True)

    @Slot(str, result=bool)
    def loadPath(self, text: str) -> bool:
        """Convenience for a single typed-in path or a directory of fonts."""
        candidate = Path(text.strip()).expanduser() if text else None
        if candidate is None or not text.strip():
            self._set_status("Enter a path to a font file")
            return False
        if candidate.is_dir():
            found = sorted(p for p in candidate.iterdir() if p.suffix.lower() in FONT_SUFFIXES)
            if not found:
                self._set_status(f"No font files in {candidate}")
                return False
            return self._apply(found, remember=True)
        return self._apply([candidate], remember=True)

    def _apply(self, paths: list[Path], remember: bool) -> bool:
        if not paths:
            self._set_status("No font selected")
            return False

        missing = [p for p in paths if not p.is_file()]
        if missing:
            self._set_status(f"Not found: {missing[0].name}")
            return False

        loaded_ids, family = self._register(paths)
        rejected = len(paths) - len(loaded_ids)

        if not family:
            for font_id in loaded_ids:
                QFontDatabase.removeApplicationFont(font_id)
            self._set_status(f"Could not read {paths[0].name} — is it a TTF/OTF?")
            return False

        # Only drop the previous custom font once the new one is known good.
        self._clear_custom()
        self._custom_ids = loaded_ids
        self._custom_family = family
        self._source = ", ".join(p.name for p in paths)

        note = f"Using {family}"
        if rejected:
            note += f" — skipped {rejected} unreadable file(s)"
        self._set_status(note)

        if remember and self._persist:
            settings = QSettings("hmi", "cluster")
            settings.setValue("fontPaths", [str(p) for p in paths])
            settings.remove("fontFamilyId")

        self.sourceChanged.emit()
        self.familyChanged.emit()
        return True

    @Slot()
    def useBundled(self) -> None:
        """Go back to the typeface the cluster was drawn against."""
        self._clear_custom()
        self._source = ""
        for entry in self._catalog:
            if entry["family"] == self._reference:
                self._selected = entry["id"]
                break
        if self._persist:
            settings = QSettings("hmi", "cluster")
            settings.remove("fontPaths")
            settings.remove("fontFamilyId")
        self._set_status("Using the typeface the cluster was drawn against")
        self.sourceChanged.emit()
        self.familyChanged.emit()

    def _restore_saved(self) -> None:
        settings = QSettings("hmi", "cluster")
        family_id = settings.value("fontFamilyId")
        if family_id and any(e["id"] == family_id for e in self._catalog):
            self._selected = str(family_id)
            self.familyChanged.emit()
            return
        saved = settings.value("fontPaths")
        if not saved:
            return
        if isinstance(saved, str):
            saved = [saved]
        if not self._apply([Path(p) for p in saved], remember=False):
            # The file moved or was deleted since last run; carry on bundled.
            self._set_status("Saved font is no longer available — using the bundled one")
