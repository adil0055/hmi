import QtQuick
import QtQuick.Shapes
import Hmi

/*!
    What is playing, in the gap between the two chevrons: cover art, title,
    artist and a progress line with the time left.

    There is no real cover to show, so the tile draws one — a dusk gradient
    behind two ridge lines, tinted from the drive mode's accent.  It reads as
    artwork at a glance, which is all this space is doing, and it means the
    centre of the cluster picks up the mode colour along with everything else.
*/
Item {
    id: root

    property string title: "Indeed"
    property string artist: "Jacob Thommsen"
    property int elapsed: 0
    property int duration: 0
    property bool playing: true
    property color accent: "#D9A05B"

    readonly property real progress: duration > 0
        ? Math.max(0, Math.min(1, elapsed / duration)) : 0

    anchors.fill: parent

    function _clock(seconds) {
        var s = Math.max(0, Math.round(seconds))
        return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2)
    }

    // ------------------------------------------------------------ cover art
    Item {
        id: art
        x: BmwTheme.centreX - BmwTheme.artSize / 2
        y: BmwTheme.artY
        width: BmwTheme.artSize
        height: BmwTheme.artSize
        clip: true

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.lighter(root.accent, 1.5) }
                GradientStop { position: 0.55; color: Qt.darker(root.accent, 1.15) }
                GradientStop { position: 1.0; color: Qt.darker(root.accent, 2.6) }
            }
        }

        // Two ridges, the far one hazier than the near one.
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "transparent"
                fillColor: Qt.rgba(0, 0, 0, 0.22)
                PathPolyline {
                    path: [Qt.point(0, art.height), Qt.point(0, art.height * 0.62),
                           Qt.point(art.width * 0.34, art.height * 0.34),
                           Qt.point(art.width * 0.62, art.height * 0.66),
                           Qt.point(art.width, art.height * 0.44),
                           Qt.point(art.width, art.height)]
                }
            }
            ShapePath {
                strokeColor: "transparent"
                fillColor: Qt.rgba(0, 0, 0, 0.45)
                PathPolyline {
                    path: [Qt.point(0, art.height), Qt.point(0, art.height * 0.84),
                           Qt.point(art.width * 0.46, art.height * 0.55),
                           Qt.point(art.width, art.height * 0.88),
                           Qt.point(art.width, art.height)]
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.14)
        }
    }

    // ------------------------------------------------------- title / artist
    ClusterText {
        text: root.title.toUpperCase()
        designSize: BmwTheme.trackTitleSize
        color: root.accent
        font.letterSpacing: 1.2
        fitWidth: BmwTheme.progressHalfW * 2
        elide: Text.ElideRight
        x: BmwTheme.centreX - width / 2
        y: BmwTheme.trackTitleY - height / 2 + Theme.capDy(BmwTheme.trackTitleSize)
    }

    ClusterText {
        text: root.artist.toUpperCase()
        designSize: BmwTheme.trackArtistSize
        color: BmwTheme.textSecondary
        font.letterSpacing: 1.0
        fitWidth: BmwTheme.progressHalfW * 2
        elide: Text.ElideRight
        x: BmwTheme.centreX - width / 2
        y: BmwTheme.trackArtistY - height / 2 + Theme.capDy(BmwTheme.trackArtistSize)
    }

    // ------------------------------------------------------------- progress
    Rectangle {
        id: rail
        x: BmwTheme.centreX - BmwTheme.progressHalfW
        y: BmwTheme.progressY
        width: BmwTheme.progressHalfW * 2
        height: 2
        color: Qt.rgba(1, 1, 1, 0.16)

        Rectangle {
            width: parent.width * root.progress
            height: parent.height
            color: root.accent
            Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
        }

        // Playhead.
        Rectangle {
            x: parent.width * root.progress - width / 2
            y: -2.5
            width: 7
            height: 7
            radius: 3.5
            color: Qt.lighter(root.accent, 1.6)
            visible: root.duration > 0
            Behavior on x { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            // A slow pulse while playing, still when paused.
            SequentialAnimation on scale {
                running: root.playing && root.duration > 0
                loops: Animation.Infinite
                NumberAnimation { to: 1.35; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
            }
        }
    }

    ClusterText {
        visible: root.duration > 0
        text: "- " + root._clock(root.duration - root.elapsed)
        designSize: BmwTheme.trackRemainingSize
        color: BmwTheme.textDim
        x: rail.x + rail.width - width
        y: rail.y + 12
    }

    ClusterText {
        visible: !root.playing
        text: qsTr("PAUSED")
        designSize: BmwTheme.trackPausedSize
        color: BmwTheme.textDim
        font.letterSpacing: 1.4
        x: rail.x
        y: rail.y + 12
    }
}
