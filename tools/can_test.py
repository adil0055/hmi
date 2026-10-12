#!/usr/bin/env python3
"""Check the cluster as an ECU: the matrix, E2E, power, lamps, failsafes, trip.

No display and no CAN hardware: python-can's in-process ``virtual`` bus is
the wire, the panel's rest-bus sends on it and the cluster ECU listens::

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


def until(condition, timeout: float = 6.0) -> float | None:
    """Seconds until ``condition()`` held, or None."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if condition():
            return time.monotonic() - start
        spin(0.02)
    return None


def main() -> int:
    try:
        import can
        import cantools
    except ImportError as exc:
        print(f"skipped: {exc} (pip install -r requirements.txt)")
        return 0
    from backend.e2e import Protection, crc8_sae_j1850
    from backend.ecu import DEFAULT_DBC, REQUESTS, ClusterEcu
    from backend.restbus import RestBus, vehicle_signals
    from backend.vehicle import _SPEC

    app = QCoreApplication(sys.argv[:1])  # noqa: F841 -- the event loop needs it
    db = cantools.database.load_file(str(DEFAULT_DBC))

    print("the matrix")
    sent = {s.name for m in db.messages if "IPC" not in m.senders for s in m.signals
            if not s.name.endswith(("_CRC", "_Counter"))}
    car = VehicleState()
    produced = set(vehicle_signals(car))
    check("the vehicle sends every signal the cluster receives", sent == produced,
          f"missing {sorted(sent - produced)}, extra {sorted(produced - sent)}")
    check("every message has a cycle time", all(m.cycle_time for m in db.messages))
    protected = [m.name for m in db.messages if Protection(m).active]
    check("safety messages are E2E protected",
          {"ESC_01", "ECM_01", "TCU_01", "SRS_01", "EPS_01", "BCM_01", "IPC_01"} <= set(protected),
          ", ".join(protected))
    check("CRC-8 SAE J1850 check value", crc8_sae_j1850(b"123456789") == 0x4B)
    check("every telltale request is wired", {s for s in REQUESTS} <= sent)
    props = {name for name, _, _ in _SPEC}
    check("the display model has the ECU's state",
          {"power", "flashing", "speedValid", "canMode"} <= props)

    print("on the bus")
    channel = f"can-test-{time.monotonic_ns()}"
    sim = Simulator(car)
    car.simulationMode = "manual"
    sim.start()
    cluster = VehicleState()
    rest = RestBus(car, can.Bus(interface="virtual", channel=channel))
    ecu = ClusterEcu(cluster, can.Bus(interface="virtual", channel=channel))
    tester = can.Bus(interface="virtual", channel=channel)
    ecu.start()
    check("dark before anything is on the bus", cluster.power == "off")
    rest.start()
    t_check = until(lambda: cluster.power == "check")
    t_run = until(lambda: cluster.power == "run")
    check("KL15 on: boot, then the bulb check", t_check is not None and t_check > 0.8,
          f"bulb check after {t_check}s")
    check("then running, the bulb check about 3 s", t_run is not None and 2.5 < t_run < 4.0,
          f"{t_run}s")

    car.absFault = True
    car.escActive = True
    car.turnLeft = True
    ok = until(lambda: cluster.absFault and ",esc," in cluster.flashing
               and ",turn_left," in cluster.flashing)
    check("lamp requests reach the display; ESC and the indicator flash", ok is not None,
          cluster.flashing)
    check("a steady request does not flash", ",abs," not in cluster.flashing)
    car.absFault = car.escActive = car.turnLeft = False
    until(lambda: not cluster.absFault and cluster.flashing == "")

    car.beltDriver = False
    until(lambda: not cluster.beltDriver)
    spin(0.2)
    check("seat belt unbuckled at rest: lit, steady",
          not cluster.beltDriver and ",seatbelt," not in cluster.flashing)
    car.speed = 40.0
    ok = until(lambda: ",seatbelt," in cluster.flashing)
    check("and flashing above 25 km/h", ok is not None)
    car.beltDriver = True
    car.speed = 0.0

    for level, want in ((0.10, True), (0.13, True), (0.16, False)):
        car.fuelLevel = level
        until(lambda: abs(cluster.fuelLevel - level) < 0.006)
        spin(0.1)
        check(f"low fuel at {level:.0%}: {'on' if want else 'off'} (hysteresis)",
              cluster.lowFuel is want)
    car.fuelLevel = 0.5

    car.gearMode, car.gearNumber = "D", 3
    ok = until(lambda: cluster.gearMode == "D" and cluster.gearNumber == 3)
    check("gear and the gear engaged", ok is not None)
    car.message = "Press brake pedal to shift"
    ok = until(lambda: cluster.message == "Press brake pedal to shift")
    check("a driver message by its request ID", ok is not None)
    car.message = ""

    odo = ecu._odo_m
    car.speed = 120.0
    spin(1.0)
    car.speed = 0.0
    travelled = ecu._odo_m - odo
    check("the cluster's own odometer counts from the speed",
          28.0 < travelled < 40.0, f"{travelled:.1f} m in 1 s at 120 km/h")
    ecu._trip_m = 1234.0
    car.resetTrip()
    ok = until(lambda: ecu._trip_m < 100.0, timeout=2.0)
    check("trip reset from the steering-wheel button, over the bus", ok is not None)

    print("the cluster's own message")
    got = []
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and not got:
        spin(0.05)
        msg = tester.recv(timeout=0.0)
        while msg is not None:
            if msg.arbitration_id == 0x5C0:
                got.append(msg)
            msg = tester.recv(timeout=0.0)
    ipc = db.get_message_by_name("IPC_01")
    if got:
        ok_crc, _ = Protection(ipc).check(bytes(got[-1].data))
        sts = str(ipc.decode(bytes(got[-1].data))["IPC_DisplaySts"])
    else:
        ok_crc, sts = False, None
    check("IPC_01 sent, protected, display Run", bool(got) and ok_crc and sts == "Run",
          f"{len(got)} frames, CRC {'ok' if ok_crc else 'bad'}, {sts}")

    print("failsafes")
    # A tester sending ESC_01 with a broken CRC: the frame is not used.
    rest.messages = [m for m in rest.messages if m.name != "ESC_01"]
    esc = db.get_message_by_name("ESC_01")
    p = Protection(esc)
    raw = {s.name: 0 for s in esc.signals}
    t_bad = time.monotonic()
    lit = None
    for k in range(60):
        data = bytearray(p.protect(raw, k))
        data[0] ^= 0x5A
        tester.send(can.Message(arbitration_id=esc.frame_id, data=bytes(data), is_extended_id=False))
        spin(0.02)
        if cluster.absFault and lit is None:
            lit = time.monotonic() - t_bad
    check("ESC_01 with a wrong CRC is lost: ABS, ESC and brake lamps on",
          cluster.absFault and cluster.escActive and cluster.brakeSystem, f"after {lit}s")
    check("and the speed is not available", cluster.speedValid is False)
    rest.messages = [m for m in rest.messages] + [esc]
    until(lambda: not cluster.absFault and cluster.speedValid)
    check("good frames again: back to normal", not cluster.absFault and cluster.speedValid)

    rest.messages = [m for m in rest.messages if m.name not in ("SRS_01", "EPS_01", "TCU_01")]
    ok = until(lambda: cluster.airbagFault and cluster.epsFault and cluster.gearMode == "-",
               timeout=2.0)
    check("SRS, EPS and TCU lost: airbag and steering lamps on, gear -", ok is not None)
    rest.stop()
    ok = until(lambda: cluster.power == "off", timeout=4.0)
    check("the bus goes quiet: the display goes dark", ok is not None, f"after {ok}s")

    rest.messages = [m for m in rest.db.messages if "IPC" not in m.senders]
    rest.start()
    until(lambda: cluster.power == "run", timeout=6.0)
    car.ignition = 0
    ok = until(lambda: cluster.power == "off", timeout=2.0)
    check("KL15 off: dark", ok is not None)

    rest.stop(close=True)
    ecu.stop()
    tester.shutdown()

    print("driven directly, without CAN")
    direct = VehicleState()
    dsim = Simulator(direct)
    direct.simulationMode = "manual"
    dsim.start()
    direct.beltDriver = False
    ok = until(lambda: ",seatbelt," in direct.flashing, timeout=2.0)
    check("the panel's own flashing set, as before", ok is not None)

    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
