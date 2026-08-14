import QtQuick
import QtQuick.Shapes
import Hmi

/*!
    One round instrument: face, rim highlight, ticks, needle, inner disc and
    the large numeric readout at its centre.
*/
Item {
    id: root

    property real centreX: Theme.dialCxLeft
    property real centreY: Theme.dialCy

    property real minValue: 0
    property real maxValue: 220
    property real majorStep: 20
    property real minorStep: 5
    property real value: 0
    property real redlineFrom: -1
    property var labelText: function (v) { return String(Math.round(v)) }

    property string valueText: "0"
    property string unitText: "km/h"
    property int valueSize: Theme.valueSize
    property color accent: Theme.accent
    /*! Centre of the specular arc on the rim, in scene degrees. */
    property real highlightCentre: 130

    anchors.fill: parent

    // --------------------------------------------------------------- face
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.centreX
                centerY: root.centreY
                centerRadius: Theme.rimRadius
                focalX: root.centreX
                focalY: root.centreY
                GradientStop { position: 0.00; color: "#0A1420" }
                GradientStop { position: 0.52; color: "#081120" }
                GradientStop { position: 0.84; color: "#0B1725" }
                GradientStop { position: 0.97; color: "#060A11" }
                GradientStop { position: 1.00; color: "#04070C" }
            }
            PathAngleArc {
                centerX: root.centreX
                centerY: root.centreY
                radiusX: Theme.rimRadius - 1
                radiusY: Theme.rimRadius - 1
                startAngle: 0
                sweepAngle: 360
            }
        }
    }

    // Faint concentric striations, like a brushed dial face.
    Repeater {
        model: 9
        delegate: Rectangle {
            required property int index
            readonly property real r: Theme.innerRadius + 8 + index * 13
            x: root.centreX - r
            y: root.centreY - r
            width: r * 2
            height: r * 2
            radius: r
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.016)
            antialiasing: true
        }
    }

    // ---------------------------------------------------------- rim + glow
    Rectangle {
        readonly property real r: Theme.rimRadius
        x: root.centreX - r
        y: root.centreY - r
        width: r * 2
        height: r * 2
        radius: r
        color: "transparent"
        border.width: 2
        border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.16)
        antialiasing: true
    }

    Repeater {
        model: [{ span: 156, alpha: 0.20 }, { span: 114, alpha: 0.34 }, { span: 70, alpha: 0.58 }]
        delegate: Arc {
            required property var modelData
            centreX: root.centreX
            centreY: root.centreY
            radius: Theme.rimRadius
            thickness: 2.6
            rounded: true
            from: root.highlightCentre - modelData.span / 2
            to: root.highlightCentre + modelData.span / 2
            stroke: Qt.rgba(Theme.accentBright.r, Theme.accentBright.g,
                            Theme.accentBright.b, modelData.alpha)
        }
    }

    // Red band on the outer edge of the scale.
    Arc {
        visible: root.redlineFrom >= 0
        centreX: root.centreX
        centreY: root.centreY
        radius: Theme.tickOuter + 4
        thickness: 5
        from: Theme.angleFor(root.redlineFrom, root.minValue, root.maxValue)
        to: Theme.angleFor(root.maxValue, root.minValue, root.maxValue)
        stroke: Theme.danger
    }

    // --------------------------------------------------------------- scale
    TickRing {
        centreX: root.centreX
        centreY: root.centreY
        minValue: root.minValue
        maxValue: root.maxValue
        majorStep: root.majorStep
        minorStep: root.minorStep
        redlineFrom: root.redlineFrom
        labelText: root.labelText
    }

    Needle {
        centreX: root.centreX
        centreY: root.centreY
        angle: Theme.angleFor(root.value, root.minValue, root.maxValue)
        innerRadius: 96
        outerRadius: Theme.tickOuter - 16
        glowColor: root.accent
    }

    // ---------------------------------------------------------- inner disc
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.centreX
                centerY: root.centreY - Theme.innerRadius * 0.35
                centerRadius: Theme.innerRadius * 1.6
                focalX: root.centreX
                focalY: root.centreY - Theme.innerRadius * 0.35
                GradientStop { position: 0.00; color: "#16273A" }
                GradientStop { position: 0.55; color: "#0B1725" }
                GradientStop { position: 1.00; color: "#050B13" }
            }
            PathAngleArc {
                centerX: root.centreX
                centerY: root.centreY
                radiusX: Theme.innerRadius
                radiusY: Theme.innerRadius
                startAngle: 0
                sweepAngle: 360
            }
        }
    }

    Rectangle {
        readonly property real r: Theme.innerRadius
        x: root.centreX - r
        y: root.centreY - r
        width: r * 2
        height: r * 2
        radius: r
        color: "transparent"
        border.width: 1.5
        border.color: Qt.rgba(0.72, 0.83, 0.94, 0.22)
        antialiasing: true
    }

    // ------------------------------------------------------------- readout
    Text {
        text: root.valueText
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: root.valueSize
        font.italic: true
        font.weight: Font.Normal
        renderType: Text.QtRendering
        x: root.centreX - width / 2
        y: root.centreY + Theme.valueDy - height / 2
    }

    Text {
        text: root.unitText
        color: Theme.textDim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.unitSize
        renderType: Text.QtRendering
        x: root.centreX - width / 2
        y: root.centreY + Theme.unitDy - height / 2
    }
}
