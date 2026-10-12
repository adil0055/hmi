import QtQuick
import QtQuick.Window
import Hmi

/*!
    Hosts the cluster and scales it to fit.

    The scene is authored at Theme.designW x Theme.designH; this window picks a
    scale that fits the available screen and never upsamples past 1.0 by
    default, which keeps every tick mark pixel-crisp.
*/
Window {
    id: root
    objectName: "clusterWindow"

    property var vehicle: null
    property real forcedScale: 0
    /*! Which cluster design to draw; follows the model so the panel can swap it. */
    readonly property string skin: vehicle ? vehicle.skin : "classic"
    /*! While a calibration pattern is up, the cluster is not drawn at all. */
    readonly property bool calibrating: typeof Calibration !== "undefined" && Calibration !== null
                                      && Calibration.active === true

    // The two designs have different canvases — 1790x870 against 1920x720 —
    // so the window re-proportions itself when the skin changes.
    readonly property int canvasW: root.skin === "bmw" ? BmwTheme.designW : Theme.designW
    readonly property int canvasH: root.skin === "bmw" ? BmwTheme.designH : Theme.designH

    readonly property real fitScale: Math.min(width / canvasW, height / canvasH)
    readonly property real renderScale: forcedScale > 0 ? forcedScale : fitScale

    title: qsTr("Instrument Cluster")
    color: root.calibrating ? "black"
                            : (root.skin === "bmw" ? BmwTheme.background : Theme.black)
    visible: true

    width: Math.min(canvasW, Screen.desktopAvailableWidth - 80)
    height: Math.round(width * canvasH / canvasW)

    Item {
        anchors.centerIn: parent
        width: root.canvasW
        height: root.canvasH
        scale: root.renderScale
        transformOrigin: Item.Center

        Loader {
            id: scene
            sourceComponent: root.calibrating
                             ? calibrationScene
                             : (root.skin === "bmw" ? bmwScene : classicScene)
        }

        // The display itself, switched off or booting: the panel goes dark
        // inside its glass (the hood round it is moulding, and stays), and
        // while it boots it shows the welcome screen. Driven by the cluster
        // ECU's power state, which follows the ignition on the bus.
        Rectangle {
            id: dark
            readonly property bool framed: root.skin !== "bmw"
            visible: !root.calibrating && root.vehicle !== null
                     && (root.vehicle.power === "off" || root.vehicle.power === "boot")
            x: framed ? Theme.glassRect.x : 0
            y: framed ? Theme.glassRect.y : 0
            width: framed ? Theme.glassRect.width : root.canvasW
            height: framed ? Theme.glassRect.height : root.canvasH
            radius: framed ? Theme.glassRadius : 0
            color: "black"
            antialiasing: true

            Column {
                anchors.centerIn: parent
                spacing: 14
                visible: root.vehicle !== null && root.vehicle.power === "boot"
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 400 } }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 120; height: 120; radius: 60
                    color: "transparent"
                    border.color: Theme.accent
                    border.width: 6
                    Text {
                        anchors.centerIn: parent
                        text: "HMI"
                        color: Theme.accentBright
                        font.family: Theme.fontFamily
                        font.pixelSize: 40
                        font.weight: Font.DemiBold
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: qsTr("Welcome")
                    color: "#C9D6DF"
                    font.family: Theme.fontFamily
                    font.pixelSize: 30
                }
            }
        }
    }

    Component {
        id: classicScene
        ClusterScene { vehicle: root.vehicle }
    }

    Component {
        id: bmwScene
        BmwScene { vehicle: root.vehicle }
    }

    Component {
        id: calibrationScene
        CalibrationScene { designW: root.canvasW; designH: root.canvasH }
    }

    // ------------------------------------------------------------ shortcuts
    Item {
        anchors.fill: parent
        focus: true

        Keys.onPressed: function (event) {
            switch (event.key) {
            case Qt.Key_F11:
                root.visibility = root.visibility === Window.FullScreen
                        ? Window.Windowed : Window.FullScreen
                event.accepted = true
                break
            case Qt.Key_B:
                if (root.vehicle)
                    root.vehicle.showBezel = !root.vehicle.showBezel
                event.accepted = true
                break
            case Qt.Key_Escape:
                if (root.visibility === Window.FullScreen) {
                    root.visibility = Window.Windowed
                    event.accepted = true
                }
                break
            }
        }
    }
}
