import QtQuick
import Hmi

/*! Wrapper used by tools/shoot.py: the scene, scaled to fill the view. */
Item {
    id: harness

    Rectangle { anchors.fill: parent; color: Theme.black }

    Item {
        anchors.centerIn: parent
        width: Theme.designW
        height: Theme.designH
        scale: Math.min(harness.width / Theme.designW, harness.height / Theme.designH)
        transformOrigin: Item.Center

        ClusterScene { vehicle: Vehicle }
    }

    Component.onCompleted: {
        Theme.assetPath = appAssetPath
        Theme.fontFamily = appFontFamily
    }
}
