pragma Singleton
import QtQuick
import Hmi

/*!
    Palette and geometry for the BMW-style cluster.

    Kept apart from \l Theme because the two designs share almost nothing: this
    one is a 16:6 letterbox with no bezel, no round dials and no needles, built
    around a pair of chevron bands that face each other across the centre —
    the signature of BMW's curved-display clusters.

    Same convention as Theme though: everything is in design pixels on a fixed
    \l designW x \l designH canvas, and the scene as a whole is scaled to the
    window, so nothing here has to know the output resolution — and, as there,
    the text sizes are bindings into \l TextSizes so the size panel can move
    them.
*/
QtObject {
    id: bmw

    // ---------------------------------------------------------------- canvas
    // A real curved display gives the driver's half roughly 1920x720.
    readonly property int designW: 1920
    readonly property int designH: 720

    // --------------------------------------------------------------- palette
    readonly property color background: "#000000"
    readonly property color panel: "#080A0D"
    readonly property color hairline: "#2A2F36"
    readonly property color textPrimary: "#FFFFFF"
    readonly property color textSecondary: "#C9D1DA"
    readonly property color textDim: "#79838F"
    readonly property color scaleTick: "#5C666F"
    readonly property color scaleTickLit: "#E8EEF4"
    readonly property color danger: "#FF3B30"

    /*!
        Unlit part of a chevron band.

        Not a flat grey: the band has to read as a machined surface catching
        light from above, so it runs from a cool steel at the top down to
        near-black, which is what stops the empty gauge looking like a hole.
    */
    readonly property color trackTop: "#39424E"
    readonly property color trackMid: "#1B222B"
    readonly property color trackBottom: "#0B0E13"
    /*! Thin bright line down the band's outer edge. */
    readonly property color trackEdge: "#5A6675"

    /*!
        Accent per drive mode, and per side.

        Sport splits the two: cold blue on the speed side, red on the power
        side, which is what the M-flavoured screens do.  The other modes run
        one colour across both — bronze for Personal, teal for Efficient.
    */
    function accentFor(mode, right) {
        if (mode === "Sport") return right ? "#FF3B30" : "#2AA8FF"
        if (mode === "Eco") return "#3FD9A0"
        if (mode === "Smart") return "#B98BE8"
        return "#D9A05B"          // Personal — the warm bronze of the reference
    }

    /*! Lighter end of an accent's gradient. */
    function accentLift(base) {
        return Qt.lighter(base, 1.45)
    }

    // ---------------------------------------------------------------- gauges
    readonly property real gaugeMidY: 330
    readonly property real gaugeHalfH: 226
    readonly property real gaugeThickness: 104
    /*! Where the band's open (outer) end and its inward point sit. */
    readonly property real leftOuterX: 372
    readonly property real leftApexX: 648
    readonly property real rightOuterX: designW - leftOuterX
    readonly property real rightApexX: designW - leftApexX

    readonly property real tickGap: 16          // between numerals and ticks
    readonly property real majorTickLen: 22
    readonly property real minorTickLen: 11
    readonly property real scaleLabelSize: TextSizes.size("bmw.scale.label")
    /*! The "km/h" / "ePower" caption. */
    readonly property real gaugeLabelSize: TextSizes.size("bmw.gauge.caption")

    readonly property real speedMax: 220
    readonly property real powerMax: 100

    // -------------------------------------------------------------- readouts
    readonly property real speedX: 176
    readonly property real speedY: 322
    readonly property real speedSize: TextSizes.size("bmw.speed.value")
    readonly property real speedUnitSize: TextSizes.size("bmw.speed.unit")
    readonly property real gearX: designW - 150
    readonly property real gearY: 322
    readonly property real gearSize: TextSizes.size("bmw.gear")
    readonly property real gearNumberSize: TextSizes.size("bmw.gear.number")

    readonly property real cruiseValueSize: TextSizes.size("bmw.cruise.value")
    readonly property real cruiseUnitSize: TextSizes.size("bmw.cruise.unit")
    readonly property real messageSize: TextSizes.size("bmw.message")


    // ----------------------------------------------------------- centre stack
    readonly property real centreX: designW / 2
    readonly property real artY: 232
    readonly property real artSize: 128
    readonly property real trackTitleSize: TextSizes.size("bmw.track.title")
    readonly property real trackArtistSize: TextSizes.size("bmw.track.artist")
    readonly property real trackRemainingSize: TextSizes.size("bmw.track.remaining")
    readonly property real trackPausedSize: TextSizes.size("bmw.track.paused")
    readonly property real trackTitleY: 404
    readonly property real trackArtistY: 436
    readonly property real progressY: 474
    readonly property real progressHalfW: 148

    // ------------------------------------------------------------ status bar
    readonly property real statusY: 646
    readonly property real statusRuleY: 612
    readonly property real statusSize: TextSizes.size("bmw.status.value")
    readonly property real statusModeSize: TextSizes.size("bmw.status.mode")
    readonly property real statusUnitSize: TextSizes.size("bmw.status.unit")
    readonly property real statusInset: 92

    // -------------------------------------------------------------- telltales
    /*! The centre of the lamp bank: three rows of fixed slots above the media tile. */
    readonly property real telltaleY: 96
    readonly property real telltaleSize: 34
    readonly property real telltaleGap: 12
    readonly property real telltaleRowGap: 10
    readonly property int telltaleColumns: 10
    readonly property real turnLeftX: 690
    readonly property real turnRightX: designW - 690
    readonly property real turnY: telltaleY
    readonly property real turnSize: 38

    // --------------------------------------------------------------- helpers
    /*!
        The six corners of a chevron band, outer edge first.

        \a t runs 0..1 up the band and is where the outline is cut off, which
        is how the lit part of a gauge is drawn: the same polygon, truncated.
        The band keeps a constant *horizontal* thickness rather than a mitred
        perpendicular one — that is what gives the flat, square-cut ends the
        real thing has.
    */
    function chevron(outerX, apexX, midY, halfH, thickness, t) {
        var dir = apexX > outerX ? 1 : -1           // which way the point faces
        var inner = thickness * dir                  // offset to the inner edge
        var top = midY - halfH
        var bottom = midY + halfH
        var cut = bottom - 2 * halfH * Math.max(0, Math.min(1, t))

        // x of the band's outer edge at height y, following the two arms.
        function edgeX(y) {
            var k = 1 - Math.abs(y - midY) / halfH   // 0 at the ends, 1 at the point
            return outerX + (apexX - outerX) * k
        }

        var points = [Qt.point(outerX, bottom), Qt.point(apexX, midY)]
        if (cut <= midY) {
            // The cut is above the point, so both arms are in play.
            points.push(Qt.point(edgeX(cut), cut))
            points.push(Qt.point(edgeX(cut) - inner, cut))
            points.push(Qt.point(apexX - inner, midY))
        } else {
            // Still on the lower arm: a short, blunt wedge.
            points = [Qt.point(outerX, bottom), Qt.point(edgeX(cut), cut),
                      Qt.point(edgeX(cut) - inner, cut)]
        }
        points.push(Qt.point(outerX - inner, bottom))
        return points
    }
}
