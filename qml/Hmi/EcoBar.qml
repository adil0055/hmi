import QtQuick
import Hmi

/*! Instantaneous fuel-economy bar with its 0..30 scale. */
Item {
    id: root

    /*! Reading in km/L. */
    property real value: 0
    property color accent: Theme.accent

    anchors.fill: parent

    readonly property rect r: Theme.ecoBarRect

    // Trough.
    Rectangle {
        x: root.r.x
        y: root.r.y
        width: root.r.width
        height: root.r.height
        radius: height / 2
        antialiasing: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#C4CCD4" }
            GradientStop { position: 0.55; color: "#98A3AE" }
            GradientStop { position: 1.0; color: "#79848F" }
        }
    }

    // Live fill.
    Rectangle {
        visible: root.value > 0.05
        x: root.r.x
        y: root.r.y
        width: Math.max(root.r.height,
                        root.r.width * Math.min(1, root.value / Theme.ecoMax))
        height: root.r.height
        radius: height / 2
        antialiasing: true
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.lighter(root.accent, 1.25) }
            GradientStop { position: 1.0; color: root.accent }
        }
        Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutQuad } }
    }

    // Scale notches inside the trough.
    Repeater {
        model: 2
        delegate: Rectangle {
            required property int index
            x: root.r.x + root.r.width * (index + 1) / 3 - 1
            y: root.r.y + 3
            width: 2
            height: root.r.height - 6
            color: Qt.rgba(0, 0, 0, 0.28)
        }
    }

    // Scale numerals.
    Repeater {
        model: [0, 10, 20, 30]
        delegate: Text {
            required property int index
            required property var modelData
            text: String(modelData)
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.ecoScaleSize
            x: root.r.x + root.r.width * index / 3 - width / 2
            y: Theme.ecoScaleY - height / 2
        }
    }
}
