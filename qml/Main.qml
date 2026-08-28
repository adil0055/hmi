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
        onOpenTextSizes: app.sizePanel.show()
    }

    /*!
        The text-size panel, opened from the control panel rather than shown
        at start-up: it is a reference for one job — reading and adjusting how
        big each run of text is set — and a third window in the way is a cost
        for everyone not doing that job.
    */
    property TextSizeWindow sizePanel: TextSizeWindow {
        cluster: app.cluster
        visible: appShowSizePanel
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
        // Sizes and offsets across the cluster are derived from these, so the
        // artwork re-aligns itself around whatever face has just been loaded.
        Theme.fontMetrics = Fonts.metrics
    }

    property Connections fontWatch: Connections {
        target: Fonts
        function onFamilyChanged() { app.syncFonts() }
        function onUiFamilyChanged() { app.syncFonts() }
    }

    /*!
        Push the saved text sizes into TextSizes.

        Assignment rather than a binding for the same reason as \l syncFonts:
        TextSizes is a singleton and cannot see the `Sizes` context property.
        Every size in the two themes is a binding onto these two, so the whole
        cluster reflows the moment either is replaced.
    */
    function syncSizes() {
        TextSizes.scale = Sizes.scale
        TextSizes.overrides = Sizes.overrides
    }

    property Connections sizeWatch: Connections {
        target: Sizes
        function onSizesChanged() { app.syncSizes() }
    }

    Component.onCompleted: {
        Theme.assetPath = appAssetPath
        syncFonts()
        syncSizes()
    }
}
