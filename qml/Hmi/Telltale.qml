import QtQuick
import Hmi

/*! A single warning / status lamp. */
Image {
    id: root

    property bool active: false
    /*! When true the lamp only shows on the "on" half of the blink cycle. */
    property bool blinking: false
    property bool blinkPhase: true

    // Lit, the lamp holds its place in the strip through the whole flash: only
    // its opacity follows the phase. Hidden instead, a flashing lamp left the
    // Flow on every off half and every lamp after it jumped a slot sideways
    // and back, 380 ms at a time.
    visible: active
    opacity: (!blinking || blinkPhase) ? 1 : 0
    width: Theme.telltaleSize
    height: Theme.telltaleSize
    sourceSize: Qt.size(128, 128)
    smooth: true
    fillMode: Image.PreserveAspectFit
}
