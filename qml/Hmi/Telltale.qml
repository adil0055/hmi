import QtQuick
import Hmi

/*! A single warning / status lamp. */
Image {
    id: root

    property bool active: false
    /*! When true the lamp only shows on the "on" half of the blink cycle. */
    property bool blinking: false
    property bool blinkPhase: true

    visible: active && (!blinking || blinkPhase)
    width: Theme.telltaleSize
    height: Theme.telltaleSize
    sourceSize: Qt.size(128, 128)
    smooth: true
    fillMode: Image.PreserveAspectFit
}
