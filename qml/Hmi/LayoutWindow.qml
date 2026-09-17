import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Hmi

/*!
    Draw the cluster deliberately wrong, by an exact amount.

    A camera-based layout check cannot be trusted until it has been shown to
    report a displacement that was really applied: on a cluster that is already
    correct, a validator that always answered PASS would score full marks.  So
    this panel moves, resizes, turns and hides elements on command, and the
    commanded numbers are exact — they are what a measurement gets scored
    against, not another opinion about where things are.

    Everything here is in \e design pixels, the units \l Theme and \l BmwTheme
    are written in, so a commanded 3 px is 3 px of the framebuffer whatever the
    cluster window has been scaled to.  \c Screen shows what the same
    displacement comes to at the current render scale, which is what a camera
    pointed at the glass would actually see.

    Editing goes through the `LayoutFaults` context property rather than
    straight into \l LayoutRoles: Python owns the value, writes it to
    QSettings and hands it back, so what the panel shows is what was stored.
*/
Window {
    id: root
    objectName: "layoutWindow"

    /*! The cluster window, for its render scale; optional. */
    property var cluster: null

    title: qsTr("Cluster Layout Faults")
    width: 760
    height: Math.min(900, Screen.desktopAvailableHeight - 80)
    color: "#14181D"

    readonly property color panelBg: "#1B2128"
    readonly property color panelLine: "#2B333C"
    readonly property color labelColor: "#93A2B1"
    readonly property color valueColor: "#E6EDF4"
    readonly property color accentColor: "#4FA8E8"
    readonly property color changedColor: "#E8A33D"
    readonly property color warnColor: "#E8604D"

    /*! Which skin's rows to list; "" lists both. */
    property string skinFilter: root.cluster ? root.cluster.skin : ""

    readonly property real renderScale: cluster && cluster.renderScale > 0
                                        ? cluster.renderScale : 1

    readonly property int canvasW: cluster && cluster.canvasW ? cluster.canvasW : 1790
    readonly property int canvasH: cluster && cluster.canvasH ? cluster.canvasH : 870

    readonly property var rows: {
        var out = []
        var all = LayoutRoles.items
        for (var i = 0; i < all.length; ++i)
            if (skinFilter === "" || all[i].skin === skinFilter)
                out.push(all[i])
        return out
    }

    // ---------------------------------------------------------------- pieces
    component Action: Button {
        id: act
        implicitHeight: 30
        font.family: Theme.uiFontFamily
        font.pixelSize: 12
        background: Rectangle {
            radius: 6
            color: act.down ? "#39454F" : (act.hovered ? "#2C353F" : "#242D36")
            border.width: 1
            border.color: root.panelLine
            opacity: act.enabled ? 1 : 0.45
        }
        contentItem: Text {
            text: act.text
            color: root.valueColor
            font: act.font
            opacity: act.enabled ? 1 : 0.5
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component Tab: Button {
        id: tab
        property bool on: false
        implicitHeight: 28
        font.family: Theme.uiFontFamily
        font.pixelSize: 12
        background: Rectangle {
            radius: 6
            color: tab.on ? root.accentColor : (tab.hovered ? "#2C353F" : "#232B33")
            border.width: 1
            border.color: tab.on ? root.accentColor : root.panelLine
        }
        contentItem: Text {
            text: tab.text
            color: tab.on ? "#0D1116" : root.valueColor
            font: tab.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    /*!
        A typed number.

        A text field rather than a slider on purpose: the value of this panel
        is that the displacement is *known*, and a slider gives you 2.7 when
        you meant 3.  The field only writes back when editing finishes, and
        only re-reads the model when it does not have focus, so it does not
        fight what is being typed into it.
    */
    component Num: TextField {
        id: field
        property real modelValue: 0
        property real neutralValue: 0
        signal committed(real value)

        implicitWidth: 62
        implicitHeight: 28
        horizontalAlignment: TextInput.AlignHCenter
        font.family: Theme.uiFontFamily
        font.pixelSize: 12
        color: modelValue === neutralValue ? root.valueColor : root.changedColor
        selectByMouse: true
        validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
        background: Rectangle {
            radius: 5
            color: field.activeFocus ? "#232D36" : "#1E252C"
            border.width: 1
            border.color: field.activeFocus ? root.accentColor : root.panelLine
        }
        text: formatted(modelValue)
        onModelValueChanged: if (!activeFocus) text = formatted(modelValue)
        onActiveFocusChanged: if (!activeFocus) text = formatted(modelValue)
        onEditingFinished: {
            var v = parseFloat(text)
            committed(isNaN(v) ? neutralValue : v)
        }
        function formatted(v) {
            return Math.abs(v - Math.round(v)) < 0.0005
                    ? String(Math.round(v)) : v.toFixed(2)
        }
    }

    // ------------------------------------------------------------- top strip
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 14
        implicitHeight: headerCol.implicitHeight + 22
        radius: 8
        color: root.panelBg
        border.width: 1
        border.color: LayoutFaults.modified && LayoutFaults.enabled
                      ? root.warnColor : root.panelLine

        ColumnLayout {
            id: headerCol
            anchors.fill: parent
            anchors.margins: 11
            spacing: 8

            // The banner. A cluster quietly drawing a few pixels out because
            // somebody left it that way is the sort of thing that gets
            // diagnosed for a fortnight as a camera fault, so it says so.
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font.family: Theme.uiFontFamily
                font.pixelSize: 12
                color: Calibration.active ? root.accentColor
                       : LayoutFaults.modified
                       ? (LayoutFaults.enabled ? root.warnColor : root.changedColor)
                       : root.labelColor
                text: Calibration.active
                      ? qsTr("A calibration pattern is up, so the cluster is not being drawn and these faults do nothing. Set the pattern to Off to see them.")
                      : !LayoutFaults.modified
                      ? qsTr("The cluster is drawing its layout as designed.")
                      : LayoutFaults.enabled
                        ? qsTr("%1 element(s) are deliberately out of place. Nothing measured off this screen is valid until they are reset.")
                          .arg(LayoutFaults.faultCount)
                        : qsTr("%1 fault(s) stored but switched off — the cluster is drawing correctly.")
                          .arg(LayoutFaults.faultCount)
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Switch {
                    id: masterSwitch
                    text: qsTr("Apply faults")
                    checked: LayoutFaults.enabled
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 12
                    onToggled: LayoutFaults.enabled = checked
                    contentItem: Text {
                        text: masterSwitch.text
                        color: root.valueColor
                        font: masterSwitch.font
                        leftPadding: masterSwitch.indicator.width + 8
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: qsTr("render ×%1").arg(root.renderScale.toFixed(3))
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 11
                }
                Action {
                    text: qsTr("Reset all")
                    Layout.preferredWidth: 82
                    enabled: LayoutFaults.modified
                    onClicked: LayoutFaults.resetAll()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Tab {
                    text: qsTr("This cluster")
                    on: root.skinFilter !== ""
                    Layout.fillWidth: true
                    onClicked: root.skinFilter = root.cluster ? root.cluster.skin : "classic"
                }
                Tab {
                    text: qsTr("Both")
                    on: root.skinFilter === ""
                    Layout.fillWidth: true
                    onClicked: root.skinFilter = ""
                }
            }

            // Column captions, so the four numbers are not a guessing game.
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Item { Layout.fillWidth: true }
                Text { text: qsTr("dx");    color: root.labelColor; Layout.preferredWidth: 62
                       horizontalAlignment: Text.AlignHCenter
                       font.family: Theme.uiFontFamily; font.pixelSize: 11 }
                Text { text: qsTr("dy");    color: root.labelColor; Layout.preferredWidth: 62
                       horizontalAlignment: Text.AlignHCenter
                       font.family: Theme.uiFontFamily; font.pixelSize: 11 }
                Text { text: qsTr("scale"); color: root.labelColor; Layout.preferredWidth: 62
                       horizontalAlignment: Text.AlignHCenter
                       font.family: Theme.uiFontFamily; font.pixelSize: 11 }
                Text { text: qsTr("rot°");  color: root.labelColor; Layout.preferredWidth: 62
                       horizontalAlignment: Text.AlignHCenter
                       font.family: Theme.uiFontFamily; font.pixelSize: 11 }
                Item { Layout.preferredWidth: 150 }
            }
        }
    }

    // ------------------------------------------------------- calibration strip
    Rectangle {
        id: calibStrip
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 14
        anchors.topMargin: 10
        implicitHeight: calibCol.implicitHeight + 22
        radius: 8
        color: root.panelBg
        border.width: 1
        border.color: Calibration.active ? root.accentColor : root.panelLine

        ColumnLayout {
            id: calibCol
            anchors.fill: parent
            anchors.margins: 11
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: qsTr("Calibration pattern")
                    color: root.valueColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.fillWidth: true
                }
                Text {
                    text: qsTr("square")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 11
                }
                Num {
                    modelValue: Calibration.squarePx
                    neutralValue: Calibration.squarePx
                    implicitWidth: 54
                    onCommitted: function (v) { Calibration.squarePx = Math.round(v) }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: [
                        { id: "",          label: qsTr("Off") },
                        { id: "checker",   label: qsTr("Chessboard") },
                        { id: "white",     label: qsTr("White") },
                        { id: "black",     label: qsTr("Black") },
                        { id: "grid",      label: qsTr("Grid") },
                        { id: "crosshair", label: qsTr("Crosses") }
                    ]
                    delegate: Tab {
                        required property var modelData
                        text: modelData.label
                        on: Calibration.pattern === modelData.id
                        Layout.fillWidth: true
                        onClicked: Calibration.pattern = modelData.id
                    }
                }
            }

            // The board's own numbers, so nobody has to guess them off the
            // glass, and the reminder about which convention the corners are
            // in — picking the wrong one is half a pixel of error through the
            // whole homography.
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: root.labelColor
                font.family: Theme.uiFontFamily
                font.pixelSize: 11
                text: {
                    if (!Calibration.active)
                        return qsTr("The cluster is drawing itself. Pick a pattern to give a camera something exact to solve its geometry against.")
                    var g = Calibration.geometry(root.canvasW, root.canvasH)
                    return qsTr("%1×%2 board of %3 px squares at (%4, %5) on a %6×%7 canvas — %8 inner corners. Export them with --calibration-export; they are in pixel-centre coordinates, not Qt's.")
                        .arg(g.cols).arg(g.rows).arg(g.square_px)
                        .arg(g.origin[0]).arg(g.origin[1])
                        .arg(g.canvas[0]).arg(g.canvas[1])
                        .arg(g.corners_pixel_centre.length)
                }
            }
        }
    }

    // ----------------------------------------------------------------- rows
    ScrollView {
        anchors.top: calibStrip.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 14
        anchors.topMargin: 10
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 8

            Repeater {
                model: root.rows

                delegate: Rectangle {
                    id: row
                    required property var modelData

                    readonly property var fault: LayoutFaults.faults[modelData.id]
                             || LayoutRoles.neutral
                    readonly property bool faulted: LayoutFaults.isFaulted(modelData.id)

                    Layout.fillWidth: true
                    implicitHeight: rowCol.implicitHeight + 18
                    radius: 8
                    color: root.panelBg
                    border.width: 1
                    border.color: row.faulted ? root.changedColor : root.panelLine

                    ColumnLayout {
                        id: rowCol
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Text {
                                    text: row.modelData.label
                                    color: root.valueColor
                                    font.family: Theme.uiFontFamily
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: row.modelData.note
                                    color: root.labelColor
                                    font.family: Theme.uiFontFamily
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            Num {
                                modelValue: row.fault.dx
                                onCommitted: function (v) {
                                    LayoutFaults.setShift(row.modelData.id, v, row.fault.dy)
                                }
                            }
                            Num {
                                modelValue: row.fault.dy
                                onCommitted: function (v) {
                                    LayoutFaults.setShift(row.modelData.id, row.fault.dx, v)
                                }
                            }
                            Num {
                                modelValue: row.fault.scale
                                neutralValue: 1
                                onCommitted: function (v) {
                                    LayoutFaults.setScale(row.modelData.id, v)
                                }
                            }
                            Num {
                                modelValue: row.fault.rot
                                onCommitted: function (v) {
                                    LayoutFaults.setRotation(row.modelData.id, v)
                                }
                            }

                            Action {
                                text: qsTr("Hide")
                                Layout.preferredWidth: 58
                                onClicked: LayoutFaults.setHidden(row.modelData.id,
                                                                  !row.fault.hidden)
                                background: Rectangle {
                                    radius: 6
                                    color: row.fault.hidden ? root.warnColor : "#242D36"
                                    border.width: 1
                                    border.color: row.fault.hidden ? root.warnColor
                                                                   : root.panelLine
                                }
                            }
                            Action {
                                text: qsTr("Reset")
                                Layout.preferredWidth: 62
                                enabled: LayoutFaults.isFaulted(row.modelData.id)
                                onClicked: LayoutFaults.resetRole(row.modelData.id)
                            }
                        }

                        // Nudges, and what the commanded shift comes to on the
                        // glass — the number a camera would be measuring.
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 5

                            Text {
                                text: row.modelData.id
                                color: root.labelColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                visible: row.fault.dx !== 0 || row.fault.dy !== 0
                                text: qsTr("%1 px on screen")
                                      .arg((Math.hypot(row.fault.dx, row.fault.dy)
                                            * root.renderScale).toFixed(2))
                                color: root.changedColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 10
                            }
                            Repeater {
                                model: [
                                    { t: "←", x: -1, y: 0 }, { t: "→", x: 1, y: 0 },
                                    { t: "↑", x: 0, y: -1 }, { t: "↓", x: 0, y: 1 }
                                ]
                                delegate: Action {
                                    required property var modelData
                                    text: modelData.t
                                    implicitHeight: 22
                                    Layout.preferredWidth: 28
                                    onClicked: LayoutFaults.nudge(row.modelData.id,
                                                                  modelData.x, modelData.y)
                                }
                            }
                            Action {
                                text: qsTr("±¼")
                                implicitHeight: 22
                                Layout.preferredWidth: 34
                                onClicked: LayoutFaults.nudge(row.modelData.id, 0.25, 0)
                            }
                        }
                    }
                }
            }
        }
    }
}
