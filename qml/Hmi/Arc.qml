import QtQuick
import QtQuick.Shapes

/*!
    A stroked circular arc drawn in scene coordinates.

    Angles are given the way the rest of the cluster thinks about them: degrees
    counter-clockwise from 3 o'clock, so 90 is straight up and 270 straight
    down.  \l from is where the arc starts and \l to where it ends.
*/
Shape {
    id: root

    property real centreX: 0
    property real centreY: 0
    property real radius: 100
    property real from: 180
    property real to: 0
    property real thickness: 4
    property color stroke: "#ffffff"
    property bool rounded: false

    // Optional gradient along the stroke, used for the rim highlight.
    property color strokeEnd: "transparent"
    property bool gradientStroke: false

    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer
    visible: Math.abs(to - from) > 0.01 && opacity > 0

    ShapePath {
        strokeColor: root.stroke
        strokeWidth: root.thickness
        fillColor: "transparent"
        capStyle: root.rounded ? ShapePath.RoundCap : ShapePath.FlatCap
        strokeStyle: ShapePath.SolidLine

        PathAngleArc {
            centerX: root.centreX
            centerY: root.centreY
            radiusX: root.radius
            radiusY: root.radius
            // Screen angles run clockwise, scene angles run counter-clockwise.
            startAngle: -root.from
            sweepAngle: -(root.to - root.from)
        }
    }
}
