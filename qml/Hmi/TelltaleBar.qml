import QtQuick
import Hmi

/*!
    The row of warning lamps across the top of the display, plus the two turn
    indicators that flank it.

    Only lit lamps take up space, so an idle cluster shows an empty strip —
    exactly as it does on the reference screenshot.  Lamps are ordered by
    severity: red stop lamps first, then amber cautions, then blue/green status.
*/
Item {
    id: root

    property var vehicle: null

    // Geometry is a parameter rather than a constant so the BMW cluster can
    // reuse the lamp table below at its own size and position.
    property real lampSize: Theme.telltaleSize
    property real gap: Theme.telltaleGap
    property real rowWidth: Theme.telltaleRowWidth
    property real centreX: Theme.centreX
    property real rowY: Theme.telltaleY
    property real turnLeftX: Theme.turnLeftX
    property real turnRightX: Theme.turnRightX
    property real turnSize: Theme.turnSize

    anchors.fill: parent

    readonly property var lamps: [
        // -- red: stop --------------------------------------------------
        { icon: "brake",        on: vehicle ? vehicle.brakeSystem : false,  blink: false },
        { icon: "park_brake",   on: vehicle ? vehicle.parkBrake : false,    blink: false },
        { icon: "oil",          on: vehicle ? vehicle.oilPressure : false,  blink: false },
        { icon: "battery",      on: vehicle ? vehicle.batteryCharge : false, blink: false },
        { icon: "temp_warn",    on: vehicle ? vehicle.engineTempWarn : false, blink: false },
        { icon: "airbag",       on: vehicle ? vehicle.airbagFault : false,  blink: false },
        { icon: "seatbelt",     on: vehicle ? (!vehicle.beltDriver || !vehicle.beltPassenger) : false,
                                blink: true },
        { icon: "door_open",    on: vehicle ? vehicle.doorAjar : false,     blink: false },
        { icon: "fca",          on: vehicle ? vehicle.fcaWarn : false,      blink: true },
        // -- amber: caution ---------------------------------------------
        { icon: "check_engine", on: vehicle ? vehicle.checkEngine : false,  blink: false },
        { icon: "abs",          on: vehicle ? vehicle.absFault : false,     blink: false },
        { icon: "esc",          on: vehicle ? vehicle.escActive : false,    blink: true },
        { icon: "esc_off",      on: vehicle ? vehicle.escOff : false,       blink: false },
        { icon: "traction_off", on: vehicle ? vehicle.tractionOff : false,  blink: false },
        { icon: "eps",          on: vehicle ? vehicle.epsFault : false,     blink: false },
        { icon: "tpms",         on: vehicle ? vehicle.tpms : false,         blink: false },
        { icon: "low_fuel",     on: vehicle ? vehicle.lowFuel : false,      blink: false },
        { icon: "washer",       on: vehicle ? vehicle.washerFluid : false,  blink: false },
        { icon: "glow_plug",    on: vehicle ? vehicle.glowPlug : false,     blink: false },
        { icon: "immobilizer",  on: vehicle ? vehicle.immobilizer : false,  blink: true },
        { icon: "lane_warn",    on: vehicle ? vehicle.laneDeparture !== "none" : false, blink: true },
        { icon: "fog_rear",     on: vehicle ? vehicle.rearFog : false,      blink: false },
        // -- blue / green: status ---------------------------------------
        { icon: "high_beam",    on: vehicle ? vehicle.highBeam : false,     blink: false },
        { icon: "low_beam",     on: vehicle ? vehicle.headlightMode === 2 : false, blink: false },
        { icon: "position_light", on: vehicle ? vehicle.headlightMode === 1 : false, blink: false },
        { icon: "fog_front",    on: vehicle ? vehicle.frontFog : false,     blink: false },
        { icon: "cruise",       on: vehicle ? vehicle.cruiseActive : false, blink: false },
        { icon: "cruise_ready", on: vehicle ? (vehicle.cruiseEnabled && !vehicle.cruiseActive) : false,
                                blink: false },
        { icon: "lane_departure", on: vehicle ? (vehicle.ldwEnabled && vehicle.laneDeparture === "none") : false,
                                blink: false }
    ]

    readonly property int activeCount: {
        var n = 0
        for (var i = 0; i < lamps.length; ++i)
            if (lamps[i].on)
                n++
        return n
    }
    readonly property int perRow:
        Math.max(1, Math.floor((root.rowWidth + root.gap) / (root.lampSize + root.gap)))

    Flow {
        id: strip
        spacing: root.gap
        // Sized to the lamps actually lit, so the group stays centred.
        width: Math.max(root.lampSize,
                        Math.min(root.activeCount, root.perRow)
                        * (root.lampSize + root.gap) - root.gap)
        x: root.centreX - width / 2
        y: root.rowY - root.lampSize / 2

        Repeater {
            model: root.lamps
            delegate: Telltale {
                required property var modelData
                source: Theme.icon(modelData.icon)
                active: modelData.on
                blinking: modelData.blink
                blinkPhase: root.vehicle ? root.vehicle.blinkOn : true
                width: root.lampSize
                height: root.lampSize
            }
        }
    }

    Telltale {
        source: Theme.icon("turn_left")
        width: root.turnSize
        height: root.turnSize
        x: root.turnLeftX - width / 2
        y: root.rowY - height / 2
        active: root.vehicle ? (root.vehicle.turnLeft || root.vehicle.hazard) : false
        blinking: true
        blinkPhase: root.vehicle ? root.vehicle.blinkOn : true
    }

    Telltale {
        source: Theme.icon("turn_right")
        width: root.turnSize
        height: root.turnSize
        x: root.turnRightX - width / 2
        y: root.rowY - height / 2
        active: root.vehicle ? (root.vehicle.turnRight || root.vehicle.hazard) : false
        blinking: true
        blinkPhase: root.vehicle ? root.vehicle.blinkOn : true
    }
}
