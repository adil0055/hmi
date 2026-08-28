import QtQuick
import Hmi

/*! Wrapper used by tools/shoot.py: the scene, scaled to fill the view. */
Item {
    id: harness

    readonly property string skin: Vehicle ? Vehicle.skin : "classic"
    readonly property int canvasW: scene.item ? scene.item.designW : Theme.designW
    readonly property int canvasH: scene.item ? scene.item.designH : Theme.designH

    Rectangle {
        anchors.fill: parent
        color: harness.skin === "bmw" ? BmwTheme.background : Theme.black
    }

    Item {
        anchors.centerIn: parent
        width: harness.canvasW
        height: harness.canvasH
        scale: Math.min(harness.width / harness.canvasW, harness.height / harness.canvasH)
        transformOrigin: Item.Center

        Loader {
            id: scene
            sourceComponent: harness.skin === "bmw" ? bmwScene : classicScene
        }
    }

    Component { id: classicScene; ClusterScene { vehicle: Vehicle } }
    Component { id: bmwScene; BmwScene { vehicle: Vehicle } }

    Component.onCompleted: {
        Theme.assetPath = appAssetPath
        // See Main.qml: singletons cannot resolve context properties, so this
        // has to be an assignment rather than a binding.
        Theme.fontFamily = Fonts.family
        Theme.uiFontFamily = Fonts.uiFamily
        Theme.fontMetrics = Fonts.metrics
    }
}
