import QtQuick
import QtQuick.Shapes
import Hmi

/*!
    The complete cluster, laid out on Theme's fixed design canvas.

    Nothing in here reads the window size: the parent scales this item as a
    whole, so the artwork keeps its proportions at any resolution.
*/
Item {
    id: root

    property var vehicle: null

    width: Theme.designW
    height: Theme.designH

    readonly property bool awake: vehicle ? vehicle.ignition > 0 : true
    readonly property color accent: vehicle ? Theme.modeAccent(vehicle.driveMode) : Theme.accent

    // Coolant gauge spans a narrower band than the raw temperature range.
    readonly property real coolantLevel:
        vehicle ? Math.max(0, Math.min(1, (vehicle.coolantTemp - 50) / 80)) : 0

    Bezel { visible: vehicle ? vehicle.showBezel : true }

    // The lit display, clipped to the glass so nothing bleeds onto the hood.
    Item {
        id: glass
        x: Theme.glassRect.x
        y: Theme.glassRect.y
        width: Theme.glassRect.width
        height: Theme.glassRect.height
        clip: true
        opacity: root.awake ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 320 } }

        // Undo the clip offset so children keep using design-canvas coordinates.
        Item {
            id: display
            x: -glass.x
            y: -glass.y
            width: Theme.designW
            height: Theme.designH

        // ------------------------------------------------------- left dial
        Dial {
            centreX: Theme.dialCxLeft
            minValue: 0
            maxValue: Theme.speedMax
            majorStep: 20
            minorStep: 5
            highlightCentre: 132
            accent: root.accent
            value: root.vehicle ? Fmt.speedValue(root.vehicle.speed, "metric") : 0
            valueText: root.vehicle ? String(Fmt.speedValue(root.vehicle.speed, root.vehicle.units)) : "0"
            unitText: root.vehicle ? Fmt.speedUnit(root.vehicle.units) : "km/h"
            valueSize: Theme.valueSize
        }

        MiniArcGauge {
            centreX: Theme.dialCxLeft
            centreY: Theme.dialCy
            level: root.vehicle ? root.vehicle.fuelLevel : 0
            fillColor: Theme.fuelFill
            alarm: root.vehicle ? root.vehicle.lowFuel : false
            leftLabel: "E"
            rightLabel: "F"
            iconSource: Theme.icon("fuel_pump")
        }

        // ------------------------------------------------------ right dial
        Dial {
            centreX: Theme.dialCxRight
            minValue: 0
            maxValue: Theme.rpmMax
            majorStep: 1
            minorStep: 0.2
            redlineFrom: Theme.redlineFrom
            highlightCentre: 48
            accent: root.accent
            value: root.vehicle ? root.vehicle.rpm / 1000 : 0
            valueText: root.vehicle ? Fmt.rpmValue(root.vehicle.rpm) : "0.0"
            unitText: qsTr("x1000rpm")
            valueSize: Theme.rpmValueSize
        }

        MiniArcGauge {
            centreX: Theme.dialCxRight
            centreY: Theme.dialCy
            level: root.coolantLevel
            fillColor: Theme.textSecondary
            zoneFrom: 0.85
            zoneTo: 1.0
            zoneColor: Theme.danger
            alarm: root.vehicle ? root.vehicle.engineTempWarn : false
            leftLabel: "C"
            rightLabel: "H"
            iconSource: Theme.icon("coolant")
        }

        // ----------------------------------------------------- centre stack
        LaneGraphic {
            leftDetected: root.vehicle ? root.vehicle.laneLeftDetected : true
            rightDetected: root.vehicle ? root.vehicle.laneRightDetected : true
            departure: root.vehicle ? root.vehicle.laneDeparture : "none"
            blink: root.vehicle ? root.vehicle.blinkOn : false
        }

        BottomBar {
            tempValue: root.vehicle ? String(Fmt.tempValue(root.vehicle.outsideTemp, root.vehicle.units)) : "28"
            tempUnit: root.vehicle ? Fmt.tempUnit(root.vehicle.units) : "°C"
            odoValue: root.vehicle ? Fmt.distanceValue(root.vehicle.odometer, root.vehicle.units, 0) : "25"
            odoUnit: root.vehicle ? Fmt.distanceUnit(root.vehicle.units) : "km"
        }

        CenterPanel {
            accent: root.accent
            gear: root.vehicle ? root.vehicle.gearMode : "P"
            gearNumber: root.vehicle ? root.vehicle.gearNumber : 0
            showGearNumber: root.vehicle ? (root.vehicle.driveMode === "Sport"
                                            && root.vehicle.gearMode === "D") : false
            rangeValue: root.vehicle ? String(Math.round(
                            Fmt.isImperial(root.vehicle.units) ? root.vehicle.rangeKm * Fmt.kmToMi
                                                               : root.vehicle.rangeKm)) : "550"
            rangeUnit: root.vehicle ? Fmt.distanceUnit(root.vehicle.units) : "km"
            tripValue: root.vehicle ? Fmt.distanceValue(root.vehicle.tripDistance, root.vehicle.units, 1) : "0.0"
            tripUnit: root.vehicle ? Fmt.distanceUnit(root.vehicle.units) : "km"
            timerValue: root.vehicle ? Fmt.duration(root.vehicle.tripSeconds) : "0:00"
            timerUnit: qsTr("h:m")
            avgValue: root.vehicle ? Fmt.consumptionValue(root.vehicle.avgConsumption,
                                                          root.vehicle.consumptionUnits) : "--.-"
            avgUnit: root.vehicle ? Fmt.consumptionUnit(root.vehicle.consumptionUnits,
                                                        root.vehicle.units) : "km/L"
            ecoValue: root.vehicle ? root.vehicle.instantConsumption : 0
            message: root.vehicle ? root.vehicle.message : ""
        }

        TelltaleBar {
            vehicle: root.vehicle
        }

        // Cruise set speed, in the free left half of the bottom panel.
        Row {
            visible: root.vehicle ? root.vehicle.cruiseEnabled : false
            spacing: 8
            x: Theme.cruiseX
            y: Theme.cruiseY - height / 2

            Text {
                text: root.vehicle ? String(root.vehicle.cruiseSetSpeed) : "0"
                color: root.vehicle && root.vehicle.cruiseActive ? "#4CD964" : Theme.textDim
                font.family: Theme.fontFamily
                font.pixelSize: 40
            }
            Text {
                text: root.vehicle ? Fmt.speedUnit(root.vehicle.units) : "km/h"
                color: Theme.textDim
                font.family: Theme.fontFamily
                font.pixelSize: 19
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 7
            }
        }

        // Shift-up prompt near the redline.
        Text {
            visible: root.vehicle ? root.vehicle.sportShiftLights : false
            text: "▲"
            color: Theme.danger
            font.pixelSize: 34
            x: Theme.dialCxRight - width / 2
            y: Theme.dialCy - 160
            SequentialAnimation on opacity {
                running: parent.visible
                loops: Animation.Infinite
                NumberAnimation { to: 0.15; duration: 200 }
                NumberAnimation { to: 1.0; duration: 200 }
            }
        }
        }
    }

    // Corner vignette, so the glass reads as glass.
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: Theme.centreX
                centerY: Theme.dialCy
                centerRadius: Theme.designW * 0.62
                focalX: Theme.centreX
                focalY: Theme.dialCy
                GradientStop { position: 0.55; color: Qt.rgba(0, 0, 0, 0) }
                GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.55) }
            }
            startX: Theme.glassRect.x; startY: Theme.glassRect.y
            PathLine { x: Theme.glassRect.x + Theme.glassRect.width; y: Theme.glassRect.y }
            PathLine { x: Theme.glassRect.x + Theme.glassRect.width
                       y: Theme.glassRect.y + Theme.glassRect.height }
            PathLine { x: Theme.glassRect.x; y: Theme.glassRect.y + Theme.glassRect.height }
            PathLine { x: Theme.glassRect.x; y: Theme.glassRect.y }
        }
    }
}
