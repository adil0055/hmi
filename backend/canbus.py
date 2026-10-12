"""CAN input: the cluster driven over a CAN bus, as a real one is.

Frames are decoded with a DBC (``can/hmi.dbc``) whose signals are named after
the `VehicleState` properties they set, so a signal added to the DBC reaches
the cluster with no code change here. Enumerations (gear, drive mode, lane
departure, units) are value tables whose names are the strings the property
holds.

The bus is anything python-can opens: ``udp_multicast`` for a virtual bus
between programs, on one computer or across a network, with no hardware;
``socketcan`` on Linux (``vcan0`` virtual, ``can0`` real); ``pcan``,
``kvaser``, ``vector``, ``slcan`` adapters. See `parse_bus`.

Frames arrive on a reader thread and are applied on the Qt thread, so the
properties' change signals reach QML where they belong. Only a signal whose
value changed since its last frame is applied: a tester repeats every message
cyclically, and the control panel can still move what the tester leaves alone.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .vehicle import _SPEC, VehicleState

DEFAULT_DBC = Path(__file__).resolve().parent.parent / "can" / "hmi.dbc"

#: python-can's virtual bus over UDP multicast, and the group it uses for IPv4.
UDP_GROUP = "239.74.163.2"

_TYPES = {name: typ for name, typ, _ in _SPEC}


def parse_bus(spec: str) -> dict:
    """``INTERFACE[:CHANNEL][@BITRATE]`` as keyword arguments for ``can.Bus``.

    ``udp_multicast`` alone means the IPv4 group, which crosses an ordinary
    network where the IPv6 default may not.
    """
    spec = spec.strip()
    bitrate = None
    if "@" in spec:
        spec, rate = spec.rsplit("@", 1)
        bitrate = int(rate)
    interface, _, channel = spec.partition(":")
    interface = interface.strip() or "udp_multicast"
    if not channel and interface == "udp_multicast":
        channel = UDP_GROUP
    kwargs: dict = {"interface": interface}
    if channel:
        kwargs["channel"] = channel
    if bitrate:
        kwargs["bitrate"] = bitrate
    return kwargs


def coerce(name: str, value):
    """A decoded signal as the property's own type, or None if there is no such property."""
    typ = _TYPES.get(name)
    if typ is None:
        return None
    named = getattr(value, "name", None)          # a value-table entry
    if typ is str:
        return str(named if named is not None else value)
    raw = getattr(value, "value", value)
    if typ is bool:
        return bool(raw)
    if typ is int:
        return int(round(float(raw)))
    return float(raw)


class CanInput(QObject):
    """Listens on a CAN bus and sets `VehicleState` from what it decodes."""

    #: {property: value}, emitted from the reader thread, applied on the Qt thread.
    decoded = Signal(object)
    #: Counters for the panel or a log: frames applied, frames not in the DBC.
    statusChanged = Signal()

    def __init__(self, vehicle: VehicleState, bus_spec: str = "udp_multicast",
                 dbc: str | Path = DEFAULT_DBC, parent: QObject | None = None) -> None:
        super().__init__(parent)
        import can
        import cantools

        self.vehicle = vehicle
        self.db = cantools.database.load_file(str(dbc))
        unknown = sorted({s.name for m in self.db.messages for s in m.signals} - set(_TYPES))
        if unknown:
            print(f"CAN: signals with no cluster property, ignored: {', '.join(unknown)}")
        self.bus_kwargs = parse_bus(bus_spec)
        self.bus = can.Bus(**self.bus_kwargs)
        self.frames = 0
        self.foreign = 0
        self._last: dict[str, object] = {}
        self._stop = threading.Event()
        self.decoded.connect(self._apply)
        self._thread = threading.Thread(target=self._read, name="can-input", daemon=True)

    def start(self) -> None:
        self._thread.start()
        where = self.bus_kwargs.get("channel", "")
        print(f"CAN: listening on {self.bus_kwargs['interface']} {where}".rstrip())

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self.bus.shutdown()

    def _read(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self.bus.recv(timeout=0.2)
            except Exception as exc:                      # adapter unplugged, socket closed
                if not self._stop.is_set():
                    print(f"CAN: receive failed: {exc}")
                return
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            try:
                values = self.db.decode_message(msg.arbitration_id, msg.data)
            except (KeyError, ValueError):
                self.foreign += 1                         # not in the DBC, or too short
                continue
            changed = {}
            for name, value in values.items():
                prop = coerce(name, value)
                if prop is not None and self._last.get(name) != prop:
                    self._last[name] = prop
                    changed[name] = prop
            self.frames += 1
            if changed:
                self.decoded.emit(changed)

    @Slot(object)
    def _apply(self, changed: dict) -> None:
        for name, value in changed.items():
            setattr(self.vehicle, name, value)
        self.statusChanged.emit()
