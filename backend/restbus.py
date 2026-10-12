"""The rest of the vehicle, on the bus: what the cluster's CAN partners send.

On a bench, a cluster is driven by a rest-bus simulation standing in for the
car's other ECUs (BCM, ECM, ESC, TCU, SRS, ...). This is that, for the test
panel and the driving model: each message of the matrix (can/cluster.dbc)
not sent by the cluster goes out at its own cycle time, encoded from the
vehicle's state, with its alive counter and CRC where it has them.

The cluster (backend.ecu) never reads the panel directly; it sees only these
frames, so anything else that sends the same frames -- a test tool, a HIL
rig, the car -- drives it the same way.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot

from .e2e import Protection
from .vehicle import VehicleState

DEFAULT_DBC = Path(__file__).resolve().parent.parent / "can" / "cluster.dbc"

KL15 = {0: "Off", 1: "Acc", 2: "On", 3: "Start"}
MESSAGE_IDS = {
    "Press brake pedal to shift": "PressBrake", "Vehicle moving": "VehicleMoving",
    "Select P or N to start": "SelectPN", "Out of fuel": "OutOfFuel",
}
TRIP_RESET_S = 0.3


def _req(on: bool, flash: bool = False) -> str:
    return "Flash" if flash else ("On" if on else "Off")


def vehicle_signals(v: VehicleState, trip_reset: bool = False) -> dict:
    """Every signal the vehicle sends, from its state: physical values or value names."""
    left = v.turnLeft or v.hazard
    right = v.turnRight or v.hazard
    cc = "Active" if v.cruiseActive else ("Ready" if v.cruiseEnabled else "Off")
    if v.laneDeparture == "left":
        ldw = "WarnLeft"
    elif v.laneDeparture == "right":
        ldw = "WarnRight"
    else:
        ldw = "Ready" if v.ldwEnabled else "Off"
    return {
        # ESC
        "ESC_VehicleSpeed": max(0.0, min(655.34, v.speed)),
        "ESC_ABS_TtReq": _req(v.absFault),
        "ESC_ESC_TtReq": _req(False, v.escActive),
        "ESC_ESCOff_TtReq": _req(v.escOff),
        "ESC_TCSOff_TtReq": _req(v.tractionOff),
        "ESC_BrakeWarn_TtReq": _req(v.brakeSystem),
        "ESC_EPB_Sts": "Applied" if v.parkBrake else "Released",
        # ECM
        "ECM_EngineSpeed": max(0.0, min(16383.5, v.rpm)),
        "ECM_EngineRunning": "Running" if v.engineRunning else "Stopped",
        "ECM_MIL_TtReq": _req(v.checkEngine),
        "ECM_OilPress_TtReq": _req(v.oilPressure),
        "ECM_Charge_TtReq": _req(v.batteryCharge),
        "ECM_GlowPlug_TtReq": _req(v.glowPlug),
        "ECM_CoolantWarn_TtReq": "Off",          # the cluster sees the temperature itself
        "ECM_ShiftUp_Req": "On" if v.sportShiftLights else "Off",
        "ECM_CoolantTemp": max(-40.0, min(214.0, v.coolantTemp)),
        "ECM_OilTemp": max(-40.0, min(214.0, v.oilTemp)),
        "ECM_FuelLevel": max(0.0, min(100.0, v.fuelLevel * 100.0)),
        "ECM_FuelRate": max(0.0, min(655.0, v.fuelRate)),
        # TCU
        "TCU_GearSel": v.gearMode if v.gearMode in ("P", "R", "N", "D") else "SNA",
        "TCU_GearActual": max(0, min(15, v.gearNumber)),
        "TCU_DriveMode": v.driveMode if v.driveMode in ("Comfort", "Eco", "Sport", "Smart") else "SNA",
        "TCU_DriverMsg": MESSAGE_IDS.get(v.message, "None"),
        # SRS, EPS, TPMS
        "SRS_Airbag_TtReq": _req(v.airbagFault),
        "SRS_BuckleDriver": "Buckled" if v.beltDriver else "Unbuckled",
        "SRS_BucklePass": "Buckled" if v.beltPassenger else "Unbuckled",
        "SRS_PassOccupied": "Occupied",
        "EPS_Warn_TtReq": _req(v.epsFault),
        "TPMS_Warn_TtReq": _req(v.tpms),
        # ADAS
        "ADAS_CC_Sts": cc,
        "ADAS_CC_SetSpeed": max(0, min(254, v.cruiseSetSpeed)),
        "ADAS_LDW_Sts": ldw,
        "ADAS_LaneLeft": "Detected" if v.laneLeftDetected else "NotDetected",
        "ADAS_LaneRight": "Detected" if v.laneRightDetected else "NotDetected",
        "ADAS_FCW_TtReq": _req(False, v.fcaWarn),
        # BCM
        "BCM_KL15": KL15.get(v.ignition, "Off"),
        "BCM_Immo_TtReq": _req(False, v.immobilizer),
        "BCM_HeadlampSts": {0: "Off", 1: "Position", 2: "LowBeam", 3: "Auto"}.get(v.headlightMode, "Off"),
        "BCM_HighBeam_TtReq": _req(v.highBeam),
        "BCM_FrontFog_TtReq": _req(v.frontFog),
        "BCM_RearFog_TtReq": _req(v.rearFog),
        "BCM_TurnLeft_Ind": _req(False, left),
        "BCM_TurnRight_Ind": _req(False, right),
        "BCM_AutoHighBeam": "On" if v.autoHighBeam else "Off",
        "BCM_DoorFL": "Open" if v.doorFL else "Closed",
        "BCM_DoorFR": "Open" if v.doorFR else "Closed",
        "BCM_DoorRL": "Open" if v.doorRL else "Closed",
        "BCM_DoorRR": "Open" if v.doorRR else "Closed",
        "BCM_Trunk": "Open" if v.trunk else "Closed",
        "BCM_Hood": "Open" if v.hood else "Closed",
        "BCM_WasherLow_TtReq": _req(v.washerFluid),
        "BCM_OutsideTemp": max(-40.0, min(87.0, v.outsideTemp)),
        # VCU, steering wheel, media
        "VCU_ePower": max(-1.28, min(1.27, v.ePower)),
        "VCU_SOC": max(0.0, min(100.0, v.batteryLevel * 100.0)),
        "VCU_Charging": "On" if v.chargingNow else "Off",
        "SWM_TripReset": "Pressed" if trip_reset else "Released",
        "MMI_Playing": "Playing" if v.mediaPlaying else "Paused",
        "MMI_Elapsed": max(0, min(65535, v.mediaElapsed)),
        "MMI_Duration": max(0, min(65535, v.mediaDuration)),
    }


class RestBus(QObject):
    """Sends ``vehicle``'s state on ``bus`` as the matrix's partners do."""

    def __init__(self, vehicle: VehicleState, bus, dbc: str | Path = DEFAULT_DBC,
                 node: str = "IPC", parent: QObject | None = None) -> None:
        super().__init__(parent)
        import cantools

        self.v = vehicle
        self.bus = bus
        self.db = cantools.database.load_file(str(dbc))
        self.messages = [m for m in self.db.messages if node not in m.senders]
        self._protection = {m.frame_id: Protection(m) for m in self.messages}
        self._counter = {m.frame_id: 0 for m in self.messages}
        self._due = {m.frame_id: 0.0 for m in self.messages}
        self._trip_reset_until = 0.0
        self.sent = 0
        vehicle.tripReset.connect(self._on_trip_reset)
        self._timer = QTimer(self)
        self._timer.setInterval(5)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._timer.start()

    def stop(self, *, close: bool = False) -> None:
        self._timer.stop()
        if close:
            try:
                self.bus.shutdown()
            except Exception:
                pass

    @Slot()
    def _on_trip_reset(self) -> None:
        # The steering-wheel button, held long enough to be seen.
        self._trip_reset_until = time.monotonic() + TRIP_RESET_S

    @Slot()
    def _tick(self) -> None:
        import can

        now = time.monotonic()
        values = None
        for m in self.messages:
            if now < self._due[m.frame_id]:
                continue
            self._due[m.frame_id] = now + (m.cycle_time or 100) / 1000.0
            if values is None:
                values = vehicle_signals(self.v, now < self._trip_reset_until)
            raw = {}
            for s in m.signals:
                value = values.get(s.name, 0)
                if isinstance(value, str):
                    raw[s.name] = s.choice_to_number(value)
                else:
                    raw[s.name] = int(round(float(s.scaled_to_raw(value))))
            p = self._protection[m.frame_id]
            if p.active:
                data = p.protect(raw, self._counter[m.frame_id])
                self._counter[m.frame_id] = (self._counter[m.frame_id] + 1) % 15
            else:
                data = m.encode(raw, scaling=False, strict=False)
            try:
                self.bus.send(can.Message(arbitration_id=m.frame_id, data=data,
                                          is_extended_id=m.is_extended_frame))
                self.sent += 1
            except Exception:
                pass
