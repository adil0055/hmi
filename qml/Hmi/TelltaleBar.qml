import QtQuick
import Hmi

/*!
    The bank of warning lamps across the top of the display, plus the two turn
    indicators that flank it.

    Every lamp has its own fixed slot, as on a production cluster: the symbol
    is printed at one place on the display and only lights or goes dark there.
    Nothing moves when other lamps come on or go off, so the driver (and a
    camera) always finds a lamp where it was. The bank is a grid of
    \l columns per row, rows centred on \l centreX, the bank centred on
    \l rowY; lamps are ordered by severity: red stop lamps first, then amber
    cautions, then blue/green status.
*/
Item {
    id: root

    property var vehicle: null

    // Geometry is a parameter rather than a constant so the BMW cluster can
    // reuse the lamp table below at its own size and position.
    property real lampSize: Theme.telltaleSize
    property real gap: Theme.telltaleGap
    property real rowGap: Theme.telltaleRowGap
    property int columns: Theme.telltaleColumns
    property real centreX: Theme.centreX
    /*! The vertical centre of the bank, and of the turn arrows. */
    property real rowY: Theme.telltaleY
    property real turnLeftX: Theme.turnLeftX
    property real turnRightX: Theme.turnRightX
    property real turnSize: Theme.turnSize

    anchors.fill: parent

    /*! The bulb check at start-up: every lamp lit, none flashing. */
    readonly property bool check: vehicle ? vehicle.power === "check" : false
    /*! Lamps the cluster is flashing now, as ",abs,seatbelt,". */
    readonly property string flashing: vehicle ? vehicle.flashing : ""
    function flashes(icon) { return !check && flashing.indexOf("," + icon + ",") >= 0 }

    readonly property var lamps: [
        // -- red: stop --------------------------------------------------
        { icon: "brake",        on: check || (vehicle ? vehicle.brakeSystem : false) },
        { icon: "park_brake",   on: check || (vehicle ? vehicle.parkBrake : false) },
        { icon: "oil",          on: check || (vehicle ? vehicle.oilPressure : false) },
        { icon: "battery",      on: check || (vehicle ? vehicle.batteryCharge : false) },
        { icon: "temp_warn",    on: check || (vehicle ? vehicle.engineTempWarn : false) },
        { icon: "airbag",       on: check || (vehicle ? vehicle.airbagFault : false) },
        { icon: "seatbelt",     on: check || (vehicle ? (!vehicle.beltDriver || !vehicle.beltPassenger) : false) },
        { icon: "door_open",    on: check || (vehicle ? vehicle.doorAjar : false) },
        { icon: "fca",          on: check || (vehicle ? vehicle.fcaWarn : false) },
        // -- amber: caution ---------------------------------------------
        { icon: "check_engine", on: check || (vehicle ? vehicle.checkEngine : false) },
        { icon: "abs",          on: check || (vehicle ? vehicle.absFault : false) },
        { icon: "esc",          on: check || (vehicle ? vehicle.escActive : false) },
        { icon: "esc_off",      on: check || (vehicle ? vehicle.escOff : false) },
        { icon: "traction_off", on: check || (vehicle ? vehicle.tractionOff : false) },
        { icon: "eps",          on: check || (vehicle ? vehicle.epsFault : false) },
        { icon: "tpms",         on: check || (vehicle ? vehicle.tpms : false) },
        { icon: "low_fuel",     on: check || (vehicle ? vehicle.lowFuel : false) },
        { icon: "washer",       on: check || (vehicle ? vehicle.washerFluid : false) },
        { icon: "glow_plug",    on: check || (vehicle ? vehicle.glowPlug : false) },
        { icon: "immobilizer",  on: check || (vehicle ? vehicle.immobilizer : false) },
        { icon: "lane_warn",    on: check || (vehicle ? vehicle.laneDeparture !== "none" : false) },
        { icon: "fog_rear",     on: check || (vehicle ? vehicle.rearFog : false) },
        // -- blue / green: status ---------------------------------------
        { icon: "high_beam",    on: check || (vehicle ? vehicle.highBeam : false) },
        { icon: "low_beam",     on: check || (vehicle ? vehicle.headlightMode === 2 : false) },
        { icon: "position_light", on: check || (vehicle ? vehicle.headlightMode === 1 : false) },
        { icon: "fog_front",    on: check || (vehicle ? vehicle.frontFog : false) },
        { icon: "cruise",       on: check || (vehicle ? vehicle.cruiseActive : false) },
        { icon: "cruise_ready", on: check || (vehicle ? (vehicle.cruiseEnabled && !vehicle.cruiseActive) : false) },
        { icon: "lane_departure", on: check || (vehicle ? (vehicle.ldwEnabled && vehicle.laneDeparture === "none") : false) }
    ]

    readonly property int rows: Math.ceil(lamps.length / Math.max(1, columns))
    readonly property real bankHeight: rows * lampSize + (rows - 1) * rowGap

    /*! The top-left corner of lamp \a index's slot, from its index alone. */
    function slotX(index) {
        var cols = Math.max(1, root.columns)
        var row = Math.floor(index / cols)
        var inRow = Math.min(cols, root.lamps.length - row * cols)
        var width = inRow * root.lampSize + (inRow - 1) * root.gap
        return root.centreX - width / 2 + (index % cols) * (root.lampSize + root.gap)
    }
    function slotY(index) {
        var row = Math.floor(index / Math.max(1, root.columns))
        return root.rowY - root.bankHeight / 2 + row * (root.lampSize + root.rowGap)
    }

    Repeater {
        model: root.lamps
        delegate: Telltale {
            required property var modelData
            required property int index
            source: Theme.icon(modelData.icon)
            active: modelData.on
            blinking: root.flashes(modelData.icon)
            blinkPhase: root.vehicle ? root.vehicle.blinkOn : true
            width: root.lampSize
            height: root.lampSize
            x: root.slotX(index)
            y: root.slotY(index)
        }
    }

    Telltale {
        source: Theme.icon("turn_left")
        width: root.turnSize
        height: root.turnSize
        x: root.turnLeftX - width / 2
        y: root.rowY - height / 2
        active: root.check || (root.vehicle ? (root.vehicle.turnLeft || root.vehicle.hazard) : false)
        blinking: root.flashes("turn_left")
        blinkPhase: root.vehicle ? root.vehicle.blinkOn : true
    }

    Telltale {
        source: Theme.icon("turn_right")
        width: root.turnSize
        height: root.turnSize
        x: root.turnRightX - width / 2
        y: root.rowY - height / 2
        active: root.check || (root.vehicle ? (root.vehicle.turnRight || root.vehicle.hazard) : false)
        blinking: root.flashes("turn_right")
        blinkPhase: root.vehicle ? root.vehicle.blinkOn : true
    }
}
