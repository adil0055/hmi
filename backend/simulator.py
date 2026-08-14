"""Driving simulation that feeds `VehicleState`.

A deliberately small longitudinal vehicle model: engine torque curve ->
gearbox -> wheels -> road load.  It is not trying to be a physics package, it
is trying to make every needle on the cluster move the way a driver expects so
the HMI can be exercised realistically.

`simulationMode == "manual"` disables the model so the control panel can drive
speed / rpm / fuel directly.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Slot

from .vehicle import VehicleState

# --- vehicle parameters (roughly a 1.2 L hatchback) ------------------------
MASS = 1180.0  # kg
WHEEL_RADIUS = 0.297  # m
DRAG_AREA = 0.68  # Cd * A
AIR_DENSITY = 1.20  # kg/m^3
ROLL_RESIST = 0.013
FINAL_DRIVE = 4.06
GEAR_RATIOS = (3.55, 2.02, 1.35, 1.03, 0.82, 0.68)
IDLE_RPM = 780.0
MAX_RPM = 6800.0
REDLINE_RPM = 6500.0
SHIFT_UP_RPM = 2400.0  # scaled up with throttle
SHIFT_DOWN_RPM = 1250.0
MAX_BRAKE_FORCE = 9500.0  # N
REVERSE_RATIO = 3.20
NOMINAL_KM_PER_L = 14.87  # used for range until a trip average exists

TICK_MS = 16  # ~60 Hz
MAX_STEP = 0.10  # clamp dt after a stall so nothing teleports


def _torque_nm(rpm: float) -> float:
    """Peaky-but-flat torque curve, N*m at the crank."""
    if rpm < 500.0:
        return 60.0
    # Peak of ~118 N*m around 4200 rpm, tapering either side.
    x = (rpm - 4200.0) / 3000.0
    return max(15.0, 118.0 * (1.0 - 0.55 * x * x))


class Simulator(QObject):
    """Advances `VehicleState` on a fixed timer."""

    def __init__(self, vehicle: VehicleState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.v = vehicle
        self._speed_ms = 0.0  # signed: negative while reversing
        self._rpm = 0.0
        self._trip_m = 0.0
        self._odo_m = vehicle.odometer * 1000.0
        self._trip_ms = 0
        self._shift_cooldown = 0.0
        self._blink_accum = 0.0
        self._instant_lph = 0.0
        self._engine_has_run = False

        # Integrate against the wall clock rather than assuming every timeout
        # lands exactly TICK_MS apart; a loaded machine drops frames, and a
        # fixed step would quietly make the car travel slower than real time.
        self._clock = QElapsedTimer()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

        self._blink = QTimer(self)
        self._blink.setInterval(380)
        self._blink.timeout.connect(self._toggle_blink)

        vehicle.tripReset.connect(self._on_trip_reset)

    def start(self) -> None:
        self._clock.start()
        self._timer.start()
        self._blink.start()

    # ----------------------------------------------------------------- blink
    def _toggle_blink(self) -> None:
        v = self.v
        if v.hazard or v.turnLeft or v.turnRight:
            v.blinkOn = not v.blinkOn
        elif v.blinkOn:
            v.blinkOn = False

    def _on_trip_reset(self) -> None:
        self._trip_m = 0.0
        self._trip_ms = 0

    # ------------------------------------------------------------------ tick
    @Slot()
    def _tick(self) -> None:
        dt = min(MAX_STEP, max(0.001, self._clock.restart() / 1000.0))
        v = self.v

        if v.engineRunning:
            self._engine_has_run = True

        if v.simulationMode != "sim":
            # Manual mode: the panel owns speed/rpm, we only keep the clock,
            # the odometer and the range estimate coherent.
            self._speed_ms = v.speed / 3.6
            self._rpm = v.rpm
            self._advance_trip(dt)
            self._update_range()
            return

        self._update_engine(dt)
        self._update_motion(dt)
        self._update_fuel(dt)
        self._update_temps(dt)
        self._advance_trip(dt)
        self._update_range()
        self._publish()

    # ---------------------------------------------------------------- engine
    def _update_engine(self, dt: float) -> None:
        v = self.v
        if not v.engineRunning:
            # Spin down to a stop.
            self._rpm = max(0.0, self._rpm - 2600.0 * dt)
            return

        throttle = v.throttle
        if v.driveMode == "Sport":
            throttle = min(1.0, throttle * 1.18)
        elif v.driveMode == "Eco":
            throttle *= 0.78

        gear_ratio = self._current_ratio()
        wheel_rpm = abs(self._speed_ms) / (2.0 * math.pi * WHEEL_RADIUS) * 60.0
        locked_rpm = wheel_rpm * gear_ratio * FINAL_DRIVE if gear_ratio else 0.0

        if v.gearMode in ("P", "N") or locked_rpm < IDLE_RPM * 1.15:
            # Free-revving / torque-converter slip near standstill.
            target = IDLE_RPM + throttle * (MAX_RPM - IDLE_RPM)
            if v.gearMode in ("D", "R") and v.brake < 0.05:
                target = max(target * 0.55, IDLE_RPM)
            rate = 7200.0 if target > self._rpm else 3400.0
            self._rpm += max(-rate * dt, min(rate * dt, target - self._rpm))
        else:
            self._rpm += (locked_rpm - self._rpm) * min(1.0, 12.0 * dt)

        self._rpm = max(0.0, min(MAX_RPM, self._rpm))
        v.sportShiftLights = self._rpm >= REDLINE_RPM - 400.0

    def _current_ratio(self) -> float:
        v = self.v
        if v.gearMode == "D":
            return GEAR_RATIOS[max(0, min(len(GEAR_RATIOS) - 1, v.gearNumber - 1))]
        if v.gearMode == "R":
            return REVERSE_RATIO
        return 0.0

    def _maybe_shift(self) -> None:
        v = self.v
        if v.gearMode != "D" or self._shift_cooldown > 0.0:
            return
        up = SHIFT_UP_RPM + v.throttle * 3400.0
        if v.driveMode == "Sport":
            up += 900.0
        elif v.driveMode == "Eco":
            up -= 500.0
        up = min(up, REDLINE_RPM - 100.0)

        if self._rpm > up and v.gearNumber < len(GEAR_RATIOS):
            v.gearNumber += 1
            self._shift_cooldown = 0.55
        elif self._rpm < SHIFT_DOWN_RPM and v.gearNumber > 1:
            v.gearNumber -= 1
            self._shift_cooldown = 0.45

    # ---------------------------------------------------------------- motion
    def _update_motion(self, dt: float) -> None:
        v = self.v
        self._shift_cooldown = max(0.0, self._shift_cooldown - dt)

        ratio = self._current_ratio()
        drive_force = 0.0
        if v.engineRunning and ratio and v.fuelLevel > 0.0:
            throttle = v.throttle
            if v.driveMode == "Eco":
                throttle *= 0.8
            wheel_torque = _torque_nm(self._rpm) * ratio * FINAL_DRIVE * 0.90
            drive_force = wheel_torque * throttle / WHEEL_RADIUS
            # Idle creep, as an automatic does.
            if throttle < 0.02 and abs(self._speed_ms) < 3.0 and v.brake < 0.05:
                drive_force = 900.0
            if v.gearMode == "R":
                drive_force = -drive_force
        elif v.engineRunning and ratio and v.fuelLevel <= 0.0:
            v.engineRunning = False

        # Cruise control: simple proportional controller on the throttle.
        if v.cruiseActive and v.gearMode == "D" and v.engineRunning:
            err = v.cruiseSetSpeed - abs(self._speed_ms) * 3.6
            v.throttle = max(0.0, min(1.0, 0.06 * err))

        speed = self._speed_ms
        drag = 0.5 * AIR_DENSITY * DRAG_AREA * speed * abs(speed)
        roll = ROLL_RESIST * MASS * 9.81 * (1.0 if speed > 0 else -1.0 if speed < 0 else 0.0)
        braking = MAX_BRAKE_FORCE * v.brake
        if v.parkBrake:
            braking = max(braking, MAX_BRAKE_FORCE * 0.45)
        brake_force = braking * (1.0 if speed > 0 else -1.0 if speed < 0 else 0.0)

        net = drive_force - drag - roll - brake_force
        speed += net / MASS * dt

        # Don't let braking drag the car backwards through zero.
        if self._speed_ms > 0 >= speed and (v.brake > 0.0 or v.parkBrake):
            speed = 0.0
        elif self._speed_ms < 0 <= speed and (v.brake > 0.0 or v.parkBrake):
            speed = 0.0
        if v.gearMode in ("P",):
            speed *= 0.90
            if abs(speed) < 0.15:
                speed = 0.0

        # Reverse is limited, as it is by the gearing in a real car.
        if v.gearMode == "R":
            speed = max(speed, -11.0)
        self._speed_ms = speed

        # ABS / ESC flicker under heavy braking or hard launches.
        v.escActive = v.brake > 0.85 and abs(speed) > 8.0 and not v.escOff

        self._maybe_shift()

    # ------------------------------------------------------------------ fuel
    def _update_fuel(self, dt: float) -> None:
        v = self.v
        if not v.engineRunning:
            self._instant_lph = 0.0
            v.instantConsumption = 0.0
            return

        # Idle draw plus a load term; enough to make the gauge and the trip
        # computer behave believably over a drive.
        load = v.throttle * (self._rpm / MAX_RPM)
        lph = 0.62 + 17.5 * load + 0.00028 * self._rpm
        if v.driveMode == "Eco":
            lph *= 0.88
        elif v.driveMode == "Sport":
            lph *= 1.12
        self._instant_lph = lph

        litres = lph * dt / 3600.0
        if litres > 0.0 and v.tankCapacity > 0.0:
            level = max(0.0, v.fuelLevel - litres / v.tankCapacity)
            v.fuelLevel = level
            v.tripFuelUsed = v.tripFuelUsed + litres
            if level <= 0.0:
                v.engineRunning = False
                v.message = "Out of fuel"

        kmh = abs(self._speed_ms) * 3.6
        v.instantConsumption = min(30.0, kmh / lph) if lph > 0.05 and kmh > 1.0 else 0.0

    # ----------------------------------------------------------------- temps
    def _update_temps(self, dt: float) -> None:
        v = self.v
        ambient = v.outsideTemp
        if v.engineRunning:
            load = 0.35 + 0.65 * v.throttle
            target = 88.0 + 14.0 * load
            # Airflow at speed and the fan above 100 C both pull heat out.
            cooling = 1.0 + abs(self._speed_ms) * 0.02
            if v.coolantTemp > 100.0:
                cooling *= 2.2
            rate = 0.09 * load + 0.02 * cooling
            v.coolantTemp = v.coolantTemp + (target - v.coolantTemp) * min(1.0, rate * dt)
            v.oilTemp = v.oilTemp + (v.coolantTemp + 12.0 - v.oilTemp) * min(1.0, 0.05 * dt)
        else:
            v.coolantTemp = v.coolantTemp + (ambient - v.coolantTemp) * min(1.0, 0.012 * dt)
            v.oilTemp = v.oilTemp + (ambient - v.oilTemp) * min(1.0, 0.010 * dt)

    # --------------------------------------------------------- trip computer
    def _advance_trip(self, dt: float) -> None:
        v = self.v
        metres = abs(self._speed_ms) * dt
        self._trip_m += metres
        self._odo_m += metres

        v.odometer = round(self._odo_m / 1000.0, 1)
        v.tripDistance = round(self._trip_m / 1000.0, 1)

        if v.engineRunning:
            self._trip_ms += int(dt * 1000.0)
            v.tripSeconds = self._trip_ms // 1000

        trip_km = self._trip_m / 1000.0
        # Wait for a little distance and fuel before showing an average, so the
        # first reading isn't a division by almost nothing.
        if v.tripFuelUsed > 0.02 and trip_km > 0.05:
            v.avgConsumption = round(trip_km / v.tripFuelUsed, 1)
        if v.tripSeconds > 0:
            v.avgSpeed = round(trip_km / (v.tripSeconds / 3600.0), 1)

    def _update_range(self) -> None:
        v = self.v
        # Keep the powered-up default until the engine has actually run once;
        # a cluster shows the last computed range, not a live guess at rest.
        if not self._engine_has_run:
            return
        litres = v.fuelLevel * v.tankCapacity
        # Fall back to a nominal efficiency until the trip average settles.
        efficiency = v.avgConsumption if v.avgConsumption > 1.0 else NOMINAL_KM_PER_L
        v.rangeKm = round(litres * efficiency)

    # --------------------------------------------------------------- publish
    def _publish(self) -> None:
        v = self.v
        v.speed = round(abs(self._speed_ms) * 3.6, 1)
        v.rpm = round(self._rpm, 0)
