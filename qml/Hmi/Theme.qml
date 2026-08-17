pragma Singleton
import QtQuick

/*!
    Every colour, coordinate and size the cluster draws with.

    The cluster is laid out on a fixed \l designW x \l designH canvas and then
    scaled uniformly to the window, so all values below are in design pixels
    and nothing needs to be recomputed when the window resizes.  Nudging the
    artwork means editing this file and nothing else.
*/
QtObject {
    id: theme

    // ---------------------------------------------------------------- canvas
    readonly property int designW: 1790
    readonly property int designH: 870

    // Bound to the FontManager by Main.qml, so loading a typeface at runtime
    // reflows the whole cluster. `uiFontFamily` stays on the bundled face: the
    // control panel has to remain readable even if a symbol font is loaded.
    property string fontFamily: "Titillium Web"
    property string uiFontFamily: "Titillium Web"
    property url assetPath: "../../assets"

    function icon(name) { return assetPath + "/icons/" + name + ".svg" }

    // --------------------------------------------------------------- palette
    readonly property color black: "#000000"
    readonly property color screenBg: "#03050A"
    readonly property color bezelTop: "#212428"
    readonly property color bezelBottom: "#0A0B0D"
    readonly property color bezelRim: "#343A41"

    readonly property color dialFaceIn: "#12203040"   // subtle navy lift
    readonly property color dialFaceOut: "#0400070C"

    readonly property color accent: "#5AA9E6"
    readonly property color accentBright: "#9FD4F5"
    readonly property color fuelFill: "#4FC9E9"
    readonly property color danger: "#E03A2F"

    readonly property color tickMajor: "#FFFFFF"
    readonly property color tickMinor: "#93A5B7"
    readonly property color tickDim: "#141D29"

    readonly property color textPrimary: "#FFFFFF"
    readonly property color textSecondary: "#DCE4EC"
    readonly property color textDim: "#9AA8B6"
    readonly property color hairline: "#39434E"

    // Drive-mode accents; "Comfort" is the blue seen on the reference cluster.
    function modeAccent(mode) {
        if (mode === "Sport") return "#E8503A"
        if (mode === "Eco") return "#57C98A"
        if (mode === "Smart") return "#B98BE8"
        return accent
    }

    // ---------------------------------------------------------------- bezel
    readonly property rect hoodRect: Qt.rect(6, 6, designW - 12, designH - 12)
    readonly property real hoodRadius: 160
    readonly property rect glassRect: Qt.rect(44, 34, designW - 88, designH - 68)
    readonly property real glassRadius: 132

    // ---------------------------------------------------------------- dials
    readonly property real dialCy: 452
    readonly property real dialCxLeft: 420
    readonly property real dialCxRight: 1370

    readonly property real rimRadius: 252        // outer glow ring
    readonly property real tickOuter: 243        // outer end of every tick
    readonly property real majorLen: 27
    readonly property real majorWidth: 4
    readonly property real minorLen: 13
    readonly property real minorWidth: 2.4
    readonly property real labelRadius: 189
    readonly property int labelSize: 34
    readonly property real innerRadius: 128

    // Scale sweep: 0 sits low-left, maximum low-right, midpoint straight up.
    readonly property real startAngle: 215
    readonly property real endAngle: -35
    readonly property real sweep: startAngle - endAngle   // 250 degrees

    readonly property int valueSize: 96          // big speed digits
    readonly property int rpmValueSize: 88
    readonly property int unitSize: 23
    readonly property real valueDy: -8           // value centre, from dial centre
    readonly property real unitDy: 62

    readonly property real redlineFrom: 6.5      // x1000 rpm
    readonly property real rpmMax: 8.0
    readonly property real speedMax: 220

    // ------------------------------------------------- bottom arc mini gauges
    readonly property real arcRadius: 250
    readonly property real arcThickness: 9
    readonly property real arcFrom: 234          // degrees, low-left
    readonly property real arcTo: 306            // degrees, low-right
    readonly property int arcSegments: 15
    readonly property real miniLabelDy: 186      // E / F row, below dial centre
    readonly property real miniLabelDx: 100
    readonly property int miniLabelSize: 24
    readonly property real miniIconSize: 32

    // --------------------------------------------------------- centre column
    readonly property real centreX: 895
    readonly property real gearX: 712
    readonly property real topRowY: 258
    readonly property int gearSize: 72
    readonly property real rangeIconX: 852
    readonly property int rangeSize: 54
    readonly property int rangeUnitSize: 24

    readonly property real driveInfoY: 337
    readonly property int driveInfoSize: 31

    readonly property real infoLabelX: 766
    readonly property real infoValueRight: 986
    readonly property real infoUnitX: 996
    readonly property var infoRowY: [403, 459, 515]
    readonly property int infoLabelSize: 28
    readonly property int infoValueSize: 36
    readonly property int infoUnitSize: 21

    readonly property rect ecoBarRect: Qt.rect(768, 549, 275, 16)
    readonly property real ecoScaleY: 583
    readonly property int ecoScaleSize: 20
    readonly property int ecoMax: 30

    // ----------------------------------------------------------- lane render
    readonly property real laneApexY: 598
    readonly property real laneApexHalf: 17
    readonly property real laneBaseHalf: 276
    readonly property real laneBaseY: 870

    // ------------------------------------------------------------ bottom bar
    readonly property rect bottomBarRect: Qt.rect(610, 686, 570, 190)
    readonly property real bottomBarRadius: 32
    readonly property real bottomTextRight: 1090
    readonly property var bottomRowY: [707, 744]
    readonly property int bottomValueSize: 34
    readonly property int bottomUnitSize: 20

    // ------------------------------------------------------------- telltales
    readonly property real telltaleY: 118
    readonly property real telltaleSize: 46
    readonly property real telltaleGap: 14
    /*! Lamps wrap inside this width so they never reach the turn arrows. */
    readonly property real telltaleRowWidth: 680
    readonly property real turnLeftX: 500
    readonly property real turnRightX: 1290
    readonly property real turnSize: 42

    // Cruise readout lives in the free left half of the bottom panel.
    readonly property real cruiseX: 650
    readonly property real cruiseY: 725

    // -------------------------------------------------------------- helpers
    /*! Angle in degrees for \a value on a scale running \a lo .. \a hi. */
    function angleFor(value, lo, hi) {
        var t = (value - lo) / (hi - lo)
        return startAngle - sweep * Math.max(0, Math.min(1, t))
    }

    function polarX(cx, radius, degrees) {
        return cx + radius * Math.cos(degrees * Math.PI / 180)
    }

    function polarY(cy, radius, degrees) {
        return cy - radius * Math.sin(degrees * Math.PI / 180)
    }
}
