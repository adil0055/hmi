#!/usr/bin/env python3
"""Drive the simulator headlessly and check the cluster's inputs behave.

No display needed::

    python3 tools/smoke_test.py

Exits non-zero on the first failed expectation.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402

from backend import Simulator, VehicleState  # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


def spin(app: QCoreApplication, seconds: float) -> None:
    """Run the event loop for `seconds`, letting the simulator tick."""
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    while loop.isRunning() or True:
        loop.exec()
        return


def main() -> int:
    app = QCoreApplication(sys.argv[:1])
    v = VehicleState()
    sim = Simulator(v)
    sim.start()

    print("power-up state (matches the reference screenshot)")
    check("ignition on, engine off", v.ignition == 2 and not v.engineRunning)
    check("parked", v.gearMode == "P")
    check("range shows 550 km", round(v.rangeKm) == 550, f"{v.rangeKm}")
    check("odometer 25 km", round(v.odometer) == 25, f"{v.odometer}")
    check("no low-fuel lamp", not v.lowFuel, f"fuel={v.fuelLevel:.2f}")
    check("trip average unavailable", v.avgConsumption == 0)

    print("\nshift interlock")
    v.setGear("D")
    check("cannot leave P with engine off", v.gearMode == "P")

    print("\nstarting and pulling away")
    v.startStopEngine()
    check("engine running", v.engineRunning)
    spin(app, 0.6)
    check("idling", 500 < v.rpm < 1600, f"{v.rpm:.0f} rpm")

    v.brake = 1.0
    v.setGear("D")
    check("shifts to D with brake applied", v.gearMode == "D")
    v.brake = 0.0
    v.throttle = 0.8
    spin(app, 12.0)

    check("accelerating", v.speed > 25, f"{v.speed:.1f} km/h")
    check("gearbox upshifted", v.gearNumber >= 2, f"gear {v.gearNumber}")
    check("engine below redline", v.rpm < 6800, f"{v.rpm:.0f} rpm")
    check("trip timer running", v.tripSeconds > 0, f"{v.tripSeconds} s")
    check("burning fuel", v.tripFuelUsed > 0, f"{v.tripFuelUsed:.3f} L")
    check("coolant warming", v.coolantTemp > 20, f"{v.coolantTemp:.1f} °C")
    check("instant economy shown", v.instantConsumption > 0, f"{v.instantConsumption:.1f} km/L")
    check("range recomputed from fuel", v.rangeKm != 550, f"{v.rangeKm} km")

    print("\nbraking to a stop")
    v.throttle = 0.0
    v.brake = 1.0
    spin(app, 8.0)
    check("stopped", v.speed < 1.0, f"{v.speed:.1f} km/h")
    check("engine still idling", v.rpm > 400, f"{v.rpm:.0f} rpm")
    # The trip meter reads to 0.1 km, so it only leaves 0.0 once ~50 m are done.
    check("trip distance accumulating", v.tripDistance > 0, f"{v.tripDistance} km")
    check("average economy computed", v.avgConsumption > 0, f"{v.avgConsumption} km/L")

    print("\ntrip reset")
    v.resetTrip()
    check("trip cleared", v.tripDistance == 0 and v.tripSeconds == 0)
    check("odometer preserved", v.odometer > 25, f"{v.odometer} km")

    print("\nwarnings")
    v.fuelLevel = 0.05
    check("low-fuel lamp lights", v.lowFuel)
    v.coolantTemp = 125
    check("overheat lamp lights", v.engineTempWarn)
    v.doorFR = True
    check("door-ajar derived", v.doorAjar)
    v.doorFR = False
    check("door-ajar clears", not v.doorAjar)

    print("\nout of fuel")
    v.fuelLevel = 0.0
    v.throttle = 0.5
    v.brake = 0.0
    spin(app, 1.0)
    check("engine cuts out", not v.engineRunning)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
