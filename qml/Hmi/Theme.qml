pragma Singleton
import QtQuick
import Hmi

/*!
    Every colour, coordinate and size the cluster draws with.

    The cluster is laid out on a fixed \l designW x \l designH canvas and then
    scaled uniformly to the window, so all values below are in design pixels
    and nothing needs to be recomputed when the window resizes.  Nudging the
    artwork means editing this file and nothing else — with one exception.
    Text sizes are adjustable at runtime, so each is declared once in
    \l TextSizes, with the label and description the size panel lists it
    under, and appears here as a binding into that rather than as a literal.
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

    // ------------------------------------------------- typeface adaptation
    /*!
        Proportions of the face currently in use, pushed in by Main.qml from
        FontManager.  Defaults describe the reference face, so the cluster is
        laid out correctly before the first update arrives.

        Every size below is a *design* size, quoted against the reference face.
        Text is set at \l px() of that and positioned with \l capDy(), which
        together keep the artwork put when the typeface changes underneath it.
    */
    property var fontMetrics: ({
        capScale: 1.0, capCentre: 0.517, lineRatio: 1.521, digitRatio: 0.560,
        digitScale: 1.0, refCapCentre: 0.517, refLineRatio: 1.521
    })

    /*!
        Pixel size at which \a designSize draws capitals the reference height.

        Nominal pixel size is a poor description of how big type looks: the two
        faces in the catalogue furthest apart put 0.63 and 0.73 of the em into
        their capitals, a 17% difference in apparent size at the same setting.
    */
    function px(designSize) {
        return Math.max(1, Math.round(designSize * fontMetrics.capScale))
    }

    /*!
        Vertical nudge that holds a vertically-centred run of glyphs in place.

        Qt centres a Text on its line box, which is ascent plus descent — and
        those swing from 0.79 to 1.14 of the em across the catalogue, largely
        because of how much room a face reserves for accents it may never draw.
        Centring on the box therefore moves the *visible* glyphs around as the
        face changes.  Adding this to a `y: centre - height / 2` puts the middle
        of the capital band back where the reference face had it, so use it
        anywhere the artwork centres text on a coordinate.
    */
    function capDy(designSize) {
        var m = fontMetrics
        var hRef = m.refLineRatio * designSize
        var hNow = m.lineRatio * designSize * m.capScale
        return hRef * (m.refCapCentre - 0.5) - hNow * (m.capCentre - 0.5)
    }

    /*! Roughly how wide \a count figures run at \a designSize, before layout. */
    function digitsWide(count, designSize) {
        return count * designSize * fontMetrics.capScale * fontMetrics.digitRatio
    }

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
    readonly property real labelSize: TextSizes.size("classic.dial.label")
    readonly property real innerRadius: 128

    // Scale sweep: 0 sits low-left, maximum low-right, midpoint straight up.
    readonly property real startAngle: 215
    readonly property real endAngle: -35
    readonly property real sweep: startAngle - endAngle   // 250 degrees

    readonly property real valueSize: TextSizes.size("classic.dial.speed")
    readonly property real rpmValueSize: TextSizes.size("classic.dial.rpm")
    readonly property real unitSize: TextSizes.size("classic.dial.unit")
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
    readonly property real miniLabelSize: TextSizes.size("classic.mini.label")
    readonly property real miniIconSize: 32

    // --------------------------------------------------------- centre column
    readonly property real centreX: 895
    readonly property real gearX: 712
    readonly property real topRowY: 258
    readonly property real gearSize: TextSizes.size("classic.gear")
    readonly property real gearNumberSize: TextSizes.size("classic.gear.number")
    readonly property real rangeIconX: 852
    readonly property real rangeSize: TextSizes.size("classic.range.value")
    readonly property real rangeUnitSize: TextSizes.size("classic.range.unit")

    readonly property real driveInfoY: 337
    readonly property real driveInfoSize: TextSizes.size("classic.driveinfo")

    readonly property real infoLabelX: 766
    readonly property real infoValueRight: 986
    readonly property real infoUnitX: 996
    readonly property var infoRowY: [403, 459, 515]
    readonly property real infoLabelSize: TextSizes.size("classic.info.label")
    readonly property real infoValueSize: TextSizes.size("classic.info.value")
    readonly property real infoUnitSize: TextSizes.size("classic.info.unit")

    readonly property real messageSize: TextSizes.size("classic.message")

    readonly property rect ecoBarRect: Qt.rect(768, 549, 275, 16)
    readonly property real ecoScaleY: 583
    readonly property real ecoScaleSize: TextSizes.size("classic.eco.scale")
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
    readonly property real bottomValueSize: TextSizes.size("classic.bottom.value")
    readonly property real bottomUnitSize: TextSizes.size("classic.bottom.unit")

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
    readonly property real cruiseValueSize: TextSizes.size("classic.cruise.value")
    readonly property real cruiseUnitSize: TextSizes.size("classic.cruise.unit")

    /*! The shift-up arrow, which stays in the UI face — see ClusterScene. */
    readonly property real shiftPromptSize: TextSizes.size("classic.shift")

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
