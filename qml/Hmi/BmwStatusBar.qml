import QtQuick
import Hmi

/*!
    The strip under the hairline: charge and clock on the left, temperature
    and range on the right, with the drive mode in the middle.
*/
Item {
    id: root

    property real batteryLevel: 0.83
    property bool charging: false
    property string clock: "11:05"
    property string driveMode: "Comfort"
    property string tempText: "+21.0"
    property string tempUnit: "°C"
    property string rangeText: "491"
    property string rangeUnit: "km"
    property color accent: "#D9A05B"

    anchors.fill: parent

    readonly property color chargeColour:
        batteryLevel < 0.12 ? BmwTheme.danger
                            : (charging ? "#3FD9A0" : BmwTheme.textSecondary)

    // Hairline the strip hangs off.
    Rectangle {
        x: BmwTheme.statusInset
        y: BmwTheme.statusRuleY
        width: BmwTheme.designW - BmwTheme.statusInset * 2
        height: 1
        color: BmwTheme.hairline
    }

    // ------------------------------------------------------- charge + clock
    Row {
        spacing: 10
        x: BmwTheme.statusInset
        y: BmwTheme.statusY - height / 2

        // Battery outline, filled to the state of charge.
        Item {
            width: 30
            height: 15
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                width: 26
                height: parent.height
                radius: 2
                color: "transparent"
                border.width: 1.4
                border.color: root.chargeColour

                Rectangle {
                    anchors.left: parent.left
                    anchors.leftMargin: 2.5
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(1, (parent.width - 5) * root.batteryLevel)
                    height: parent.height - 5
                    color: root.chargeColour
                    Behavior on width { NumberAnimation { duration: 500 } }
                }
            }

            Rectangle {   // terminal
                x: 26.5
                anchors.verticalCenter: parent.verticalCenter
                width: 3
                height: 7
                radius: 1
                color: root.chargeColour
            }

            // Pulses while charging, so the strip shows it without a label.
            SequentialAnimation on opacity {
                running: root.charging
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 700; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 700; easing.type: Easing.InOutSine }
            }
        }

        ClusterText {
            id: chargeText
            text: Math.round(root.batteryLevel * 100) + " %"
            designSize: BmwTheme.statusSize
            color: BmwTheme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }

        Item { width: 34; height: 1 }

        ClusterText {
            text: root.clock
            designSize: BmwTheme.statusSize
            color: BmwTheme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // ------------------------------------------------------------ the mode
    ClusterText {
        text: root.driveMode.toUpperCase()
        designSize: 18
        color: root.accent
        font.letterSpacing: 2.4
        x: BmwTheme.centreX - width / 2
        y: BmwTheme.statusY - height / 2 + Theme.capDy(18)
        Behavior on color { ColorAnimation { duration: 320 } }
    }

    // ------------------------------------------------------- temp and range
    Row {
        spacing: 8
        layoutDirection: Qt.RightToLeft
        x: BmwTheme.designW - BmwTheme.statusInset - width
        y: BmwTheme.statusY - height / 2

        ClusterText {
            text: root.rangeUnit
            designSize: 17
            color: BmwTheme.textDim
            anchors.baseline: rangeValue.baseline
        }

        ClusterText {
            id: rangeValue
            text: root.rangeText
            designSize: BmwTheme.statusSize
            color: BmwTheme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }

        // Range-to-empty pictogram: a road narrowing to a point.
        Canvas {
            width: 22
            height: 16
            anchors.verticalCenter: parent.verticalCenter
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = BmwTheme.textDim
                ctx.lineWidth = 1.4
                ctx.beginPath()
                ctx.moveTo(1, height - 1); ctx.lineTo(9, 1)
                ctx.moveTo(21, height - 1); ctx.lineTo(13, 1)
                ctx.stroke()
            }
        }

        Item { width: 34; height: 1 }

        ClusterText {
            text: root.tempUnit
            designSize: 17
            color: BmwTheme.textDim
            anchors.baseline: tempValue.baseline
        }

        ClusterText {
            id: tempValue
            text: root.tempText
            designSize: BmwTheme.statusSize
            color: BmwTheme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
