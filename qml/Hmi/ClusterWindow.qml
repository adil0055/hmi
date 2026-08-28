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

    // The two designs have different canvases — 1790x870 against 1920x720 —
    // so the window re-proportions itself when the skin changes.
    readonly property int canvasW: scene.item ? scene.item.designW : Theme.designW
    readonly property int canvasH: scene.item ? scene.item.designH : Theme.designH

    readonly property real fitScale: Math.min(width / canvasW, height / canvasH)
    readonly property real renderScale: forcedScale > 0 ? forcedScale : fitScale

    title: qsTr("Instrument Cluster")
    color: root.skin === "bmw" ? BmwTheme.background : Theme.black
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
            sourceComponent: root.skin === "bmw" ? bmwScene : classicScene
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
