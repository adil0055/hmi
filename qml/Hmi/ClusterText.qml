import QtQuick
import Hmi

/*!
    Text drawn in the cluster's typeface, sized so it keeps its apparent size
    when that typeface changes.

    Set \l designSize rather than \c font.pixelSize: it is a size quoted
    against the reference face, which Theme converts for whatever face is
    loaded.  Give it a size from \l Theme or \l BmwTheme rather than a
    literal — those come from \l TextSizes, which is what lets the size panel
    find this run of text and adjust it.  Where the artwork centres text on a
    coordinate, add
    \c Theme.capDy(designSize) to the \c y as well; where one run has to sit on
    another's baseline, anchor to it (\c anchors.baseline) instead of guessing
    an offset, so Qt does the arithmetic from the real metrics.

    Give \l fitWidth a value for a readout with a hard limit on its slot — the
    widest face in the catalogue sets figures half again as wide as the
    narrowest, which is more than enough to overrun a gap the artwork leaves.
*/
Text {
    id: root

    /*! Size against the reference face; the real pixel size follows from it. */
    property real designSize: 24
    /*! When > 0, shrink rather than overrun this width. */
    property real fitWidth: 0

    font.family: Theme.fontFamily
    font.pixelSize: Theme.px(designSize)
    // Figures on a fixed pitch: a changing readout must not shuffle sideways
    // as its digits change, and most of this text is a changing readout.
    font.features: ({ "tnum": 1 })
    // Distance-field glyphs, so the whole scene scales to the window cleanly.
    renderType: Text.QtRendering
    color: Theme.textPrimary

    width: fitWidth > 0 ? fitWidth : implicitWidth
    fontSizeMode: fitWidth > 0 ? Text.HorizontalFit : Text.FixedSize
    minimumPixelSize: Math.max(8, Math.round(font.pixelSize * 0.5))
    horizontalAlignment: fitWidth > 0 ? Text.AlignHCenter : Text.AlignLeft
}
