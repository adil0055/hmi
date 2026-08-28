import QtQuick
import QtQuick.Shapes
import Hmi

/*!
    The lit part of a chevron band, on its own so it can be drawn twice: once
    as a hidden source for the bloom, once crisp over the top of it.

    Two copies are needed because MultiEffect takes its source item over — an
    item feeding an effect is not also drawn in place — so a single instance
    would give either a sharp band or a blurred one, never a sharp band with
    light spilling out of it.
*/
Shape {
    id: root

    property real outerX: 0
    property real apexX: 0
    property real midY: 0
    property real halfH: 0
    property real thickness: 0
    /*! 0..1 of the band that is lit. */
    property real level: 0
    property color accent: "#D9A05B"

    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        strokeColor: "transparent"
        // Anchored to the band, not to the fill, so the colour at any given
        // height stays put as the level moves through it.
        fillGradient: LinearGradient {
            x1: 0; y1: root.midY + root.halfH
            x2: 0; y2: root.midY - root.halfH
            GradientStop { position: 0.0; color: Qt.darker(root.accent, 1.9) }
            GradientStop { position: 0.45; color: root.accent }
            GradientStop { position: 1.0; color: BmwTheme.accentLift(root.accent) }
        }
        PathPolyline {
            path: BmwTheme.chevron(root.outerX, root.apexX, root.midY,
                                   root.halfH, root.thickness, root.level)
        }
    }
}
