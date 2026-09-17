import QtQuick
import Hmi

/*!
    A test pattern instead of the cluster, drawn at exact framebuffer
    coordinates.

    This is the cluster's side of the bargain with whatever is measuring it: a
    camera has to map its own pixels onto display pixels before any of its
    numbers mean anything, and the shortest way to establish that mapping is
    for the display to say exactly where things are rather than have it
    inferred from the artwork or the bezel.

    The geometry is not computed here.  It comes from backend/calibration.py
    through the \c Calibration context property, which is also what writes the
    exported corner list — so what is drawn and what the rig is told cannot
    drift apart. Changing the square size changes both at once.
*/
Item {
    id: root

    /*! Canvas to draw on; follows whichever skin is selected. */
    property int designW: 1790
    property int designH: 870

    width: designW
    height: designH

    readonly property string pattern: Calibration ? Calibration.pattern : ""
    readonly property var geom: Calibration ? Calibration.geometry(designW, designH) : null
    readonly property int square: geom ? geom.square_px : 100
    readonly property int cols: geom ? geom.cols : 0
    readonly property int rows: geom ? geom.rows : 0
    readonly property int originX: geom ? geom.origin[0] : 0
    readonly property int originY: geom ? geom.origin[1] : 0

    // Flat black under everything: it is the dark frame, and it is what the
    // quiet zone around the board is measured against.
    Rectangle {
        anchors.fill: parent
        color: root.pattern === "white" ? "#FFFFFF" : "#000000"
    }

    // ----------------------------------------------------------- chessboard
    Item {
        visible: root.pattern === "checker"
        anchors.fill: parent

        // Quiet zone. A board running to the edge of the panel gives the
        // detector nothing to separate the outer squares from what is beyond
        // the glass, and it will refuse the frame rather than return worse
        // corners.
        Rectangle {
            x: root.originX - root.square
            y: root.originY - root.square
            width: root.cols * root.square + 2 * root.square
            height: root.rows * root.square + 2 * root.square
            color: "#FFFFFF"
        }

        Repeater {
            model: root.cols * root.rows
            delegate: Rectangle {
                required property int index
                readonly property int col: index % root.cols
                readonly property int row: Math.floor(index / root.cols)
                visible: (col + row) % 2 === 0
                x: root.originX + col * root.square
                y: root.originY + row * root.square
                width: root.square
                height: root.square
                color: "#000000"
            }
        }
    }

    // ------------------------------------------------------------ plain grid
    Item {
        visible: root.pattern === "grid"
        anchors.fill: parent

        Repeater {
            model: Math.floor(root.designW / root.square) + 1
            delegate: Rectangle {
                required property int index
                x: index * root.square
                y: 0
                width: 1
                height: root.designH
                color: index % 5 === 0 ? "#FFFFFF" : "#4A5A6A"
            }
        }
        Repeater {
            model: Math.floor(root.designH / root.square) + 1
            delegate: Rectangle {
                required property int index
                x: 0
                y: index * root.square
                width: root.designW
                height: 1
                color: index % 5 === 0 ? "#FFFFFF" : "#4A5A6A"
            }
        }

        // Only this pattern carries a caption: on the others any extra mark is
        // something a detector could lock onto.
        Text {
            x: 12
            y: 8
            color: "#FFFFFF"
            font.family: Theme.uiFontFamily
            font.pixelSize: 22
            text: qsTr("%1×%2 canvas · %3 px grid").arg(root.designW)
                  .arg(root.designH).arg(root.square)
        }
    }

    // ------------------------------------------------------------ crosshairs
    Item {
        visible: root.pattern === "crosshair"
        anchors.fill: parent

        Repeater {
            model: [
                { x: root.square, y: root.square },
                { x: root.designW - root.square, y: root.square },
                { x: root.designW - root.square, y: root.designH - root.square },
                { x: root.square, y: root.designH - root.square },
                { x: Math.round(root.designW / 2), y: Math.round(root.designH / 2) }
            ]
            delegate: Item {
                required property var modelData
                Rectangle {
                    x: modelData.x - 60; y: modelData.y
                    width: 121; height: 1; color: "#FFFFFF"
                }
                Rectangle {
                    x: modelData.x; y: modelData.y - 60
                    width: 1; height: 121; color: "#FFFFFF"
                }
                Rectangle {
                    x: modelData.x - 24; y: modelData.y - 24
                    width: 49; height: 49; color: "transparent"
                    border.width: 1; border.color: "#FFFFFF"
                }
            }
        }
    }
}
