"""Typeface loading for the cluster.

Holds the bundled font family and lets the control panel swap in one the user
supplies at runtime.  The choice is remembered between runs, so a cluster
retargeted to a brand typeface stays that way.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QSettings, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase

#: Extensions QFontDatabase can register.
FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc", ".pfb", ".woff", ".woff2"}

#: Used when neither a custom font nor the bundled files are available.
SYSTEM_FALLBACKS = ("Titillium Web", "Roboto", "Open Sans", "Noto Sans", "DejaVu Sans")


class FontManager(QObject):
    """Registers font files and publishes the family the cluster should use."""

    familyChanged = Signal()
    uiFamilyChanged = Signal()
    sourceChanged = Signal()
    statusChanged = Signal()

    def __init__(self, bundled_dir: Path, persist: bool = True,
                 parent: QObject | None = None) -> None:
        """`persist` off keeps a run from touching the saved preference, which
        is what one-shot tools such as tools/shoot.py want."""
        super().__init__(parent)
        self._persist = persist
        self._bundled_dir = Path(bundled_dir)
        self._bundled_family = ""
        self._custom_family = ""
        self._custom_ids: list[int] = []
        self._source = ""
        self._status = ""

        self._load_bundled()
        if persist:
            self._restore_saved()

    # ------------------------------------------------------------- properties
    def _get_family(self) -> str:
        """Family the cluster draws with."""
        return self._custom_family or self._bundled_family or self._first_system()

    def _get_ui_family(self) -> str:
        """Family the control panel draws with.

        Deliberately never the custom font: a symbol or display face would make
        the panel unreadable, and you would have no way to undo the change.
        """
        return self._bundled_family or self._first_system()

    def _get_source(self) -> str:
        return self._source

    def _get_status(self) -> str:
        return self._status

    def _get_custom(self) -> bool:
        return bool(self._custom_family)

    family = Property(str, _get_family, notify=familyChanged)
    uiFamily = Property(str, _get_ui_family, notify=uiFamilyChanged)
    source = Property(str, _get_source, notify=sourceChanged)
    status = Property(str, _get_status, notify=statusChanged)
    isCustom = Property(bool, _get_custom, notify=familyChanged)

    # ---------------------------------------------------------------- loading
    def _first_system(self) -> str:
        available = set(QFontDatabase.families())
        for name in SYSTEM_FALLBACKS:
            if name in available:
                return name
        return "sans-serif"

    def _load_bundled(self) -> None:
        for path in sorted(self._bundled_dir.glob("*.ttf")):
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families and not self._bundled_family:
                self._bundled_family = families[0]

    def _set_status(self, text: str) -> None:
        if self._status != text:
            self._status = text
            self.statusChanged.emit()

    def _clear_custom(self) -> None:
        for font_id in self._custom_ids:
            QFontDatabase.removeApplicationFont(font_id)
        self._custom_ids.clear()
        self._custom_family = ""

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

        loaded_ids: list[int] = []
        families: list[str] = []
        rejected: list[str] = []
        for path in paths:
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                rejected.append(path.name)
                continue
            loaded_ids.append(font_id)
            for name in QFontDatabase.applicationFontFamilies(font_id):
                if name not in families:
                    families.append(name)

        if not families:
            for font_id in loaded_ids:
                QFontDatabase.removeApplicationFont(font_id)
            name = rejected[0] if rejected else paths[0].name
            self._set_status(f"Could not read {name} — is it a TTF/OTF?")
            return False

        # Only drop the previous custom font once the new one is known good.
        self._clear_custom()
        self._custom_ids = loaded_ids
        self._custom_family = families[0]
        self._source = ", ".join(p.name for p in paths)

        note = f"Using {self._custom_family}"
        if len(families) > 1:
            note += f" (+{len(families) - 1} more famil{'y' if len(families) == 2 else 'ies'})"
        if rejected:
            note += f" — skipped {len(rejected)} unreadable file(s)"
        self._set_status(note)

        if remember and self._persist:
            QSettings("hmi", "cluster").setValue("fontPaths", [str(p) for p in paths])

        self.sourceChanged.emit()
        self.familyChanged.emit()
        return True

    @Slot()
    def useBundled(self) -> None:
        """Go back to the typeface shipped with the project."""
        self._clear_custom()
        self._source = ""
        if self._persist:
            QSettings("hmi", "cluster").remove("fontPaths")
        self._set_status("Using the bundled typeface")
        self.sourceChanged.emit()
        self.familyChanged.emit()

    def _restore_saved(self) -> None:
        saved = QSettings("hmi", "cluster").value("fontPaths")
        if not saved:
            return
        if isinstance(saved, str):
            saved = [saved]
        paths = [Path(p) for p in saved]
        if not self._apply(paths, remember=False):
            # The file moved or was deleted since last run; carry on bundled.
            self._set_status("Saved font is no longer available — using the bundled one")
