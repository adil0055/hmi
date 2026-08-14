import QtQuick
import Hmi

/*!
    Dial needle.

    Drawn from \l innerRadius outward so its tail passes behind the inner disc,
    which is how it reads on the reference cluster.  Built from rounded
    rectangles rather than a path so it stays sharp at any render scale.
*/
Item {
    id: root

    property real centreX: 0
    property real centreY: 0
    property real angle: Theme.startAngle
    property real innerRadius: 100
    property real outerRadius: 228
    property color needleColor: Theme.textPrimary
    property color glowColor: Theme.accentBright
    /*! Needles are damped, like a real stepper-driven pointer. */
    property bool animated: true

    x: centreX
    y: centreY
    width: 0
    height: 0
    rotation: -angle

    Behavior on rotation {
        enabled: root.animated
        SmoothedAnimation { velocity: 620; duration: 400 }
    }

    // Soft halo around the pointer.
    Rectangle {
        x: root.innerRadius
        y: -7
        width: root.outerRadius - root.innerRadius
        height: 14
        radius: 7
        antialiasing: true
        color: Qt.rgba(root.glowColor.r, root.glowColor.g, root.glowColor.b, 0.10)
    }

    Rectangle {
        x: root.innerRadius
        y: -3.5
        width: root.outerRadius - root.innerRadius
        height: 7
        radius: 3.5
        antialiasing: true
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.55) }
            GradientStop { position: 0.35; color: root.needleColor }
            GradientStop { position: 1.0; color: root.needleColor }
        }
    }
}
