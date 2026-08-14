import QtQuick
import Hmi

/*!
    Tick marks and their numerals for one dial.

    Ticks are plain rotated rectangles rather than a painted path, so they stay
    perfectly crisp whatever scale the cluster is rendered at.
*/
Item {
    id: root

    property real centreX: 0
    property real centreY: 0
    property real minValue: 0
    property real maxValue: 220
    property real majorStep: 20
    property real minorStep: 5
    /*! Values at or above this are drawn in the warning colour; < 0 disables. */
    property real redlineFrom: -1
    property color majorColor: Theme.tickMajor
    property color minorColor: Theme.tickMinor
    property color warnColor: Theme.danger
    /*! Formats a major tick's numeral. */
    property var labelText: function (v) { return String(Math.round(v)) }

    readonly property int minorCount: Math.round((maxValue - minValue) / minorStep) + 1
    readonly property int majorCount: Math.round((maxValue - minValue) / majorStep) + 1

    function _isRed(v) { return redlineFrom >= 0 && v >= redlineFrom - 1e-6 }

    anchors.fill: parent

    // ---------------------------------------------------------- minor ticks
    Repeater {
        model: root.minorCount
        delegate: Item {
            required property int index
            readonly property real value: root.minValue + index * root.minorStep
            // Majors are drawn separately; skip the minors that coincide.
            readonly property bool onMajor:
                Math.abs(value / root.majorStep - Math.round(value / root.majorStep)) < 1e-6

            x: root.centreX
            y: root.centreY
            width: 0
            height: 0
            visible: !onMajor
            rotation: -Theme.angleFor(value, root.minValue, root.maxValue)

            Rectangle {
                x: Theme.tickOuter - Theme.minorLen
                y: -Theme.minorWidth / 2
                width: Theme.minorLen
                height: Theme.minorWidth
                antialiasing: true
                color: root._isRed(parent.value) ? root.warnColor : root.minorColor
            }
        }
    }

    // ---------------------------------------------------------- major ticks
    Repeater {
        model: root.majorCount
        delegate: Item {
            required property int index
            readonly property real value: root.minValue + index * root.majorStep

            x: root.centreX
            y: root.centreY
            width: 0
            height: 0
            rotation: -Theme.angleFor(value, root.minValue, root.maxValue)

            Rectangle {
                x: Theme.tickOuter - Theme.majorLen
                y: -Theme.majorWidth / 2
                width: Theme.majorLen
                height: Theme.majorWidth
                antialiasing: true
                color: root._isRed(parent.value) ? root.warnColor : root.majorColor
            }
        }
    }

    // -------------------------------------------------------------- numerals
    Repeater {
        model: root.majorCount
        delegate: Text {
            required property int index
            readonly property real value: root.minValue + index * root.majorStep
            readonly property real angle: Theme.angleFor(value, root.minValue, root.maxValue)

            text: root.labelText(value)
            // Numerals stay white even inside the red band; only the ticks and
            // the outer arc carry the warning colour.
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.labelSize
            font.weight: Font.Normal
            renderType: Text.QtRendering
            x: Theme.polarX(root.centreX, Theme.labelRadius, angle) - width / 2
            y: Theme.polarY(root.centreY, Theme.labelRadius, angle) - height / 2
        }
    }
}
