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
        y: Theme.topRowY - height / 2 + Theme.capDy(Theme.gearSize)

        ClusterText {
            id: gearText
            text: root.gear
            designSize: Theme.gearSize
        }

        ClusterText {
            visible: root.showGearNumber && root.gearNumber > 0
            text: root.gearNumber
            color: root.accent
            designSize: Theme.gearNumberSize
            // On the gear letter's baseline, from its metrics rather than a
            // fraction of the nominal size, which every face reads differently.
            anchors.baseline: gearText.baseline
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

    ClusterText {
        id: rangeText
        text: root.rangeValue
        designSize: Theme.rangeSize
        font.weight: Font.DemiBold
        x: rangeIcon.x + rangeIcon.width + 12
        y: Theme.topRowY - height / 2 + Theme.capDy(Theme.rangeSize)
    }

    ClusterText {
        text: root.rangeUnit
        color: Theme.textDim
        designSize: Theme.rangeUnitSize
        x: rangeText.x + rangeText.width + 5
        anchors.baseline: rangeText.baseline
    }

    // ------------------------------------------------------- drive info
    ClusterText {
        text: qsTr("Drive info")
        color: Theme.textSecondary
        designSize: Theme.driveInfoSize
        x: Theme.centreX - width / 2
        y: Theme.driveInfoY - height / 2 + Theme.capDy(Theme.driveInfoSize)
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

            ClusterText {
                text: modelData.label
                color: Theme.textSecondary
                designSize: Theme.infoLabelSize
                x: Theme.infoLabelX
                y: parent.cy - height / 2 + Theme.capDy(Theme.infoLabelSize)
            }

            ClusterText {
                id: value
                text: modelData.value
                designSize: Theme.infoValueSize
                // Right-aligned into the gap the label leaves, and shrunk
                // rather than allowed to grow back over it.
                fitWidth: Theme.infoValueRight - Theme.infoLabelX - 92
                horizontalAlignment: Text.AlignRight
                x: Theme.infoValueRight - width
                y: parent.cy - height / 2 + Theme.capDy(Theme.infoValueSize)
            }

            ClusterText {
                text: modelData.unit
                color: Theme.textDim
                designSize: Theme.infoUnitSize
                x: Theme.infoUnitX
                anchors.baseline: value.baseline
            }
        }
    }

    EcoBar {
        value: root.ecoValue
        accent: root.accent
    }

    // Transient driver message.
    ClusterText {
        visible: root.message !== ""
        text: root.message
        color: "#F5A623"
        designSize: Theme.messageSize
        x: Theme.centreX - width / 2
        y: 615
    }
}
