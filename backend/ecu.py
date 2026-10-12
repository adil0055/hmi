"""The instrument cluster as an ECU: everything it shows comes off the CAN bus.

It behaves the way a production cluster does, so that whatever is built to
test this one works on a real one:

* **Power.** BCM_KL15 is the ignition. Off (or no frame at all), the display
  is dark. On, the cluster boots (black, then its welcome screen), shows the
  bulb check -- every lamp lit and the gauges swept, for 3 s -- and then runs.
* **Cyclic messages, monitored.** A message missing for 5 of its cycles (at
  least 200 ms) is lost, and the cluster shows the failsafe for it: ESC_01
  lost lights the ABS, ESC and brake lamps and the speed reads ---; SRS_01
  the airbag lamp; EPS_01 the steering lamp; ECM_01 the engine lamp; TPMS_01
  the tyre lamp; TCU_01 the gear reads -; BCM_01 is the ignition, so it going
  quiet switches the display off.
* **End-to-end protection.** A frame whose CRC is wrong, or whose alive
  counter did not move, is not used; three in a row and the message is lost.
* **Telltale requests** are Off, On, Flash or SNA; the cluster flashes a lamp
  itself, at 1.3 Hz. Values meaning "signal not available" are shown as such.
* **Its own logic**, as clusters have it: the low fuel lamp from the fuel
  level, the door lamp from the doors, the seat-belt reminder (steady, and
  flashing above 25 km/h), the coolant warning from the temperature, and the
  trip computer and odometer, integrated from the speed and the fuel rate.
* **It transmits** IPC_01: its display state and odometer, protected.

The display model it fills is a `VehicleState`; QML binds to that.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from .e2e import Protection
from .vehicle import VehicleState

DEFAULT_DBC = Path(__file__).resolve().parent.parent / "can" / "cluster.dbc"

TASK_MS = 20                 # the cluster's main task
BOOT_S = 1.2                 # dark, then the welcome screen
CHECK_S = 3.0                # the bulb check
FLASH_MS = 380               # a flashing lamp's on and off halves (1.3 Hz)
LOST_CYCLES = 5
LOST_MIN_S = 0.2
E2E_ERRORS_LOST = 3
SLEEP_S = 2.0                # no frame at all for this long: the display goes dark
TANK_L = 37.0
NOMINAL_KM_PER_L = 14.87
BELT_FLASH_KMH = 25.0

MESSAGES = {
    "None": "", "PressBrake": "Press brake pedal to shift",
    "VehicleMoving": "Vehicle moving", "SelectPN": "Select P or N to start",
    "OutOfFuel": "Out of fuel",
}

# Telltale requests: signal -> the lamp's icon, and the VehicleState flag it sets.
REQUESTS = {
    "ESC_ABS_TtReq": ("abs", "absFault"),
    "ESC_ESC_TtReq": ("esc", "escActive"),
    "ESC_ESCOff_TtReq": ("esc_off", "escOff"),
    "ESC_TCSOff_TtReq": ("traction_off", "tractionOff"),
    "ESC_BrakeWarn_TtReq": ("brake", "brakeSystem"),
    "ECM_MIL_TtReq": ("check_engine", "checkEngine"),
    "ECM_OilPress_TtReq": ("oil", "oilPressure"),
    "ECM_Charge_TtReq": ("battery", "batteryCharge"),
    "ECM_GlowPlug_TtReq": ("glow_plug", "glowPlug"),
    "SRS_Airbag_TtReq": ("airbag", "airbagFault"),
    "EPS_Warn_TtReq": ("eps", "epsFault"),
    "TPMS_Warn_TtReq": ("tpms", "tpms"),
    "BCM_Immo_TtReq": ("immobilizer", "immobilizer"),
    "BCM_WasherLow_TtReq": ("washer", "washerFluid"),
    "BCM_HighBeam_TtReq": ("high_beam", "highBeam"),
    "BCM_FrontFog_TtReq": ("fog_front", "frontFog"),
    "BCM_RearFog_TtReq": ("fog_rear", "rearFog"),
    "ADAS_FCW_TtReq": ("fca", "fcaWarn"),
}

# What a lost message lights.
FAILSAFE = {
    "ESC_01": ("ESC_ABS_TtReq", "ESC_ESC_TtReq", "ESC_BrakeWarn_TtReq"),
    "SRS_01": ("SRS_Airbag_TtReq",),
    "EPS_01": ("EPS_Warn_TtReq",),
    "ECM_01": ("ECM_MIL_TtReq",),
    "TPMS_01": ("TPMS_Warn_TtReq",),
}


class _Message:
    """What the cluster knows about one received message."""

    def __init__(self, message) -> None:
        self.message = message
        self.protection = Protection(message)
        self.timeout = max(LOST_CYCLES * (message.cycle_time or 100) / 1000.0, LOST_MIN_S)
        self.values: dict = {}
        self.last_ok = -1e9
        self.counter = None
        self.errors = 0

    def alive(self, now: float) -> bool:
        return now - self.last_ok <= self.timeout and self.errors < E2E_ERRORS_LOST


class ClusterEcu(QObject):
    """Receives the matrix on ``bus``, fills ``vehicle``, sends IPC_01."""

    _frame = Signal(int, bytes, float)

    def __init__(self, vehicle: VehicleState, bus, dbc: str | Path = DEFAULT_DBC,
                 node: str = "IPC", quick_boot: bool = False,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        import cantools

        self.v = vehicle
        self.bus = bus
        self.db = cantools.database.load_file(str(dbc))
        self.rx = {m.frame_id: _Message(m) for m in self.db.messages if node not in m.senders}
        self.by_name = {m.message.name: m for m in self.rx.values()}
        self.of_signal = {s.name: m for m in self.rx.values() for s in m.message.signals}
        self.tx = [m for m in self.db.messages if node in m.senders]
        self._tx_counter = 0
        self._tx_due = 0.0
        self.boot_s = 0.0 if quick_boot else BOOT_S
        self.check_s = 0.0 if quick_boot else CHECK_S
        self.state = "off"
        self._since = time.monotonic()
        self._last_frame = -1e9
        self._last_task = time.monotonic()
        self._flash_on = True
        self._flash_since = time.monotonic()
        self._fuel_low = False
        self._engine_has_run = False
        self._trip_m = 0.0
        self._odo_m = vehicle.odometer * 1000.0
        self._trip_fuel_l = 0.0
        self._trip_s = 0.0
        self._trip_reset_was = False
        self.frames = 0
        self.e2e_errors = 0
        self._stop = threading.Event()
        self._frame.connect(self._on_frame)
        self._reader = threading.Thread(target=self._read, name="cluster-rx", daemon=True)
        self._task = QTimer(self)
        self._task.setInterval(TASK_MS)
        self._task.timeout.connect(self._step)
        vehicle.canMode = True
        vehicle.power = "off"

    def start(self) -> None:
        self._reader.start()
        self._task.start()

    def stop(self) -> None:
        self._stop.set()
        self._task.stop()
        self._reader.join(timeout=1.0)
        try:
            self.bus.shutdown()
        except Exception:
            pass

    # -- receiving ---------------------------------------------------------------

    def _read(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self.bus.recv(timeout=0.1)
            except Exception:
                if self._stop.is_set():
                    return
                time.sleep(0.1)
                continue
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            self._frame.emit(msg.arbitration_id, bytes(msg.data), time.monotonic())

    @Slot(int, bytes, float)
    def _on_frame(self, frame_id: int, data: bytes, at: float) -> None:
        self._last_frame = at
        rx = self.rx.get(frame_id)
        if rx is None:
            return
        self.frames += 1
        if rx.protection.active:
            ok, counter = rx.protection.check(data)
            if not ok or counter == rx.counter:
                rx.errors += 1
                self.e2e_errors += 1
                return
            rx.counter = counter
        try:
            rx.values = rx.message.decode(data, decode_choices=True)
        except Exception:
            rx.errors += 1
            return
        rx.errors = 0
        rx.last_ok = at

    # -- the cluster's task --------------------------------------------------------

    def _get(self, signal: str, default=None, now: float | None = None):
        """A signal's value, or ``default`` while its message is lost or it reads SNA."""
        m = self.of_signal.get(signal)
        if m is None or signal not in m.values:
            return default
        if not m.alive(now if now is not None else time.monotonic()):
            return default
        value = m.values[signal]
        if hasattr(value, "name"):                       # a value-table entry
            return default if value.name == "SNA" else value.name
        return value

    def _lost(self, message: str, now: float) -> bool:
        m = self.by_name.get(message)
        return m is not None and not m.alive(now)

    def _request(self, signal: str, now: float) -> str:
        """Off / On / Flash for a telltale request, with its message's failsafe."""
        for message, signals in FAILSAFE.items():
            if signal in signals and self._lost(message, now):
                return "On"
        value = self._get(signal, "Off", now)
        return value if value in ("On", "Flash") else "Off"

    @Slot()
    def _step(self) -> None:
        now = time.monotonic()
        dt = min(0.2, now - self._last_task)
        self._last_task = now
        kl15 = self._get("BCM_KL15", "Off", now)
        awake = kl15 in ("On", "Start") and now - self._last_frame < SLEEP_S
        if not awake:
            self._enter("off", now)
        elif self.state == "off":
            self._enter("boot", now)
        elif self.state == "boot" and now - self._since >= self.boot_s:
            self._enter("check", now)
        elif self.state == "check" and now - self._since >= self.check_s:
            self._enter("run", now)
        if now - self._flash_since >= FLASH_MS / 1000.0:
            self._flash_on = not self._flash_on
            self._flash_since = now
        if self.state == "check":
            self._sweep(now)
        elif self.state == "run":
            self._run(now, dt)
        self._transmit(now)

    def _enter(self, state: str, now: float) -> None:
        if state == self.state:
            return
        self.state = state
        self._since = now
        v = self.v
        v.power = state
        # The BMW design plays its own wake-up on the ignition coming on.
        v.ignition = 2 if state in ("check", "run") else 0
        if state in ("off", "boot"):
            v.speed = 0.0
            v.rpm = 0.0

    def _sweep(self, now: float) -> None:
        """The bulb check's needle sweep: up, hold, down."""
        t = (now - self._since) / max(self.check_s, 1e-6)
        k = min(1.0, t / 0.4) if t < 0.4 else (1.0 if t < 0.6 else max(0.0, (1.0 - t) / 0.4))
        v = self.v
        v.speed = round(220.0 * k, 1)
        v.rpm = round(8000.0 * k, 0)
        v.flashing = ""

    def _run(self, now: float, dt: float) -> None:
        v = self.v
        g = lambda s, d=None: self._get(s, d, now)  # noqa: E731
        speed = g("ESC_VehicleSpeed")
        v.speedValid = speed is not None
        v.speed = round(float(speed or 0.0), 1)
        v.rpm = round(float(g("ECM_EngineSpeed", 0.0)), 0)
        v.engineRunning = g("ECM_EngineRunning", "Stopped") == "Running"
        if v.engineRunning:
            self._engine_has_run = True
        gear = g("TCU_GearSel")
        v.gearMode = gear if gear in ("P", "R", "N", "D") else "-"
        v.gearNumber = int(g("TCU_GearActual", 0)) if gear == "D" else 0
        mode = g("TCU_DriveMode")
        if mode in ("Comfort", "Eco", "Sport", "Smart"):
            v.driveMode = mode
        v.message = MESSAGES.get(str(g("TCU_DriverMsg", "None")), "")
        v.sportShiftLights = g("ECM_ShiftUp_Req", "Off") == "On"
        coolant = g("ECM_CoolantTemp")
        if coolant is not None:
            v.coolantTemp = float(coolant)
        oil = g("ECM_OilTemp")
        if oil is not None:
            v.oilTemp = float(oil)
        fuel = g("ECM_FuelLevel")
        if fuel is not None:
            v.fuelLevel = max(0.0, min(1.0, float(fuel) / 100.0))
        outside = g("BCM_OutsideTemp")
        if outside is not None:
            v.outsideTemp = float(outside)

        flashing = set()
        for signal, (icon, flag) in REQUESTS.items():
            req = self._request(signal, now)
            setattr(v, flag, req != "Off")
            if req == "Flash":
                flashing.add(icon)
        epb = g("ESC_EPB_Sts", "Released")
        v.parkBrake = epb in ("Applied", "Fault")
        if epb == "Fault":
            flashing.add("park_brake")
        # Coolant warning: requested, or seen by the cluster itself.
        v.engineTempWarn = (self._request("ECM_CoolantWarn_TtReq", now) != "Off"
                            or v.coolantTemp >= 118.0)
        # Low fuel, with hysteresis so it does not chatter at the line.
        level = v.fuelLevel * 100.0
        self._fuel_low = level <= 12.0 or (self._fuel_low and level < 15.0)
        v.lowFuel = self._fuel_low
        # Lights.
        head = g("BCM_HeadlampSts", "Off")
        v.headlightMode = {"Off": 0, "Position": 1, "LowBeam": 2, "Auto": 3}.get(head, 0)
        v.autoHighBeam = g("BCM_AutoHighBeam", "Off") == "On"
        left, right = g("BCM_TurnLeft_Ind", "Off"), g("BCM_TurnRight_Ind", "Off")
        v.turnLeft, v.turnRight, v.hazard = left != "Off", right != "Off", False
        if left == "Flash":
            flashing.add("turn_left")
        if right == "Flash":
            flashing.add("turn_right")
        # Body.
        for prop, sig in (("doorFL", "BCM_DoorFL"), ("doorFR", "BCM_DoorFR"),
                          ("doorRL", "BCM_DoorRL"), ("doorRR", "BCM_DoorRR"),
                          ("trunk", "BCM_Trunk"), ("hood", "BCM_Hood")):
            setattr(v, prop, g(sig, "Closed") == "Open")
        # Seat belts: a belt in use and unbuckled lights the lamp, and above
        # 25 km/h it flashes.
        driver = g("SRS_BuckleDriver", "Buckled")
        passenger = g("SRS_BucklePass", "Buckled")
        occupied = g("SRS_PassOccupied", "Occupied") == "Occupied"
        v.beltDriver = driver != "Unbuckled"
        v.beltPassenger = passenger != "Unbuckled" or not occupied
        if (not v.beltDriver or not v.beltPassenger) and v.speed >= BELT_FLASH_KMH:
            flashing.add("seatbelt")
        # Driver assistance.
        cc = g("ADAS_CC_Sts", "Off")
        v.cruiseEnabled = cc in ("Ready", "Active")
        v.cruiseActive = cc == "Active"
        v.cruiseSetSpeed = int(g("ADAS_CC_SetSpeed", 0) or 0)
        ldw = g("ADAS_LDW_Sts", "Off")
        v.ldwEnabled = ldw in ("Ready", "WarnLeft", "WarnRight")
        v.laneDeparture = {"WarnLeft": "left", "WarnRight": "right"}.get(ldw, "none")
        if v.laneDeparture != "none":
            flashing.add("lane_warn")
        v.laneLeftDetected = g("ADAS_LaneLeft", "Detected") == "Detected"
        v.laneRightDetected = g("ADAS_LaneRight", "Detected") == "Detected"
        # Electric drive and media.
        v.ePower = float(g("VCU_ePower", 0.0) or 0.0)
        soc = g("VCU_SOC")
        if soc is not None:
            v.batteryLevel = max(0.0, min(1.0, float(soc) / 100.0))
        v.chargingNow = g("VCU_Charging", "Off") == "On"
        v.mediaPlaying = g("MMI_Playing", "Paused") == "Playing"
        v.mediaElapsed = int(g("MMI_Elapsed", 0) or 0)
        v.mediaDuration = int(g("MMI_Duration", 0) or 0)

        v.flashing = "," + ",".join(sorted(flashing)) + "," if flashing else ""
        v.blinkOn = self._flash_on if flashing else False
        self._trip(now, dt, g)

    def _trip(self, now: float, dt: float, g) -> None:
        """The trip computer and the odometer, which the cluster keeps itself."""
        v = self.v
        pressed = g("SWM_TripReset", "Released") == "Pressed"
        if pressed and not self._trip_reset_was:
            self._trip_m = self._trip_fuel_l = self._trip_s = 0.0
            v.resetTrip()
        self._trip_reset_was = pressed
        metres = (v.speed / 3.6) * dt if v.speedValid else 0.0
        self._odo_m += metres
        self._trip_m += metres
        self._trip_s += dt
        rate = float(g("ECM_FuelRate", 0.0) or 0.0)
        self._trip_fuel_l += rate * dt / 3600.0
        v.odometer = round(self._odo_m / 1000.0, 1)
        v.tripDistance = round(self._trip_m / 1000.0, 1)
        v.tripSeconds = int(self._trip_s)
        v.tripFuelUsed = self._trip_fuel_l
        km = self._trip_m / 1000.0
        if self._trip_fuel_l > 0.05:
            v.avgConsumption = round(km / self._trip_fuel_l, 1)
        v.instantConsumption = min(30.0, v.speed / rate) if rate > 0.05 and v.speed > 1.0 else 0.0
        if self._trip_s > 1.0:
            v.avgSpeed = round(km / (self._trip_s / 3600.0), 1)
        if self._engine_has_run:
            efficiency = v.avgConsumption if v.avgConsumption > 1.0 else NOMINAL_KM_PER_L
            v.rangeKm = round(v.fuelLevel * TANK_L * efficiency)

    # -- transmitting ----------------------------------------------------------------

    def _transmit(self, now: float) -> None:
        if now < self._tx_due or self.state == "off" and now - self._last_frame > SLEEP_S:
            return
        import can

        self._tx_due = now + 0.1
        for m in self.tx:
            raw = {s.name: 0 for s in m.signals}
            if "IPC_DisplaySts" in raw:
                raw["IPC_DisplaySts"] = {"off": 0, "boot": 1, "check": 2, "run": 3}[self.state]
            if "IPC_Odometer" in raw:
                raw["IPC_Odometer"] = int(round(self._odo_m / 100.0))
            p = Protection(m)
            data = p.protect(raw, self._tx_counter) if p.active else \
                m.encode(raw, scaling=False, strict=False)
            try:
                self.bus.send(can.Message(arbitration_id=m.frame_id, data=data,
                                          is_extended_id=m.is_extended_frame))
            except Exception:
                pass
        self._tx_counter = (self._tx_counter + 1) % 15
