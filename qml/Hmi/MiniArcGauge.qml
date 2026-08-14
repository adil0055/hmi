import QtQuick
import Hmi

/*!
    The small segmented arc across the bottom of each dial: fuel under the
    speedometer, coolant under the tachometer.

    The bar is a plain arc with separator notches punched through it in the
    background colour, which gives the segmented look without needing one
    Shape per segment.
*/
Item {
    id: root

    property real centreX: 0
    property real centreY: 0
    /*! Current reading, 0..1, filling from the left end of the arc. */
    property real level: 0
    property color fillColor: Theme.fuelFill
    /*! Permanently marked band (fuel reserve, coolant overheat); < 0 hides it. */
    property real zoneFrom: -1
    property real zoneTo: 1
    property color zoneColor: Theme.danger

    property string leftLabel: "E"
    property string rightLabel: "F"
    property url iconSource: ""
    /*! Pulses the fill when the reading is in the warning band. */
    property bool alarm: false

    readonly property real _span: Theme.arcTo - Theme.arcFrom
    function _angle(t) { return Theme.arcFrom + _span * Math.max(0, Math.min(1, t)) }

    anchors.fill: parent

    // Unlit track.
    Arc {
        centreX: root.centreX
        centreY: root.centreY
        radius: Theme.arcRadius
        thickness: Theme.arcThickness
        from: Theme.arcFrom
        to: Theme.arcTo
        stroke: Theme.tickDim
    }

    // Live reading.
    Arc {
        id: fill
        visible: root.level > 0.001
        centreX: root.centreX
        centreY: root.centreY
        radius: Theme.arcRadius
        thickness: Theme.arcThickness
        from: Theme.arcFrom
        to: root._angle(root.level)
        stroke: root.fillColor

        Behavior on to { SmoothedAnimation { velocity: 40; duration: 500 } }

        SequentialAnimation on opacity {
            running: root.alarm
            loops: Animation.Infinite
            NumberAnimation { to: 0.25; duration: 480 }
            NumberAnimation { to: 1.0; duration: 480 }
            onRunningChanged: if (!running) fill.opacity = 1
        }
    }

    // Fixed warning band, kept on top so it reads even at a full deflection.
    Arc {
        visible: root.zoneFrom >= 0
        centreX: root.centreX
        centreY: root.centreY
        radius: Theme.arcRadius
        thickness: Theme.arcThickness
        from: root._angle(root.zoneFrom)
        to: root._angle(root.zoneTo)
        stroke: root.zoneColor
    }

    // Segment notches.
    Repeater {
        model: Theme.arcSegments - 1
        delegate: Item {
            required property int index
            x: root.centreX
            y: root.centreY
            width: 0
            height: 0
            rotation: -root._angle((index + 1) / Theme.arcSegments)

            Rectangle {
                x: Theme.arcRadius - Theme.arcThickness / 2 - 1
                y: -1.6
                width: Theme.arcThickness + 2
                height: 3.2
                color: Theme.screenBg
            }
        }
    }

    // E / icon / F row.
    Text {
        text: root.leftLabel
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.miniLabelSize
        x: root.centreX - Theme.miniLabelDx - width / 2
        y: root.centreY + Theme.miniLabelDy - height / 2
    }

    Image {
        source: root.iconSource
        width: Theme.miniIconSize
        height: Theme.miniIconSize
        sourceSize: Qt.size(96, 96)
        smooth: true
        x: root.centreX - width / 2
        y: root.centreY + Theme.miniLabelDy - height / 2
    }

    Text {
        text: root.rightLabel
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.miniLabelSize
        x: root.centreX + Theme.miniLabelDx - width / 2
        y: root.centreY + Theme.miniLabelDy - height / 2
    }
}
