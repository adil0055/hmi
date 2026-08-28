import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Hmi

/*!
    Every run of text in the cluster, how big it is currently set, and a
    slider for each.

    Three numbers per row, because "font size" means three different things
    once the typeface is switchable:

    \list
    \li \b design — what the artwork asks for, the number you edit here.
    \li \b set — what actually reaches \c font.pixelSize.  \l Theme.px scales
        the design size by how tall the loaded face draws its capitals, so a
        face with small capitals is set larger to look the same size.  This is
        the column that explains why swapping face changed nothing visible.
    \li \b screen — the same again times the cluster window's render scale,
        which is what you could measure on the glass.
    \endlist

    Editing goes through the `Sizes` context property rather than straight
    into \l TextSizes: Python owns the value, writes it to QSettings and hands
    it back, so what the panel shows is always what was stored.
*/
Window {
    id: root
    objectName: "textSizeWindow"

    /*! The cluster window, for its render scale; optional. */
    property var cluster: null

    title: qsTr("Cluster Text Sizes")
    width: 560
    height: Math.min(940, Screen.desktopAvailableHeight - 80)
    color: "#14181D"

    readonly property color panelBg: "#1B2128"
    readonly property color panelLine: "#2B333C"
    readonly property color labelColor: "#93A2B1"
    readonly property color valueColor: "#E6EDF4"
    readonly property color accentColor: "#4FA8E8"
    readonly property color changedColor: "#E8A33D"

    /*! Which skin's rows to list; "" lists both. */
    property string skinFilter: root.cluster ? root.cluster.skin : ""

    readonly property real renderScale: cluster && cluster.renderScale > 0
                                        ? cluster.renderScale : 1

    readonly property var rows: {
        var out = []
        var all = TextSizes.roles
        for (var i = 0; i < all.length; ++i)
            if (skinFilter === "" || all[i].skin === skinFilter)
                out.push(all[i])
        return out
    }

    /*!
        Pixel size a role is actually set at.

        Everything but the shift prompt is drawn in the cluster's typeface and
        so goes through the cap-height normalisation; that one run is drawn in
        the UI face at its nominal size, and reporting it normalised would be
        a lie about what is on screen.
    */
    function setPixels(role) {
        var size = TextSizes.size(role.id)
        return role.ui ? Math.round(size) : Theme.px(size)
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
        border.color: root.panelLine

        ColumnLayout {
            id: headerCol
            anchors.fill: parent
            anchors.margins: 11
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    text: qsTr("Set in %1").arg(Theme.fontFamily)
                    color: root.valueColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    // The cap-height correction in one number: how far the
                    // loaded face is from the one the artwork was drawn for.
                    text: qsTr("×%1 cap correction").arg(Theme.fontMetrics.capScale.toFixed(3))
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 11
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    text: qsTr("All text")
                    color: root.labelColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    Layout.preferredWidth: 62
                }
                Slider {
                    id: scaleSlider
                    Layout.fillWidth: true
                    from: 0.6
                    to: 1.8
                    stepSize: 0.01
                    value: Sizes.scale
                    onMoved: Sizes.scale = value
                }
                Text {
                    text: "×" + Sizes.scale.toFixed(2)
                    color: Sizes.scale === 1 ? root.valueColor : root.changedColor
                    font.family: Theme.uiFontFamily
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 46
                }
                Action {
                    text: qsTr("Reset all")
                    Layout.preferredWidth: 76
                    enabled: Sizes.modified
                    onClicked: Sizes.resetAll()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Tab {
                    text: qsTr("Classic")
                    Layout.fillWidth: true
                    on: root.skinFilter === "classic"
                    onClicked: root.skinFilter = "classic"
                }
                Tab {
                    text: qsTr("BMW")
                    Layout.fillWidth: true
                    on: root.skinFilter === "bmw"
                    onClicked: root.skinFilter = "bmw"
                }
                Tab {
                    text: qsTr("Both")
                    Layout.fillWidth: true
                    on: root.skinFilter === ""
                    onClicked: root.skinFilter = ""
                }
            }

            Text {
                Layout.fillWidth: true
                text: Sizes.overrideCount > 0
                      ? qsTr("%1 of %2 runs moved off the size they were drawn at — "
                             + "design → set → on screen.")
                        .arg(Sizes.overrideCount).arg(TextSizes.roles.length)
                      : qsTr("Design size → the size it is set at in this face → "
                             + "the size it covers on screen.")
                color: root.labelColor
                font.family: Theme.uiFontFamily
                font.pixelSize: 10
                wrapMode: Text.Wrap
                opacity: 0.8
            }
        }
    }

    // ----------------------------------------------------------- the listing
    ScrollView {
        id: list
        anchors.top: header.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        anchors.bottomMargin: 14
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: list.availableWidth
            spacing: 6

            Repeater {
                model: root.rows

                delegate: Rectangle {
                    id: row
                    required property int index
                    required property var modelData

                    readonly property real designSize: TextSizes.size(modelData.id)
                    readonly property real baseSize: TextSizes.baseSize(modelData.id)
                    readonly property bool overridden: TextSizes.isOverridden(modelData.id)
                    readonly property int setSize: root.setPixels(modelData)

                    /*! The first row of a group carries that group's heading. */
                    readonly property string heading:
                        index === 0 || root.rows[index - 1].group !== modelData.group
                        ? (root.skinFilter === "" ? modelData.skin.toUpperCase() + "  " : "")
                          + modelData.group.toUpperCase()
                        : ""

                    Layout.fillWidth: true
                    Layout.topMargin: row.heading === "" ? 0 : 22
                    implicitHeight: rowCol.implicitHeight + 18
                    radius: 8
                    color: root.panelBg
                    border.width: 1
                    border.color: row.overridden ? Qt.rgba(0.91, 0.64, 0.24, 0.5)
                                                 : root.panelLine

                    // Hung above the row rather than laid out with it, so a
                    // heading costs the list nothing where there is none.
                    RowLayout {
                        visible: row.heading !== ""
                        anchors.bottom: parent.top
                        anchors.bottomMargin: 5
                        anchors.left: parent.left
                        anchors.right: parent.right
                        spacing: 8
                        Text {
                            text: row.heading
                            color: root.accentColor
                            font.family: Theme.uiFontFamily
                            font.pixelSize: 11
                            font.letterSpacing: 1.5
                            font.weight: Font.DemiBold
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: root.panelLine
                        }
                    }

                    ColumnLayout {
                        id: rowCol
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    Layout.fillWidth: true
                                    text: row.modelData.label
                                    color: root.valueColor
                                    font.family: Theme.uiFontFamily
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: row.modelData.note
                                    color: root.labelColor
                                    font.family: Theme.uiFontFamily
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                            }

                            // design, then what it is set at, then on screen.
                            Text {
                                text: row.designSize.toFixed(row.designSize % 1 === 0 ? 0 : 1)
                                color: row.overridden || Sizes.scale !== 1
                                       ? root.changedColor : root.valueColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 15
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 42
                            }
                            Text {
                                text: "→ " + row.setSize + qsTr(" px")
                                color: root.labelColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 62
                            }
                            Text {
                                text: Math.round(row.setSize * root.renderScale)
                                      + qsTr(" on screen")
                                color: root.labelColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 10
                                opacity: 0.75
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 72
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Slider {
                                Layout.fillWidth: true
                                // Half to double what the artwork asks for:
                                // enough to rebalance a face, not enough to
                                // lose a run off the canvas without noticing.
                                from: Math.max(6, Math.round(row.baseSize * 0.5))
                                to: Math.round(row.baseSize * 2)
                                stepSize: 1
                                value: row.overridden
                                       ? TextSizes.overrides[row.modelData.id]
                                       : row.baseSize
                                onMoved: Sizes.setSize(row.modelData.id, value)
                            }

                            Text {
                                text: qsTr("drawn at %1").arg(row.baseSize)
                                color: root.labelColor
                                font.family: Theme.uiFontFamily
                                font.pixelSize: 10
                                opacity: row.overridden ? 1 : 0.45
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 66
                            }

                            Action {
                                text: qsTr("Reset")
                                implicitHeight: 24
                                Layout.preferredWidth: 54
                                enabled: row.overridden
                                onClicked: Sizes.resetSize(row.modelData.id)
                            }
                        }

                        // A specimen in the face the run is actually drawn in,
                        // so the number and the thing it describes sit
                        // together.  Its size tracks the row, which is what
                        // makes the list scannable — but only up to a point:
                        // the speed digits cover 116 design pixels and would
                        // otherwise push every other row off the window.
                        Text {
                            Layout.fillWidth: true
                            text: qsTr("0123 km/h  %1").arg(row.modelData.label)
                            color: root.valueColor
                            font.family: row.modelData.ui ? Theme.uiFontFamily
                                                          : Theme.fontFamily
                            font.pixelSize: Math.max(9, Math.min(24,
                                            row.setSize * root.renderScale))
                            elide: Text.ElideRight
                            opacity: 0.8
                        }
                    }
                }
            }
        }
    }
}
