import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import Hmi

/*!
    The BMW-style cluster: two chevron gauges facing each other, the speed and
    the selected gear pushed out to the edges, what is playing in the middle,
    and a status strip along the bottom.

    Laid out on BmwTheme's canvas rather than Theme's — the parent scales this
    item as a whole, so nothing in here reads the window size.

    Animation is not decoration on a cluster; it is how the screen tells you it
    is alive and that a value moved rather than jumped.  What runs here:

    \list
    \li a wake-up sweep — both bands run to full scale and back, the way a
        real cluster proves its instruments on power-up, with the furniture
        fading in behind it;
    \li every gauge chases its value with easing (in BmwGauge) instead of
        snapping, and the scale lights up tick by tick as it passes;
    \li the speed counts rather than cuts, so a digit change is legible;
    \li the gear letter lifts and settles when the selection changes;
    \li drive mode cross-fades the accent through everything at once — bands,
        cover art, mode caption;
    \li the power band pulses once it is near the stop, and the recuperation
        side of the scale swaps to its own colour below zero;
    \li indicators, telltales and the charging lamp blink or breathe.
    \endlist
*/
Item {
    id: root

    property var vehicle: null

    readonly property int designW: BmwTheme.designW
    readonly property int designH: BmwTheme.designH

    width: designW
    height: designH

    readonly property bool awake: vehicle ? vehicle.ignition > 0 : true
    readonly property string mode: vehicle ? vehicle.driveMode : "Comfort"
    readonly property color accentLeft: BmwTheme.accentFor(mode, false)
    readonly property color accentRight: BmwTheme.accentFor(mode, true)

    // ePower runs -1..1 in the model; the band shows 0..100 of the positive
    // half and turns the recuperation range into its own colour below that.
    readonly property real power: vehicle ? vehicle.ePower : 0
    readonly property bool recuperating: power < -0.02

    // -------------------------------------------------------- wake-up sweep
    /*! True while the instruments are proving themselves rather than reading. */
    property bool intro: false
    /*! 0..1 sweep position, only meaningful while \l intro. */
    property real introT: 0
    /*! 0..1 fade-in for everything that is not a gauge band. */
    property real reveal: 0

    SequentialAnimation {
        id: introAnim
        PropertyAction { target: root; property: "intro"; value: true }
        ParallelAnimation {
            NumberAnimation {
                target: root; property: "introT"
                from: 0; to: 1; duration: 780; easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: root; property: "reveal"
                from: 0; to: 1; duration: 620; easing.type: Easing.OutCubic
            }
        }
        NumberAnimation {
            target: root; property: "introT"
            to: 0; duration: 620; easing.type: Easing.InOutCubic
        }
        PropertyAction { target: root; property: "intro"; value: false }
    }

    function playIntro() {
        introAnim.restart()
    }

    Component.onCompleted: if (root.awake) playIntro()

    onAwakeChanged: {
        if (awake) {
            playIntro()
        } else {
            introAnim.stop()
            intro = false
            introT = 0
            reveal = 0
        }
    }

    // ------------------------------------------------------ smoothed values
    /*! Speed the readout shows: counts towards the real one instead of cutting. */
    property real shownSpeed: 0
    Behavior on shownSpeed { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Binding {
        target: root
        property: "shownSpeed"
        value: root.vehicle ? root.vehicle.speed : 0
        when: !root.intro
    }

    // ---------------------------------------------------------- background
    Rectangle {
        anchors.fill: parent
        color: BmwTheme.background
    }

    // A faint wireframe behind the middle, so the centre reads as a surface
    // rather than a void.  It has to stay at the very edge of visible: the
    // moment you can actually see it, it competes with the readouts.
    Item {
        anchors.fill: parent
        opacity: root.reveal
        // Faded out at both ends so the mesh has no border, it just stops.
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: meshMask
            maskSpreadAtMin: 0.1
        }

        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.lineWidth = 1
                ctx.strokeStyle = Qt.rgba(0.40, 0.54, 0.72, 0.085)
                var yTop = 108
                var yBot = 552
                var step = 74
                ctx.beginPath()
                for (var x = BmwTheme.leftApexX - 460; x < BmwTheme.rightApexX + 460; x += step) {
                    ctx.moveTo(x, yTop); ctx.lineTo(x + 340, yBot)
                    ctx.moveTo(x, yBot); ctx.lineTo(x + 340, yTop)
                }
                ctx.stroke()
            }
        }
    }

    Item {
        id: meshMask
        anchors.fill: parent
        visible: false
        layer.enabled: true
        Rectangle {
            x: BmwTheme.leftApexX - 20
            y: 90
            width: BmwTheme.rightApexX - BmwTheme.leftApexX + 40
            height: 480
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.35; color: "white" }
                GradientStop { position: 0.65; color: "white" }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
    }

    // -------------------------------------------------------------- gauges
    LayoutShift {
        role: "bmw.gauge.speed"
        pivotX: BmwTheme.leftApexX / 2; pivotY: BmwTheme.designH / 2
        BmwGauge {
            id: speedGauge
            mirrored: false
            minValue: 0
            maxValue: BmwTheme.speedMax
            majorStep: 30
            minorStep: 10
            caption: root.vehicle ? Fmt.speedUnit(root.vehicle.units) : "km/h"
            accent: root.accentLeft
            reveal: root.reveal
            value: root.intro ? BmwTheme.speedMax * root.introT
                              : (root.vehicle ? root.vehicle.speed : 0)
            Behavior on accent { ColorAnimation { duration: 420 } }
        }
    }

    LayoutShift {
        role: "bmw.gauge.power"
        pivotX: (BmwTheme.rightApexX + BmwTheme.designW) / 2; pivotY: BmwTheme.designH / 2
        BmwGauge {
            id: powerGauge
            mirrored: true
            minValue: 0
            maxValue: BmwTheme.powerMax
            majorStep: 25
            minorStep: 12.5
            caption: qsTr("ePower %")
            // Recuperation gets the cool colour whatever the mode, because it is a
            // different thing happening, not a different amount of the same thing.
            accent: root.recuperating ? "#3FD9A0" : root.accentRight
            reveal: root.reveal
            value: root.intro
                   ? BmwTheme.powerMax * root.introT
                   : BmwTheme.powerMax * Math.abs(root.power)
            Behavior on accent { ColorAnimation { duration: 420 } }

            // Near the stop the band breathes, the way a rev counter nags near
            // the redline.
            SequentialAnimation on opacity {
                running: !root.intro && Math.abs(root.power) > 0.88
                loops: Animation.Infinite
                onStopped: powerGauge.opacity = 1
                NumberAnimation { to: 0.55; duration: 320; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 320; easing.type: Easing.InOutSine }
            }
        }
    }

    // ------------------------------------------------------- speed readout
    LayoutShift {
        role: "bmw.speed.value"
        pivotX: BmwTheme.speedX; pivotY: BmwTheme.speedY
        ClusterText {
            id: speedText
            text: root.vehicle
                  ? String(Fmt.speedValue(root.intro ? BmwTheme.speedMax * root.introT
                                                     : root.shownSpeed, root.vehicle.units))
                  : "0"
            designSize: BmwTheme.speedSize
            color: BmwTheme.textPrimary
            opacity: root.reveal
            fitWidth: 250
            horizontalAlignment: Text.AlignHCenter
            x: BmwTheme.speedX - width / 2
            y: BmwTheme.speedY - height / 2 + Theme.capDy(BmwTheme.speedSize)
        }
    }

    LayoutShift {
        role: "bmw.speed.unit"
        pivotX: BmwTheme.speedX; pivotY: BmwTheme.speedY + 78
        ClusterText {
            text: root.vehicle ? Fmt.speedUnit(root.vehicle.units) : "km/h"
            designSize: BmwTheme.speedUnitSize
            color: BmwTheme.textDim
            opacity: root.reveal
            x: BmwTheme.speedX - width / 2
            y: BmwTheme.speedY + 78 + Theme.capDy(BmwTheme.speedUnitSize)
        }
    }

    // ---------------------------------------------------------------- gear
    LayoutShift {
        role: "bmw.gear"
        pivotX: BmwTheme.gearX; pivotY: BmwTheme.gearY
        Item {
            id: gearBox
            x: BmwTheme.gearX
            y: BmwTheme.gearY
            opacity: root.reveal

            ClusterText {
                id: gearText
                text: root.vehicle ? root.vehicle.gearMode : "P"
                designSize: BmwTheme.gearSize
                color: BmwTheme.textPrimary
                x: -width / 2
                y: -height / 2 + Theme.capDy(BmwTheme.gearSize)

                // Lift and settle on a change of selection, so the letter reads as
                // having been *selected* rather than simply having been replaced.
                onTextChanged: gearPop.restart()
                SequentialAnimation {
                    id: gearPop
                    NumberAnimation {
                        target: gearBox; property: "scale"
                        to: 1.22; duration: 130; easing.type: Easing.OutQuad
                    }
                    NumberAnimation {
                        target: gearBox; property: "scale"
                        to: 1.0; duration: 260; easing.type: Easing.OutBack
                    }
                }
            }

            // The ratio in use, tucked under the letter when the box is in D.
            ClusterText {
                visible: root.vehicle
                         ? (root.vehicle.gearMode === "D" && root.vehicle.gearNumber > 0)
                         : false
                text: root.vehicle ? String(root.vehicle.gearNumber) : ""
                designSize: BmwTheme.gearNumberSize
                color: root.accentRight
                x: -width / 2
                y: 62 + Theme.capDy(BmwTheme.gearNumberSize)
                Behavior on color { ColorAnimation { duration: 420 } }
            }
        }
    }

    // -------------------------------------------------------- centre stack
    LayoutShift {
        role: "bmw.media"
        pivotX: BmwTheme.centreX; pivotY: BmwTheme.artY + BmwTheme.artSize / 2
        BmwMediaTile {
            // Stands aside for a driver message rather than being covered by one.
            opacity: root.reveal * (root.vehicle && root.vehicle.message !== "" ? 0 : 1)
            Behavior on opacity { NumberAnimation { duration: 220 } }
            accent: root.accentLeft
            title: root.vehicle ? root.vehicle.mediaTitle : ""
            artist: root.vehicle ? root.vehicle.mediaArtist : ""
            elapsed: root.vehicle ? root.vehicle.mediaElapsed : 0
            duration: root.vehicle ? root.vehicle.mediaDuration : 0
            playing: root.vehicle ? root.vehicle.mediaPlaying : false
            Behavior on accent { ColorAnimation { duration: 420 } }
        }
    }

    // A driver message displaces the cover art rather than sitting over it.
    LayoutShift {
        role: "bmw.message"
        pivotX: BmwTheme.centreX; pivotY: BmwTheme.artY + BmwTheme.artSize / 2
        Rectangle {
            visible: root.vehicle ? root.vehicle.message !== "" : false
            x: BmwTheme.centreX - width / 2
            y: BmwTheme.artY + BmwTheme.artSize / 2 - height / 2
            width: message.width + 44
            height: message.height + 26
            radius: 6
            color: Qt.rgba(0, 0, 0, 0.82)
            border.width: 1
            border.color: Qt.rgba(0.96, 0.65, 0.14, 0.55)
            opacity: root.reveal

            ClusterText {
                id: message
                anchors.centerIn: parent
                text: root.vehicle ? root.vehicle.message : ""
                designSize: BmwTheme.messageSize
                color: "#F5A623"
            }
        }
    }

    // ---------------------------------------------------------- status bar
    LayoutShift {
        role: "bmw.statusbar"
        pivotX: BmwTheme.centreX; pivotY: BmwTheme.statusY
        BmwStatusBar {
            opacity: root.reveal
            accent: root.accentLeft
            driveMode: root.mode
            batteryLevel: root.vehicle ? root.vehicle.batteryLevel : 0
            charging: root.vehicle ? root.vehicle.chargingNow : false
            clock: Qt.formatTime(new Date(), "HH:mm")
            tempText: root.vehicle
                      ? (root.vehicle.outsideTemp > 0 ? "+" : "")
                        + Fmt.tempValue(root.vehicle.outsideTemp, root.vehicle.units).toFixed(1)
                      : "0.0"
            tempUnit: root.vehicle ? Fmt.tempUnit(root.vehicle.units) : "°C"
            rangeText: root.vehicle
                       ? String(Math.round(Fmt.isImperial(root.vehicle.units)
                                           ? root.vehicle.rangeKm * Fmt.kmToMi
                                           : root.vehicle.rangeKm))
                       : "0"
            rangeUnit: root.vehicle ? Fmt.distanceUnit(root.vehicle.units) : "km"
            Behavior on accent { ColorAnimation { duration: 420 } }
        }
    }

    // ----------------------------------------------------------- telltales
    LayoutShift {
        role: "bmw.telltales"
        pivotX: BmwTheme.centreX; pivotY: BmwTheme.telltaleY
        TelltaleBar {
            vehicle: root.vehicle
            opacity: root.reveal
            lampSize: BmwTheme.telltaleSize
            gap: BmwTheme.telltaleGap
            rowWidth: BmwTheme.telltaleRowWidth
            centreX: BmwTheme.centreX
            rowY: BmwTheme.telltaleY
            turnLeftX: BmwTheme.turnLeftX
            turnRightX: BmwTheme.turnRightX
            turnSize: BmwTheme.turnSize
        }
    }

    // Cruise set speed, under the speed readout on the left.
    LayoutShift {
        role: "bmw.cruise"
        pivotX: BmwTheme.speedX; pivotY: BmwTheme.speedY + 128
        Row {
            visible: root.vehicle ? root.vehicle.cruiseEnabled : false
            opacity: root.reveal
            spacing: 7
            x: BmwTheme.speedX - width / 2
            y: BmwTheme.speedY + 128

            ClusterText {
                id: cruiseValue
                text: root.vehicle ? String(root.vehicle.cruiseSetSpeed) : "0"
                designSize: BmwTheme.cruiseValueSize
                color: root.vehicle && root.vehicle.cruiseActive ? "#3FD9A0" : BmwTheme.textDim
                Behavior on color { ColorAnimation { duration: 240 } }
            }

            ClusterText {
                text: root.vehicle ? Fmt.speedUnit(root.vehicle.units) : "km/h"
                designSize: BmwTheme.cruiseUnitSize
                color: BmwTheme.textDim
                anchors.baseline: cruiseValue.baseline
            }
        }
    }

    // The screen dims to nothing when the ignition goes off.
    Rectangle {
        anchors.fill: parent
        color: BmwTheme.background
        opacity: root.awake ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 300 } }
    }
}
