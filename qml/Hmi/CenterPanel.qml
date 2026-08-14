import QtQuick
import Hmi

/*! Gear, range, and the Drive info block between the two dials. */
Item {
    id: root

    property string gear: "P"
    property int gearNumber: 0
    property bool showGearNumber: false
    property string rangeValue: "550"
    property string rangeUnit: "km"

    property string tripValue: "0.0"
    property string tripUnit: "km"
    property string timerValue: "0:00"
    property string timerUnit: "h:m"
    property string avgValue: "--.-"
    property string avgUnit: "km/L"

    property real ecoValue: 0
    property color accent: Theme.accent
    property string message: ""

    anchors.fill: parent

    // ------------------------------------------------------------ gear
    Row {
        spacing: 4
        x: Theme.gearX - width / 2
        y: Theme.topRowY - height / 2

        Text {
            text: root.gear
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.gearSize
            renderType: Text.QtRendering
        }

        Text {
            visible: root.showGearNumber && root.gearNumber > 0
            text: root.gearNumber
            color: root.accent
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(Theme.gearSize * 0.55)
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Theme.gearSize * 0.12
        }
    }

    // ----------------------------------------------------------- range
    Image {
        id: rangeIcon
        source: Theme.icon("fuel_pump_white")
        width: 30
        height: 34
        sourceSize: Qt.size(96, 96)
        smooth: true
        x: Theme.rangeIconX
        y: Theme.topRowY - height / 2
    }

    Text {
        id: rangeText
        text: root.rangeValue
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.rangeSize
        font.weight: Font.DemiBold
        renderType: Text.QtRendering
        x: rangeIcon.x + rangeIcon.width + 12
        y: Theme.topRowY - height / 2
    }

    Text {
        text: root.rangeUnit
        color: Theme.textDim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.rangeUnitSize
        x: rangeText.x + rangeText.width + 5
        y: rangeText.y + rangeText.height - height - Theme.rangeSize * 0.16
    }

    // ------------------------------------------------------- drive info
    Text {
        text: qsTr("Drive info")
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.driveInfoSize
        renderType: Text.QtRendering
        x: Theme.centreX - width / 2
        y: Theme.driveInfoY - height / 2
    }

    Repeater {
        model: [
            { label: qsTr("Trip"), value: root.tripValue, unit: root.tripUnit, row: 0 },
            { label: qsTr("Timer"), value: root.timerValue, unit: root.timerUnit, row: 1 },
            { label: qsTr("Avg."), value: root.avgValue, unit: root.avgUnit, row: 2 }
        ]
        delegate: Item {
            required property var modelData
            readonly property real cy: Theme.infoRowY[modelData.row]

            Text {
                text: modelData.label
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.infoLabelSize
                x: Theme.infoLabelX
                y: parent.cy - height / 2
            }

            Text {
                id: value
                text: modelData.value
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.infoValueSize
                renderType: Text.QtRendering
                x: Theme.infoValueRight - width
                y: parent.cy - height / 2
            }

            Text {
                text: modelData.unit
                color: Theme.textDim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.infoUnitSize
                x: Theme.infoUnitX
                // Align with the value's baseline.
                y: value.y + value.height - height - Theme.infoValueSize * 0.14
            }
        }
    }

    EcoBar {
        value: root.ecoValue
        accent: root.accent
    }

    // Transient driver message.
    Text {
        visible: root.message !== ""
        text: root.message
        color: "#F5A623"
        font.family: Theme.fontFamily
        font.pixelSize: 22
        x: Theme.centreX - width / 2
        y: 615
    }
}
