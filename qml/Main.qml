import QtQuick
import QtQuick.Window
import Hmi

/*!
    Application root: the cluster display plus the separate control panel that
    feeds it test input.  Both windows share the one `Vehicle` model exposed
    from Python.
*/
QtObject {
    id: app

    property ClusterWindow cluster: ClusterWindow {
        vehicle: Vehicle
        forcedScale: appForcedScale
        visibility: appFullscreen ? Window.FullScreen : Window.Windowed
    }

    property ControlWindow panel: ControlWindow {
        vehicle: Vehicle
        visible: appShowPanel
        // Sit beside the cluster when there is room for both.
        x: Math.max(0, Screen.desktopAvailableWidth - width - 20)
        y: 40
    }

    Component.onCompleted: {
        Theme.assetPath = appAssetPath
        Theme.fontFamily = appFontFamily
    }
}
