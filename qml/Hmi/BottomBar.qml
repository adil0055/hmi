import QtQuick
import Hmi

/*! Outside temperature over the odometer, in the rounded panel at the bottom. */
Item {
    id: root

    property string tempValue: "28"
    property string tempUnit: "°C"
    property string odoValue: "25"
    property string odoUnit: "km"

    anchors.fill: parent

    readonly property rect r: Theme.bottomBarRect

    Rectangle {
        x: root.r.x
        y: root.r.y
        width: root.r.width
        height: root.r.height
        radius: Theme.bottomBarRadius
        antialiasing: true
        border.width: 1.3
        border.color: Qt.rgba(0.34, 0.40, 0.47, 0.55)
        // Near-black, so the lane markings fade out as they run under it.
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.012, 0.022, 0.04, 0.55) }
            GradientStop { position: 0.45; color: Qt.rgba(0.008, 0.016, 0.03, 0.93) }
            GradientStop { position: 1.0; color: Qt.rgba(0.004, 0.010, 0.02, 1.0) }
        }
    }

    Repeater {
        model: [
            { value: root.tempValue, unit: root.tempUnit, row: 0 },
            { value: root.odoValue, unit: root.odoUnit, row: 1 }
        ]
        delegate: Item {
            required property var modelData
            readonly property real cy: Theme.bottomRowY[modelData.row]

            ClusterText {
                id: valueText
                text: modelData.value
                designSize: Theme.bottomValueSize
                x: unitText.x - 5 - width
                y: parent.cy - height / 2 + Theme.capDy(Theme.bottomValueSize)
            }

            ClusterText {
                id: unitText
                text: modelData.unit
                color: Theme.textDim
                designSize: Theme.bottomUnitSize
                x: Theme.bottomTextRight - width
                // Sit the unit on the value's baseline — Qt derives that from
                // the face's own metrics, so it holds for any of them.
                anchors.baseline: valueText.baseline
            }
        }
    }
}
