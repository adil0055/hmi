import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window
import Hmi

/*!
    Test bench for the cluster.

    Everything the cluster can display is drivable from here.  Two input
    styles are offered: "Simulate" runs the physics model so the pedals,
    gearbox and fuel burn behave like a car, while "Manual" lets you pin
    speed, rpm and the gauges to exact values for screenshots and edge cases.
*/
Window {
    id: root
    objectName: "controlWindow"

    property var vehicle: null

    title: qsTr("HMI Test Panel")
    width: 470
    height: Math.min(1000, Screen.desktopAvailableHeight - 80)
    color: "#14181D"

    readonly property color panelBg: "#1B2128"
    readonly property color panelLine: "#2B333C"
    readonly property color labelColor: "#93A2B1"
    readonly property color valueColor: "#E6EDF4"
    readonly property color accentColor: "#4FA8E8"

    // ---------------------------------------------------------------- pieces
    component SectionBox: ColumnLayout {
        id: section
        property string title: ""
        Layout.fillWidth: true
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 6
            Text {
                text: section.title.toUpperCase()
                color: root.accentColor
                font.family: Theme.uiFontFamily
                font.pixelSize: 12
                font.letterSpacing: 1.6
                font.weight: Font.DemiBold
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: root.panelLine }
        }
    }

    component Slider2: RowLayout {
        id: row
        property string label: ""
        property real from: 0
        property real to: 1
        property real value: 0
        property int decimals: 2
        property string suffix: ""
        signal moved(real v)

        Layout.fillWidth: true
        spacing: 8

        Text {
            text: row.label
            color: root.labelColor
            font.family: Theme.uiFontFamily
            font.pixelSize: 13
            Layout.preferredWidth: 92
        }

        Slider {
            id: slider
            Layout.fillWidth: true
            from: row.from
            to: row.to
            value: row.value
            onMoved: row.moved(value)
        }

        Text {
            text: row.value.toFixed(row.decimals) + row.suffix
            color: root.valueColor
            font.family: Theme.uiFontFamily
            font.pixelSize: 13
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: 64
        }
    }

    /*!
        A latching-looking button whose appearance comes straight from the
        model.  It is deliberately not `checkable`: letting the control toggle
        its own `checked` state would overwrite the binding to the vehicle, and
        the chip would stop tracking changes made anywhere else.
    */
    component Chip: Button {
        id: chip
        property bool on: false
        implicitHeight: 30
        leftPadding: 10
        rightPadding: 10
        font.family: Theme.uiFontFamily
        font.pixelSize: 12

        background: Rectangle {
            radius: 6
            color: chip.on ? root.accentColor : (chip.hovered ? "#2C353F" : "#232B33")
            border.width: 1
            border.color: chip.on ? root.accentColor : root.panelLine
            opacity: chip.enabled ? 1 : 0.45
        }
        contentItem: Text {
            text: chip.text
            color: chip.on ? "#0D1116" : root.valueColor
            font: chip.font
            opacity: chip.enabled ? 1 : 0.5
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component Action: Button {
        id: act
        implicitHeight: 32
        font.family: Theme.uiFontFamily
        font.pixelSize: 12
        background: Rectangle {
            radius: 6
            color: act.down ? "#39454F" : (act.hovered ? "#2C353F" : "#242D36")
            border.width: 1
            border.color: root.panelLine
        }
        contentItem: Text {
            text: act.text
            color: root.valueColor
            font: act.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    // ------------------------------------------------------------------ body
    ScrollView {
        anchors.fill: parent
        anchors.margins: 14
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 10

            // ------------------------------------------------------ status
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 62
                radius: 8
                color: root.panelBg
                border.width: 1
                border.color: root.panelLine

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 16

                    Repeater {
                        model: [
                            { k: qsTr("Speed"), v: root.vehicle ? root.vehicle.speed.toFixed(0) + " km/h" : "-" },
                            { k: qsTr("Engine"), v: root.vehicle ? root.vehicle.rpm.toFixed(0) + " rpm" : "-" },
                            { k: qsTr("Gear"), v: root.vehicle ? root.vehicle.gearMode : "-" },
                            { k: qsTr("Fuel"), v: root.vehicle ? (root.vehicle.fuelLevel * 100).toFixed(0) + " %" : "-" }
                        ]
                        delegate: ColumnLayout {
                            required property var modelData
                            spacing: 2
                            Text {
                                text: modelData.k
                                color: root.labelColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 11
                            }
                            Text {
                                text: modelData.v
                                color: root.valueColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 16
                            }
                        }
                    }
                }
            }

            // ------------------------------------------------------ typeface
            SectionBox { title: qsTr("Typeface") }

            FileDialog {
                id: fontDialog
                title: qsTr("Choose font files")
                fileMode: FileDialog.OpenFiles
                nameFilters: [qsTr("Font files (*.ttf *.otf *.ttc *.otc *.woff *.woff2)"),
                              qsTr("All files (*)")]
                onAccepted: Fonts.loadFiles(selectedFiles)
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: fontInfo.implicitHeight + 20
                radius: 8
                color: root.panelBg
                border.width: 1
                border.color: root.panelLine

                ColumnLayout {
                    id: fontInfo
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 3

                    Text {
                        Layout.fillWidth: true
                        text: Fonts.family
                        color: root.valueColor
                        font.family: Theme.uiFontFamily
                        font.pixelSize: 15
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: Fonts.isCustom ? Fonts.source : qsTr("bundled with the project")
                        color: root.labelColor
                        font.family: Theme.uiFontFamily
                        font.pixelSize: 11
                        elide: Text.ElideMiddle
                    }
                    // Live preview in the font the cluster is actually using.
                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        text: "0123456789  km/h  Drive info"
                        color: root.valueColor
                        font.family: Theme.fontFamily
                        font.pixelSize: 20
                        elide: Text.ElideRight
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Action {
                    Layout.fillWidth: true
                    text: qsTr("Load font…")
                    onClicked: fontDialog.open()
                }
                Action {
                    Layout.fillWidth: true
                    text: qsTr("Use bundled")
                    enabled: Fonts.isCustom
                    opacity: enabled ? 1 : 0.45
                    onClicked: Fonts.useBundled()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                TextField {
                    id: fontPath
                    Layout.fillWidth: true
                    placeholderText: qsTr("…or type a font file or folder path")
                    color: root.valueColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 12
                    background: Rectangle {
                        radius: 6
                        color: "#232B33"
                        border.width: 1
                        border.color: fontPath.activeFocus ? root.accentColor : root.panelLine
                    }
                    onAccepted: Fonts.loadPath(text)
                }
                Action {
                    text: qsTr("Apply")
                    Layout.preferredWidth: 70
                    onClicked: Fonts.loadPath(fontPath.text)
                }
            }

            Text {
                Layout.fillWidth: true
                visible: Fonts.status !== ""
                text: Fonts.status
                color: Fonts.status.indexOf("Could not") === 0
                       || Fonts.status.indexOf("Not found") === 0
                       || Fonts.status.indexOf("No font") === 0 ? "#F5A623" : root.labelColor
                font.family: Theme.uiFontFamily
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Select a family's regular, italic and bold files together — the "
                           + "cluster uses italic numerals and a demi-bold range. The choice "
                           + "is remembered next time. The panel keeps its own font so it "
                           + "stays readable.")
                color: root.labelColor
                font.family: Theme.uiFontFamily
                font.pixelSize: 10
                wrapMode: Text.Wrap
                opacity: 0.75
            }

            // ------------------------------------------------------ ignition
            SectionBox { title: qsTr("Ignition & mode") }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Action {
                    Layout.fillWidth: true
                    text: root.vehicle && root.vehicle.engineRunning ? qsTr("Stop engine") : qsTr("Start engine")
                    onClicked: if (root.vehicle) root.vehicle.startStopEngine()
                }
                Chip {
                    text: qsTr("Ign. on")
                    on: root.vehicle ? root.vehicle.ignition > 0 : false
                    onClicked: if (root.vehicle) root.vehicle.ignition = !on ? 2 : 0
                }
                Chip {
                    text: qsTr("Bezel")
                    on: root.vehicle ? root.vehicle.showBezel : true
                    onClicked: if (root.vehicle) root.vehicle.showBezel = !on
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: qsTr("Input")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.preferredWidth: 92
                }
                Repeater {
                    model: [{ id: "sim", label: qsTr("Simulate") }, { id: "manual", label: qsTr("Manual") }]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        on: root.vehicle ? root.vehicle.simulationMode === modelData.id : false
                        onClicked: if (root.vehicle) root.vehicle.simulationMode = modelData.id
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: qsTr("Drive mode")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.preferredWidth: 92
                }
                Repeater {
                    model: ["Comfort", "Eco", "Sport", "Smart"]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData
                        on: root.vehicle ? root.vehicle.driveMode === modelData : false
                        onClicked: if (root.vehicle) root.vehicle.driveMode = modelData
                    }
                }
            }

            // ------------------------------------------------------- driving
            SectionBox { title: qsTr("Driving") }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: qsTr("Gear")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.preferredWidth: 92
                }
                Repeater {
                    model: ["P", "R", "N", "D"]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData
                        on: root.vehicle ? root.vehicle.gearMode === modelData : false
                        onClicked: if (root.vehicle) root.vehicle.setGear(modelData)
                    }
                }
            }

            Slider2 {
                label: qsTr("Throttle")
                value: root.vehicle ? root.vehicle.throttle : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.throttle = v }
            }

            Slider2 {
                label: qsTr("Brake")
                value: root.vehicle ? root.vehicle.brake : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.brake = v }
            }

            Slider2 {
                label: qsTr("Speed")
                from: 0
                to: 220
                decimals: 0
                suffix: " km/h"
                enabled: root.vehicle ? root.vehicle.simulationMode === "manual" : false
                opacity: enabled ? 1 : 0.4
                value: root.vehicle ? root.vehicle.speed : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.speed = v }
            }

            Slider2 {
                label: qsTr("Engine rpm")
                from: 0
                to: 8000
                decimals: 0
                enabled: root.vehicle ? root.vehicle.simulationMode === "manual" : false
                opacity: enabled ? 1 : 0.4
                value: root.vehicle ? root.vehicle.rpm : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.rpm = v }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Park brake")
                    on: root.vehicle ? root.vehicle.parkBrake : false
                    onClicked: if (root.vehicle) root.vehicle.parkBrake = !on
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Cruise")
                    on: root.vehicle ? root.vehicle.cruiseEnabled : false
                    onClicked: {
                        if (!root.vehicle)
                            return
                        var want = !on
                        root.vehicle.cruiseEnabled = want
                        if (want && root.vehicle.cruiseSetSpeed === 0)
                            root.vehicle.cruiseSetSpeed = Math.max(40, Math.round(root.vehicle.speed))
                        if (!want)
                            root.vehicle.cruiseActive = false
                    }
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Set")
                    enabled: root.vehicle ? root.vehicle.cruiseEnabled : false
                    on: root.vehicle ? root.vehicle.cruiseActive : false
                    onClicked: {
                        if (!root.vehicle)
                            return
                        root.vehicle.cruiseSetSpeed = Math.max(30, Math.round(root.vehicle.speed))
                        root.vehicle.cruiseActive = !on
                    }
                }
            }

            // --------------------------------------------------------- fluids
            SectionBox { title: qsTr("Fluids & climate") }

            Slider2 {
                label: qsTr("Fuel level")
                decimals: 2
                value: root.vehicle ? root.vehicle.fuelLevel : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.fuelLevel = v }
            }

            Slider2 {
                label: qsTr("Coolant")
                from: 10
                to: 130
                decimals: 0
                suffix: " °C"
                value: root.vehicle ? root.vehicle.coolantTemp : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.coolantTemp = v }
            }

            Slider2 {
                label: qsTr("Outside")
                from: -30
                to: 55
                decimals: 0
                suffix: " °C"
                value: root.vehicle ? root.vehicle.outsideTemp : 0
                onMoved: function (v) { if (root.vehicle) root.vehicle.outsideTemp = v }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Action {
                    Layout.fillWidth: true
                    text: qsTr("Refuel")
                    onClicked: if (root.vehicle) root.vehicle.refuel()
                }
                Action {
                    Layout.fillWidth: true
                    text: qsTr("Reset trip")
                    onClicked: if (root.vehicle) root.vehicle.resetTrip()
                }
                Chip {
                    Layout.fillWidth: true
                    text: root.vehicle && root.vehicle.units === "imperial" ? qsTr("mph / mi") : qsTr("km/h / km")
                    on: root.vehicle ? root.vehicle.units === "imperial" : false
                    onClicked: if (root.vehicle) root.vehicle.units = !on ? "imperial" : "metric"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: qsTr("Economy")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.preferredWidth: 92
                }
                Repeater {
                    model: ["km/L", "L/100km", "mpg"]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData
                        on: root.vehicle ? root.vehicle.consumptionUnits === modelData : false
                        onClicked: if (root.vehicle) root.vehicle.consumptionUnits = modelData
                    }
                }
            }

            // -------------------------------------------------------- lights
            SectionBox { title: qsTr("Lighting") }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: [
                        { label: qsTr("Off"), mode: 0 },
                        { label: qsTr("Position"), mode: 1 },
                        { label: qsTr("Low beam"), mode: 2 },
                        { label: qsTr("Auto"), mode: 3 }
                    ]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        on: root.vehicle ? root.vehicle.headlightMode === modelData.mode : false
                        onClicked: if (root.vehicle) root.vehicle.headlightMode = modelData.mode
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 6
                rowSpacing: 6

                Chip {
                    Layout.fillWidth: true
                    text: qsTr("High beam")
                    on: root.vehicle ? root.vehicle.highBeam : false
                    onClicked: if (root.vehicle) root.vehicle.highBeam = !on
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Front fog")
                    on: root.vehicle ? root.vehicle.frontFog : false
                    onClicked: if (root.vehicle) root.vehicle.frontFog = !on
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Rear fog")
                    on: root.vehicle ? root.vehicle.rearFog : false
                    onClicked: if (root.vehicle) root.vehicle.rearFog = !on
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Left ◀")
                    on: root.vehicle ? root.vehicle.turnLeft : false
                    onClicked: {
                        if (!root.vehicle)
                            return
                        root.vehicle.turnLeft = !on
                        if (!on)
                            root.vehicle.turnRight = false
                    }
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Hazard")
                    on: root.vehicle ? root.vehicle.hazard : false
                    onClicked: if (root.vehicle) root.vehicle.hazard = !on
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("▶ Right")
                    on: root.vehicle ? root.vehicle.turnRight : false
                    onClicked: {
                        if (!root.vehicle)
                            return
                        root.vehicle.turnRight = !on
                        if (!on)
                            root.vehicle.turnLeft = false
                    }
                }
            }

            // ---------------------------------------------------------- body
            SectionBox { title: qsTr("Doors & belts") }

            GridLayout {
                Layout.fillWidth: true
                columns: 4
                columnSpacing: 6
                rowSpacing: 6

                Repeater {
                    model: [
                        { label: qsTr("Door FL"), prop: "doorFL" },
                        { label: qsTr("Door FR"), prop: "doorFR" },
                        { label: qsTr("Door RL"), prop: "doorRL" },
                        { label: qsTr("Door RR"), prop: "doorRR" },
                        { label: qsTr("Trunk"), prop: "trunk" },
                        { label: qsTr("Hood"), prop: "hood" }
                    ]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        on: root.vehicle ? root.vehicle[modelData.prop] : false
                        onClicked: if (root.vehicle) root.vehicle[modelData.prop] = !on
                    }
                }

                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Belt D")
                    on: root.vehicle ? !root.vehicle.beltDriver : false
                    onClicked: if (root.vehicle) root.vehicle.beltDriver = !root.vehicle.beltDriver
                }
                Chip {
                    Layout.fillWidth: true
                    text: qsTr("Belt P")
                    on: root.vehicle ? !root.vehicle.beltPassenger : false
                    onClicked: if (root.vehicle) root.vehicle.beltPassenger = !root.vehicle.beltPassenger
                }
            }

            // ----------------------------------------------------- telltales
            SectionBox { title: qsTr("Warning lamps") }

            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 6
                rowSpacing: 6

                Repeater {
                    model: [
                        { label: qsTr("Brake"), prop: "brakeSystem" },
                        { label: qsTr("Oil press."), prop: "oilPressure" },
                        { label: qsTr("Battery"), prop: "batteryCharge" },
                        { label: qsTr("Airbag"), prop: "airbagFault" },
                        { label: qsTr("Check eng."), prop: "checkEngine" },
                        { label: qsTr("ABS"), prop: "absFault" },
                        { label: qsTr("ESC off"), prop: "escOff" },
                        { label: qsTr("Traction"), prop: "tractionOff" },
                        { label: qsTr("EPS"), prop: "epsFault" },
                        { label: qsTr("TPMS"), prop: "tpms" },
                        { label: qsTr("Washer"), prop: "washerFluid" },
                        { label: qsTr("Glow plug"), prop: "glowPlug" },
                        { label: qsTr("Immobiliser"), prop: "immobilizer" },
                        { label: qsTr("Fwd. collision"), prop: "fcaWarn" },
                        { label: qsTr("Lane assist"), prop: "ldwEnabled" }
                    ]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        on: root.vehicle ? root.vehicle[modelData.prop] : false
                        onClicked: if (root.vehicle) root.vehicle[modelData.prop] = !on
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: qsTr("Lane drift")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.preferredWidth: 92
                }
                Repeater {
                    model: [{ label: qsTr("None"), v: "none" },
                            { label: qsTr("Left"), v: "left" },
                            { label: qsTr("Right"), v: "right" }]
                    delegate: Chip {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        on: root.vehicle ? root.vehicle.laneDeparture === modelData.v : false
                        onClicked: if (root.vehicle) root.vehicle.laneDeparture = modelData.v
                    }
                }
            }

            Action {
                Layout.fillWidth: true
                Layout.bottomMargin: 12
                text: qsTr("Clear all warning lamps")
                onClicked: {
                    if (!root.vehicle)
                        return
                    var props = ["brakeSystem", "oilPressure", "batteryCharge", "airbagFault",
                                 "checkEngine", "absFault", "escOff", "tractionOff", "epsFault",
                                 "tpms", "washerFluid", "glowPlug", "immobilizer", "fcaWarn"]
                    for (var i = 0; i < props.length; ++i)
                        root.vehicle[props[i]] = false
                    root.vehicle.laneDeparture = "none"
                    root.vehicle.message = ""
                }
            }
        }
    }
}
