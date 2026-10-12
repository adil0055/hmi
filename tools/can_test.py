#!/usr/bin/env python3
"""Check the CAN input: the DBC, decoding, and what reaches the cluster.

No display and no CAN hardware needed: python-can's in-process ``virtual``
bus stands in for the wire::

    python3 tools/can_test.py

Exits non-zero on the first failed expectation.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402

from backend import Simulator, VehicleState  # noqa: E402
from backend.vehicle import _SPEC  # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


def spin(seconds: float) -> None:
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def main() -> int:
    try:
        import can
        import cantools
    except ImportError as exc:
        print(f"skipped: {exc} (pip install -r requirements.txt)")
        return 0
    from backend.canbus import DEFAULT_DBC, CanInput, coerce, parse_bus

    app = QCoreApplication(sys.argv[:1])  # noqa: F841 -- the event loop needs it

    print("the DBC")
    db = cantools.database.load_file(str(DEFAULT_DBC))
    names = {s.name for m in db.messages for s in m.signals}
    props = {name for name, _, _ in _SPEC}
    check("every signal is a cluster property", names <= props,
          ", ".join(sorted(names - props)))
    v = VehicleState()
    differs = []
    for m in db.messages:
        decoded = m.decode(m.encode({s.name: s.raw_initial or 0 for s in m.signals},
                                    scaling=False))
        for name, value in decoded.items():
            mine, theirs = coerce(name, value), getattr(v, name)
            if isinstance(theirs, float) and abs(mine - theirs) > 0.006:
                differs.append(f"{name} {mine} != {theirs}")
            elif not isinstance(theirs, float) and mine != theirs:
                differs.append(f"{name} {mine!r} != {theirs!r}")
    check("start values are the cluster's power-up state", not differs, "; ".join(differs))

    print("bus specs")
    check("udp_multicast alone is the IPv4 group",
          parse_bus("udp_multicast") == {"interface": "udp_multicast", "channel": "239.74.163.2"})
    check("an adapter with a bitrate",
          parse_bus("pcan:PCAN_USBBUS1@500000")
          == {"interface": "pcan", "channel": "PCAN_USBBUS1", "bitrate": 500000})

    print("frames reach the cluster")
    sim = Simulator(v)
    sim.external = True
    sim.start()
    inp = CanInput(v, "virtual:hmi-test")
    inp.start()
    tester = can.Bus(interface="virtual", channel="hmi-test")
    state = {m.name: {s.name: s.raw_initial or 0 for s in m.signals} for m in db.messages}

    def send(**signals) -> None:
        for name, value in signals.items():
            m = next(m for m in db.messages if any(s.name == name for s in m.signals))
            sig = m.get_signal_by_name(name)
            state[m.name][name] = (sig.choice_to_number(value) if isinstance(value, str)
                                   else sig.scaled_to_raw(value))
            tester.send(can.Message(arbitration_id=m.frame_id, is_extended_id=False,
                                    data=m.encode(state[m.name], scaling=False)))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            spin(0.05)
            if all(_matches(getattr(v, k), val) for k, val in signals.items()):
                return

    send(absFault=1, speed=118.4, gearMode="D", headlightMode=2, laneDeparture="left")
    check("a lamp bit", v.absFault is True)
    check("a scaled value", abs(v.speed - 118.4) < 0.06, f"{v.speed}")
    check("a gear letter from the value table", v.gearMode == "D", v.gearMode)
    check("an integer mode", v.headlightMode == 2)
    check("a string enumeration", v.laneDeparture == "left")
    send(beltDriver=0)
    check("belt unfastened", v.beltDriver is False)

    print("the model stands still while the bus drives")
    odo = v.odometer
    spin(0.6)
    check("no kilometres counted at 118 km/h", v.odometer == odo, f"{odo} -> {v.odometer}")

    print("lamps that flash have a phase to flash on")
    send(laneDeparture="none", absFault=0)
    phases = set()
    for _ in range(12):
        spin(0.1)
        phases.add(v.blinkOn)
    check("the seat-belt lamp's phase runs with no indicator on", phases == {True, False},
          str(phases))
    send(beltDriver=1)
    spin(0.5)
    check("and stops when nothing flashes", v.blinkOn is False)

    print("the panel still moves what the bus leaves alone")
    send(coolantTemp=20)          # FLUIDS once, as a tester sending cyclically has
    spin(0.3)
    v.fuelLevel = 0.5
    send(coolantTemp=20)          # the same frame again, fuel still 0.14 in it
    spin(0.3)
    check("a repeated frame does not undo it", abs(v.fuelLevel - 0.5) < 1e-9, f"{v.fuelLevel}")
    send(fuelLevel=0.3)
    check("a changed one does", abs(v.fuelLevel - 0.3) < 0.006, f"{v.fuelLevel}")

    tester.shutdown()
    inp.stop()

    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


def _matches(have, want) -> bool:
    if isinstance(want, str):
        return have == want
    if isinstance(have, bool):
        return have is bool(want)
    return abs(float(have) - float(want)) < 0.06


if __name__ == "__main__":
    raise SystemExit(main())
