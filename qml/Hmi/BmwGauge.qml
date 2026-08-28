import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import Hmi

/*!
    One chevron gauge: the dark band, the lit part of it, a scale down its
    outer side and a caption.

    The band is a polygon rather than a stroked path because the lit part has
    to be the *same shape* truncated partway up, and because a fill gradient
    running the height of the band is what gives it the metallic look.  Both
    come free from BmwTheme.chevron().
*/
Item {
    id: root

    property bool mirrored: false          // true puts the point on the left
    property real minValue: 0
    property real maxValue: 220
    property real value: 0
    property real majorStep: 30
    property real minorStep: 10
    property string caption: "km/h"
    property color accent: "#D9A05B"
    /*! Scales the whole gauge in and out for the wake-up sweep. */
    property real reveal: 1

    readonly property real outerX: mirrored ? BmwTheme.rightOuterX : BmwTheme.leftOuterX
    readonly property real apexX: mirrored ? BmwTheme.rightApexX : BmwTheme.leftApexX
    readonly property real midY: BmwTheme.gaugeMidY
    readonly property real halfH: BmwTheme.gaugeHalfH
    readonly property real dir: mirrored ? -1 : 1

    /*! 0..1 up the scale; everything below is driven from this.

        Writable only so a Behavior can attach to it — treat it as derived. */
    property real level: {
        var span = maxValue - minValue
        return span > 0 ? Math.max(0, Math.min(1, (value - minValue) / span)) : 0
    }
    // The band chases the value rather than snapping to it — a real gauge has
    // mass, and without this the fill flickers on every simulator tick.
    Behavior on level { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

    readonly property real levelY: midY + halfH - 2 * halfH * level

    anchors.fill: parent

    function _scaleY(v) {
        var span = maxValue - minValue
        var t = span > 0 ? (v - minValue) / span : 0
        return midY + halfH - 2 * halfH * Math.max(0, Math.min(1, t))
    }

    /*! x of the band's outer edge at height \a y, following the two arms. */
    function _edgeX(y) {
        return outerX + (apexX - outerX) * (1 - Math.abs(y - midY) / halfH)
    }

    // ------------------------------------------------------------- the track
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        opacity: root.reveal

        ShapePath {
            strokeColor: Qt.rgba(1, 1, 1, 0.10)
            strokeWidth: 1
            // Light falls from above, so the band is brightest along its top
            // arm and sinks to nothing at the bottom — the same trick that
            // makes a rendered bevel read as metal rather than as paint.
            fillGradient: LinearGradient {
                x1: 0; y1: root.midY - root.halfH
                x2: 0; y2: root.midY + root.halfH
                GradientStop { position: 0.0; color: BmwTheme.trackTop }
                GradientStop { position: 0.30; color: BmwTheme.trackMid }
                GradientStop { position: 0.62; color: BmwTheme.trackBottom }
                GradientStop { position: 1.0; color: "#05070A" }
            }
            PathPolyline {
                path: BmwTheme.chevron(root.outerX, root.apexX, root.midY,
                                       root.halfH, BmwTheme.gaugeThickness, 1)
            }
        }

        // A bright hairline down the outer edge only, which is what separates
        // the band from the black behind it at the bottom of the sweep.
        ShapePath {
            strokeColor: BmwTheme.trackEdge
            strokeWidth: 1.4
            fillColor: "transparent"
            capStyle: ShapePath.FlatCap
            startX: root.outerX; startY: root.midY - root.halfH
            PathLine { x: root.apexX; y: root.midY }
            PathLine { x: root.outerX; y: root.midY + root.halfH }
        }
    }

    // --------------------------------------------------------- the lit part
    // Hidden; it exists to be blurred by the MultiEffect below.
    Item {
        id: bloomSource
        anchors.fill: parent
        visible: false
        layer.enabled: true
        layer.smooth: true

        BmwChevron {
            anchors.fill: parent
            outerX: root.outerX; apexX: root.apexX
            midY: root.midY; halfH: root.halfH
            thickness: BmwTheme.gaugeThickness
            level: root.level
            accent: root.accent
        }
    }

    // Bloom.  A backlit panel this bright spills into the black around it, and
    // without that the gauge looks printed rather than emissive.
    MultiEffect {
        source: bloomSource
        anchors.fill: parent
        blurEnabled: true
        blur: 1.0
        blurMax: 56
        blurMultiplier: 1.6
        opacity: 0.7 * root.reveal
    }

    // The crisp band, over its own glow.
    BmwChevron {
        anchors.fill: parent
        opacity: root.reveal
        outerX: root.outerX; apexX: root.apexX
        midY: root.midY; halfH: root.halfH
        thickness: BmwTheme.gaugeThickness
        level: root.level
        accent: root.accent
    }

    // Bright cap on the leading edge, with a soft bloom above it.  The band
    // keeps a constant horizontal thickness, so the cap is just that wide,
    // hung off whichever edge is the outer one.
    Item {
        id: cap
        readonly property real edge: root._edgeX(root.levelY)
        visible: root.level > 0.004 && root.reveal > 0.02
        x: root.dir > 0 ? edge - BmwTheme.gaugeThickness : edge
        y: root.levelY
        width: BmwTheme.gaugeThickness
        height: 0

        Rectangle {
            y: -1.5
            width: parent.width
            height: 3
            color: Qt.lighter(root.accent, 1.8)
            opacity: 0.95 * root.reveal
        }

        Rectangle {
            y: -26
            width: parent.width
            height: 26
            opacity: 0.5 * root.reveal
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: Qt.rgba(root.accent.r, root.accent.g,
                                                             root.accent.b, 0.7) }
            }
        }
    }

    // ----------------------------------------------------------------- scale
    Repeater {
        model: Math.round((root.maxValue - root.minValue) / root.minorStep) + 1
        delegate: Rectangle {
            required property int index
            readonly property real v: root.minValue + index * root.minorStep
            readonly property bool major:
                Math.abs(v / root.majorStep - Math.round(v / root.majorStep)) < 1e-6
            readonly property real len: major ? BmwTheme.majorTickLen : BmwTheme.minorTickLen

            width: len
            height: major ? 2.5 : 1.5
            // Ticks sit outboard of the band's widest point, in a straight
            // column, so the scale still reads as a scale next to a shape that
            // is anything but straight.
            x: root.dir > 0 ? root.outerX - BmwTheme.tickGap - len
                            : root.outerX + BmwTheme.tickGap
            y: root._scaleY(v) - height / 2
            antialiasing: true
            opacity: root.reveal
            // Passed values light up; the rest stay as faint furniture.
            color: v <= root.value + 1e-6 ? BmwTheme.scaleTickLit : BmwTheme.scaleTick
            Behavior on color { ColorAnimation { duration: 180 } }
        }
    }

    Repeater {
        model: Math.round((root.maxValue - root.minValue) / root.majorStep) + 1
        delegate: ClusterText {
            required property int index
            readonly property real v: root.minValue + index * root.majorStep

            text: String(Math.round(v))
            designSize: BmwTheme.scaleLabelSize
            color: v <= root.value + 1e-6 ? BmwTheme.textSecondary : BmwTheme.textDim
            opacity: root.reveal
            x: root.dir > 0
               ? root.outerX - BmwTheme.tickGap - BmwTheme.majorTickLen - 12 - width
               : root.outerX + BmwTheme.tickGap + BmwTheme.majorTickLen + 12
            y: root._scaleY(v) - height / 2 + Theme.capDy(BmwTheme.scaleLabelSize)
            Behavior on color { ColorAnimation { duration: 180 } }
        }
    }

    // Caption, just above the top of the scale.
    ClusterText {
        text: root.caption
        designSize: BmwTheme.gaugeLabelSize
        color: BmwTheme.textDim
        opacity: root.reveal
        x: root.dir > 0 ? root.outerX - BmwTheme.tickGap - width
                        : root.outerX + BmwTheme.tickGap
        y: root.midY - root.halfH - 34 + Theme.capDy(BmwTheme.gaugeLabelSize)
    }
}
