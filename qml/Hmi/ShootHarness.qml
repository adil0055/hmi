import QtQuick
import Hmi

/*! Wrapper used by tools/shoot.py: the scene, scaled to fill the view. */
Item {
    id: harness

    readonly property string skin: Vehicle ? Vehicle.skin : "classic"
    readonly property bool calibrating: typeof Calibration !== "undefined" && Calibration !== null
                                      && Calibration.active === true
    readonly property int canvasW: skin === "bmw" ? BmwTheme.designW : Theme.designW
    readonly property int canvasH: skin === "bmw" ? BmwTheme.designH : Theme.designH

    Rectangle {
        anchors.fill: parent
        color: harness.calibrating ? "black"
                                   : (harness.skin === "bmw" ? BmwTheme.background : Theme.black)
    }

    Item {
        anchors.centerIn: parent
        width: harness.canvasW
        height: harness.canvasH
        scale: Math.min(harness.width / harness.canvasW, harness.height / harness.canvasH)
        transformOrigin: Item.Center

        Loader {
            id: scene
            sourceComponent: harness.calibrating
                             ? calibrationScene
                             : (harness.skin === "bmw" ? bmwScene : classicScene)
        }
    }

    Component { id: classicScene; ClusterScene { vehicle: Vehicle } }
    Component { id: bmwScene; BmwScene { vehicle: Vehicle } }
    Component {
        id: calibrationScene
        CalibrationScene { designW: harness.canvasW; designH: harness.canvasH }
    }

    Component.onCompleted: {
        Theme.assetPath = appAssetPath
        // See Main.qml: singletons cannot resolve context properties, so this
        // has to be an assignment rather than a binding.
        Theme.fontFamily = Fonts.family
        Theme.uiFontFamily = Fonts.uiFamily
        Theme.fontMetrics = Fonts.metrics
        // Text sizes likewise, so a shot matches what the app would draw.
        TextSizes.scale = Sizes.scale
        TextSizes.overrides = Sizes.overrides
        // Layout faults likewise, so a shot shows the displacement that was
        // commanded rather than a correct cluster.
        LayoutRoles.enabled = LayoutFaults.enabled
        LayoutRoles.faults = LayoutFaults.faults
    }
}
