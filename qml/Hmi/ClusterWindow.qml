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

    readonly property real fitScale: Math.min(width / Theme.designW, height / Theme.designH)
    readonly property real renderScale: forcedScale > 0 ? forcedScale : fitScale

    title: qsTr("Instrument Cluster")
    color: Theme.black
    visible: true

    width: Math.min(Theme.designW, Screen.desktopAvailableWidth - 80)
    height: Math.round(width * Theme.designH / Theme.designW)

    Item {
        anchors.centerIn: parent
        width: Theme.designW
        height: Theme.designH
        scale: root.renderScale
        transformOrigin: Item.Center

        ClusterScene {
            vehicle: root.vehicle
        }
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
