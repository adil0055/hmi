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

    /*!
        Push the current typeface into Theme.

        This is a explicit assignment driven by FontManager's signals rather
        than a Qt.binding: a binding assigned to a singleton's property is
        evaluated in that singleton's scope, and QML singletons cannot see
        context properties like `Fonts`, so it would silently resolve to null.
    */
    function syncFonts() {
        Theme.fontFamily = Fonts.family
        Theme.uiFontFamily = Fonts.uiFamily
    }

    property Connections fontWatch: Connections {
        target: Fonts
        function onFamilyChanged() { app.syncFonts() }
        function onUiFamilyChanged() { app.syncFonts() }
    }

    Component.onCompleted: {
        Theme.assetPath = appAssetPath
        syncFonts()
    }
}
