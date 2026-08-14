import QtQuick
import QtQuick.Shapes
import Hmi

/*!
    The perspective road drawn below the drive-info block.

    Each lane line brightens when the corresponding marking is detected and
    turns amber while the car is drifting across it, which is what the lane
    departure warning does on the real cluster.
*/
Item {
    id: root

    property bool leftDetected: true
    property bool rightDetected: true
    /*! "none", "left" or "right". */
    property string departure: "none"
    property bool blink: false

    anchors.fill: parent

    readonly property real apexY: Theme.laneApexY
    readonly property real baseY: Theme.laneBaseY
    readonly property real cx: Theme.centreX
    readonly property real ah: Theme.laneApexHalf
    readonly property real bh: Theme.laneBaseHalf

    function lineColor(side) {
        if (departure === side)
            return blink ? Qt.rgba(0.96, 0.65, 0.14, 1.0) : Qt.rgba(0.96, 0.65, 0.14, 0.3)
        var seen = side === "left" ? leftDetected : rightDetected
        return seen ? Qt.rgba(0.66, 0.82, 0.95, 0.52) : Qt.rgba(0.66, 0.82, 0.95, 0.14)
    }

    // Road surface between the markings.
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 0; y1: root.apexY; x2: 0; y2: root.baseY
                GradientStop { position: 0.0; color: Qt.rgba(0.36, 0.60, 0.85, 0.0) }
                GradientStop { position: 1.0; color: Qt.rgba(0.36, 0.60, 0.85, 0.05) }
            }
            startX: root.cx - root.ah; startY: root.apexY
            PathLine { x: root.cx + root.ah; y: root.apexY }
            PathLine { x: root.cx + root.bh; y: root.baseY }
            PathLine { x: root.cx - root.bh; y: root.baseY }
            PathLine { x: root.cx - root.ah; y: root.apexY }
        }
    }

    // Lane markings, tapered so they read as perspective.
    Repeater {
        model: ["left", "right"]

        delegate: Shape {
            id: marking
            required property var modelData

            readonly property real dir: modelData === "left" ? -1 : 1
            readonly property color tint: root.lineColor(modelData)

            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
                strokeColor: "transparent"
                fillGradient: LinearGradient {
                    x1: 0; y1: root.apexY; x2: 0; y2: root.baseY
                    GradientStop { position: 0.0; color: Qt.rgba(marking.tint.r, marking.tint.g,
                                                                 marking.tint.b, 0.0) }
                    GradientStop { position: 0.4; color: Qt.rgba(marking.tint.r, marking.tint.g,
                                                                 marking.tint.b, marking.tint.a * 0.35) }
                    GradientStop { position: 1.0; color: marking.tint }
                }
                startX: root.cx + marking.dir * root.ah
                startY: root.apexY
                PathLine { x: root.cx + marking.dir * (root.ah + 2.0); y: root.apexY }
                PathLine { x: root.cx + marking.dir * (root.bh + 7); y: root.baseY }
                PathLine { x: root.cx + marking.dir * root.bh; y: root.baseY }
                PathLine { x: root.cx + marking.dir * root.ah; y: root.apexY }
            }
        }
    }
}
