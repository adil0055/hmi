"""Vehicle state model.

`VehicleState` is the single source of truth the cluster renders from.  Every
signal a real instrument cluster consumes lives here as a notifiable Qt
property, so QML can bind to it directly and the control panel can write to it.

The property list is data-driven (see ``_SPEC``) purely to keep ~90 properties
readable; each one still ends up as a real meta-property with its own
``<name>Changed`` notifier.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

# --------------------------------------------------------------------------
# Property specification: (name, type, default)
# --------------------------------------------------------------------------
_SPEC: list[tuple[str, type, object]] = [
    # -- powertrain ---------------------------------------------------------
    # Powers up in "ignition on, engine not running", which is the state the
    # cluster shows at rest: gear P, 0 km/h, 0 rpm, full instrumentation lit.
    ("ignition", int, 2),  # 0 off, 1 accessory, 2 on, 3 cranking
    ("engineRunning", bool, False),
    ("speed", float, 0.0),  # km/h, always positive (reverse shows magnitude)
    ("rpm", float, 0.0),  # revolutions per minute
    ("throttle", float, 0.0),  # 0..1 pedal travel
    ("brake", float, 0.0),  # 0..1 pedal travel
    ("gearMode", str, "P"),  # P / R / N / D
    ("gearNumber", int, 0),  # active ratio in D, 0 when not applicable
    ("driveMode", str, "Comfort"),  # Comfort / Eco / Sport / Smart
    ("sportShiftLights", bool, False),
    # -- fluids and temperatures -------------------------------------------
    ("fuelLevel", float, 0.14),  # 0..1 of tank
    ("tankCapacity", float, 37.0),  # litres
    ("coolantTemp", float, 20.0),  # degrees C
    ("oilTemp", float, 20.0),  # degrees C
    ("outsideTemp", float, 28.0),  # degrees C
    # -- trip computer ------------------------------------------------------
    ("odometer", float, 25.0),  # km
    ("tripDistance", float, 0.0),  # km
    ("tripSeconds", int, 0),
    ("tripFuelUsed", float, 0.0),  # litres
    ("avgConsumption", float, 0.0),  # km/L, 0 renders as "--.-"
    ("instantConsumption", float, 0.0),  # km/L
    ("avgSpeed", float, 0.0),  # km/h
    ("rangeKm", float, 550.0),  # distance to empty
    ("units", str, "metric"),  # metric / imperial
    ("consumptionUnits", str, "km/L"),  # km/L or L/100km
    # -- exterior lighting --------------------------------------------------
    ("headlightMode", int, 0),  # 0 off, 1 position, 2 low beam, 3 auto
    ("highBeam", bool, False),
    ("autoHighBeam", bool, False),
    ("frontFog", bool, False),
    ("rearFog", bool, False),
    ("turnLeft", bool, False),
    ("turnRight", bool, False),
    ("hazard", bool, False),
    ("blinkOn", bool, False),  # driven by the indicator timer
    # -- body ---------------------------------------------------------------
    ("doorFL", bool, False),
    ("doorFR", bool, False),
    ("doorRL", bool, False),
    ("doorRR", bool, False),
    ("trunk", bool, False),
    ("hood", bool, False),
    ("beltDriver", bool, True),  # True == fastened
    ("beltPassenger", bool, True),
    # -- warning / status telltales ----------------------------------------
    ("parkBrake", bool, False),
    ("brakeSystem", bool, False),
    ("absFault", bool, False),
    ("escActive", bool, False),  # flashes while intervening
    ("escOff", bool, False),
    ("tractionOff", bool, False),
    ("airbagFault", bool, False),
    ("checkEngine", bool, False),
    ("oilPressure", bool, False),
    ("batteryCharge", bool, False),
    ("tpms", bool, False),
    ("lowFuel", bool, False),
    ("washerFluid", bool, False),
    ("glowPlug", bool, False),
    ("engineTempWarn", bool, False),
    ("immobilizer", bool, False),
    ("epsFault", bool, False),
    ("doorAjar", bool, False),  # derived from the six body openings
    # -- driver assistance --------------------------------------------------
    ("cruiseEnabled", bool, False),
    ("cruiseActive", bool, False),
    ("cruiseSetSpeed", int, 0),
    ("ldwEnabled", bool, False),
    ("laneLeftDetected", bool, True),
    ("laneRightDetected", bool, True),
    ("laneDeparture", str, "none"),  # none / left / right
    ("fcaWarn", bool, False),
    # -- misc ---------------------------------------------------------------
    ("message", str, ""),  # transient text shown under Drive info
    ("simulationMode", str, "sim"),  # sim (physics) or manual (direct set)
    ("showBezel", bool, True),
]


def _make_property(name: str, typ: type, sig: Signal) -> Property:
    attr = "_" + name

    def getter(self):
        return getattr(self, attr)

    def setter(self, value):
        if getattr(self, attr) == value:
            return
        setattr(self, attr, value)
        getattr(self, name + "Changed").emit()

    return Property(typ, getter, setter, notify=sig)


def _build_namespace() -> dict:
    signals = {name + "Changed": Signal() for name, _, _ in _SPEC}
    ns: dict = dict(signals)
    for name, typ, default in _SPEC:
        ns["_" + name] = default
        ns[name] = _make_property(name, typ, signals[name + "Changed"])
    return ns


# QObject's metaclass has to build the type so Property/Signal get registered.
_VehicleProps = type(QObject)("_VehicleProps", (QObject,), _build_namespace())


class VehicleState(_VehicleProps):
    """All the values an instrument cluster needs, as bindable properties."""

    #: Emitted when the trip computer is reset, so views can flash an ack.
    tripReset = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Give every instance its own copy of the defaults.
        for name, _, default in _SPEC:
            setattr(self, "_" + name, default)

        for prop in ("doorFL", "doorFR", "doorRL", "doorRR", "trunk", "hood"):
            getattr(self, prop + "Changed").connect(self._refresh_door_ajar)
        self.fuelLevelChanged.connect(self._refresh_low_fuel)
        self.coolantTempChanged.connect(self._refresh_temp_warn)

    # -- derived state ------------------------------------------------------
    def _refresh_door_ajar(self) -> None:
        self.doorAjar = any(
            (self._doorFL, self._doorFR, self._doorRL, self._doorRR, self._trunk, self._hood)
        )

    def _refresh_low_fuel(self) -> None:
        self.lowFuel = self._fuelLevel <= 0.12

    def _refresh_temp_warn(self) -> None:
        self.engineTempWarn = self._coolantTemp >= 118.0

    # -- actions invoked from QML ------------------------------------------
    @Slot()
    def resetTrip(self) -> None:
        self.tripDistance = 0.0
        self.tripSeconds = 0
        self.tripFuelUsed = 0.0
        self.avgConsumption = 0.0
        self.avgSpeed = 0.0
        self.tripReset.emit()

    @Slot(str)
    def setGear(self, gear: str) -> None:
        gear = gear.upper()
        if gear not in ("P", "R", "N", "D"):
            return
        # Refuse to leave Park unless the brake is applied and the engine runs,
        # which is how a real shift interlock behaves.
        if self._gearMode == "P" and gear != "P":
            if not self._engineRunning or self._brake < 0.05:
                self.message = "Press brake pedal to shift"
                return
        # Never allow a direction change while rolling.
        if gear in ("R", "P") and self._speed > 5.0:
            self.message = "Vehicle moving"
            return
        self.message = ""
        self.gearMode = gear
        self.gearNumber = 1 if gear == "D" else 0

    @Slot()
    def toggleHazard(self) -> None:
        self.hazard = not self._hazard

    @Slot(bool)
    def setIgnitionOn(self, on: bool) -> None:
        self.ignition = 2 if on else 0

    @Slot()
    def startStopEngine(self) -> None:
        if self._engineRunning:
            self.engineRunning = False
            self.ignition = 0
            self.rpm = 0.0
            self.cruiseEnabled = False
            self.cruiseActive = False
        else:
            if self._gearMode not in ("P", "N"):
                self.message = "Select P or N to start"
                return
            if self._fuelLevel <= 0.0:
                self.message = "Out of fuel"
                return
            self.message = ""
            self.ignition = 2
            self.engineRunning = True

    @Slot()
    def refuel(self) -> None:
        self.fuelLevel = 1.0

    @Slot(str)
    def flashMessage(self, text: str) -> None:
        self.message = text
