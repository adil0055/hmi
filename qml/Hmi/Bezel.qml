import QtQuick
import Hmi

/*! The instrument hood and the glass panel the cluster is drawn on. */
Item {
    id: root

    anchors.fill: parent

    readonly property rect hood: Theme.hoodRect
    readonly property rect glass: Theme.glassRect

    Rectangle {
        anchors.fill: parent
        color: Theme.black
    }

    // Moulded hood around the display.
    Rectangle {
        x: root.hood.x
        y: root.hood.y
        width: root.hood.width
        height: root.hood.height
        radius: Theme.hoodRadius
        antialiasing: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.bezelTop }
            GradientStop { position: 0.42; color: "#141618" }
            GradientStop { position: 1.0; color: Theme.bezelBottom }
        }
    }

    // Light catching the top edge of the moulding.
    Rectangle {
        x: root.hood.x + 1
        y: root.hood.y + 1
        width: root.hood.width - 2
        height: root.hood.height - 2
        radius: Theme.hoodRadius - 1
        color: "transparent"
        border.width: 1.6
        border.color: Qt.rgba(0.36, 0.39, 0.43, 0.55)
        antialiasing: true
    }

    // Shadow line where the glass drops into the hood.
    Rectangle {
        x: root.glass.x - 5
        y: root.glass.y - 5
        width: root.glass.width + 10
        height: root.glass.height + 10
        radius: Theme.glassRadius + 5
        color: "#000000"
        opacity: 0.85
        antialiasing: true
    }

    Rectangle {
        x: root.glass.x
        y: root.glass.y
        width: root.glass.width
        height: root.glass.height
        radius: Theme.glassRadius
        color: Theme.screenBg
        antialiasing: true
    }
}
